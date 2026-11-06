"""
Scraper de Mercadona + enriquecedor OpenFoodFacts.

Jerarquía de categorías confirmada el 2026-04-10:
  Nivel 0  (ej: id=1 "Fruta y verdura")  → GET /categories/{id}/ devuelve 404
  Nivel 1  (ej: id=27 "Fruta")           → GET /categories/{id}/ devuelve nivel-2 con productos
  Nivel 2  (ej: id=853 "Plátano y uva")  → productos embebidos en la respuesta nivel-1, sin EAN

Flujo por producto:
  1. GET /categories/          → árbol completo (nivel-0 y nivel-1 embebidos)
  2. Para cada nivel-1 mapeado → GET /categories/{id}/ → nivel-2 + productos
  3. Para cada producto        → GET /products/{id}/   → EAN (solo disponible aquí)
  4. OpenFoodFacts con EAN    → macros (kcal, proteína, grasa, carbohidratos)
  5a. Todo OK  → ScrapedProduct  → ProductORM
  5b. Falta algo → PendingProduct → ProductPendingORM

La Mercadona API no expone macros numéricos. Confirmado en 20+ productos de 7 categorías.
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

from app.scraper.normalizer import SCRAPE_TOP_LEVEL_IDS, CategoryMapping, get_mapping

log = logging.getLogger(__name__)

MERCADONA_BASE = "https://tienda.mercadona.es/api"
OFF_BASE       = "https://world.openfoodfacts.org/api/v2"

MERCADONA_DELAY = 1.5   # segundos entre requests a Mercadona
OFF_DELAY       = 2.0   # segundos entre requests a OpenFoodFacts (429 frecuentes con < 2s)

_HEADERS_MERCADONA = {
    "Accept-Language": "es",
    "User-Agent": "CalorIA/0.1 (educational project, contact: dev@caloria.local)",
}
_HEADERS_OFF = {
    "User-Agent": "CalorIA/0.1 (educational project, contact: dev@caloria.local)",
}


# ─────────────────────────────────────────────
# Tipos de resultado
# ─────────────────────────────────────────────

@dataclass
class ScrapedProduct:
    """Producto listo para insertar en ProductORM."""
    name: str
    category: str
    price_per_100g: float
    kcal_per_100g: float
    protein_per_100g: float
    fat_per_100g: float
    carbs_per_100g: float
    max_grams_per_day: float
    ean: str | None
    source: str = "mercadona"
    supermarket: str = "mercadona"
    scraped_at: datetime = None

    def __post_init__(self):
        if self.scraped_at is None:
            self.scraped_at = datetime.now(timezone.utc)


@dataclass
class PendingProduct:
    """Producto de Mercadona sin macros completos."""
    mercadona_id: str
    name: str
    ean: str | None
    mercadona_category: str
    internal_category: str | None
    price_per_100g: float | None
    reason: str


# ─────────────────────────────────────────────
# HTTP helpers
# ─────────────────────────────────────────────

def _get(client: httpx.Client, url: str, delay: float = 0) -> dict | None:
    """GET con delay y manejo de errores. Devuelve None si falla."""
    if delay:
        time.sleep(delay)
    try:
        r = client.get(url, timeout=20)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as e:
        log.warning("HTTP %s → %s", e.response.status_code, url)
        return None
    except Exception as e:
        log.warning("Error de red %s → %s", type(e).__name__, url)
        return None


# ─────────────────────────────────────────────
# Precio por 100g
# ─────────────────────────────────────────────

def _price_per_100g(price_instructions: dict) -> float | None:
    """
    Precio/100g desde reference_price y reference_format.
    Solo kg/l son computables. "ud", "dz", etc. → None.
    """
    fmt = (price_instructions.get("reference_format") or "").lower()
    ref = price_instructions.get("reference_price")
    if fmt not in ("kg", "l") or ref is None:
        return None
    try:
        return round(float(ref) / 10, 4)
    except (ValueError, TypeError):
        return None


# ─────────────────────────────────────────────
# OpenFoodFacts
# ─────────────────────────────────────────────

_OFF_NOT_FOUND   = "off_not_found"    # EAN no existe en OpenFoodFacts
_OFF_INCOMPLETE  = "off_incomplete"   # Existe pero faltan macros
_OFF_RATE_LIMIT  = "off_rate_limit"   # 429 — reintentar más tarde

# ─────────────────────────────────────────────
# Validación de rangos nutricionales
# ─────────────────────────────────────────────

# (kcal_min, kcal_max, extra_check_fn_or_None)
_MACRO_RANGES: dict[str, dict] = {
    "proteina":     {"kcal": (50,  900), "protein_per_100g": 5.0},
    "legumbre":     {"kcal": (50,  400)},
    "carbohidrato": {"kcal": (50,  600), "carbs_per_100g":  10.0},
    "verdura":      {"kcal": (5,   200)},
    "fruta":        {"kcal": (20,  400)},
    "lacteo":       {"kcal": (20,  700)},
    "grasa":        {"kcal": (50,  950), "fat_per_100g":    10.0},
}


def _validate_macros(category: str, macros: dict) -> bool:
    """
    Devuelve True si los macros son plausibles para la categoría dada.
    macros es el dict devuelto por _fetch_off_macros: {kcal_per_100g, protein_per_100g, ...}
    """
    rules = _MACRO_RANGES.get(category)
    if rules is None:
        return True  # categoría desconocida → no validar

    kcal = macros.get("kcal_per_100g", 0)
    kcal_min, kcal_max = rules["kcal"]
    if not (kcal_min <= kcal <= kcal_max):
        return False

    if "protein_per_100g" in rules:
        if macros.get("protein_per_100g", 0) < rules["protein_per_100g"]:
            return False

    if "carbs_per_100g" in rules:
        if macros.get("carbs_per_100g", 0) < rules["carbs_per_100g"]:
            return False

    if "fat_per_100g" in rules:
        if macros.get("fat_per_100g", 0) < rules["fat_per_100g"]:
            return False

    return True


def _fetch_off_macros(
    client: httpx.Client, ean: str | None
) -> tuple[dict | None, str | None]:
    """
    Macros por 100g desde OpenFoodFacts usando EAN.
    Requiere: energy-kcal_100g, proteins_100g, fat_100g, carbohydrates_100g.

    Returns:
        (macros_dict, None)     si todos los macros están disponibles
        (None, reason_string)   si no es posible obtener los macros
    """
    if not ean:
        return None, "no_ean"

    url = f"{OFF_BASE}/product/{ean}.json"
    if OFF_DELAY:
        time.sleep(OFF_DELAY)
    try:
        r = client.get(url, timeout=20)
        if r.status_code == 429:
            log.warning("Rate limit OpenFoodFacts, esperando 5s...")
            time.sleep(5)
            r = client.get(url, timeout=20)  # un reintento
        if r.status_code == 404 or r.status_code >= 400:
            return None, _OFF_NOT_FOUND
        data = r.json()
    except Exception as e:
        log.warning("Error red OpenFoodFacts %s: %s", ean, e)
        return None, _OFF_NOT_FOUND

    if data.get("status") != 1:
        return None, _OFF_NOT_FOUND

    n = data.get("product", {}).get("nutriments", {})
    kcal  = n.get("energy-kcal_100g")
    prot  = n.get("proteins_100g")
    fat   = n.get("fat_100g")
    carbs = n.get("carbohydrates_100g")

    if any(v is None for v in (kcal, prot, fat, carbs)):
        return None, _OFF_INCOMPLETE

    return {
        "kcal_per_100g":     float(kcal),
        "protein_per_100g":  float(prot),
        "fat_per_100g":      float(fat),
        "carbs_per_100g":    float(carbs),
    }, None


# ─────────────────────────────────────────────
# Proceso de un producto
# ─────────────────────────────────────────────

def _process_product(
    raw: dict,
    level1_subcat_name: str,
    mapping: CategoryMapping | None,
    off_client: httpx.Client,
) -> ScrapedProduct | PendingProduct:
    pid  = str(raw.get("id", ""))
    name = raw.get("display_name") or raw.get("slug") or pid
    ean  = raw.get("ean")  # solo presente en /products/{id}/, no en listado

    price = _price_per_100g(raw.get("price_instructions", {}))

    if price is None:
        return PendingProduct(
            mercadona_id=pid, name=name, ean=ean,
            mercadona_category=level1_subcat_name,
            internal_category=mapping.internal if mapping else None,
            price_per_100g=None, reason="price_not_per_kg",
        )

    if mapping is None:
        return PendingProduct(
            mercadona_id=pid, name=name, ean=ean,
            mercadona_category=level1_subcat_name,
            internal_category=None,
            price_per_100g=price, reason="category_not_mapped",
        )

    macros, reason = _fetch_off_macros(off_client, ean)
    if macros is None:
        return PendingProduct(
            mercadona_id=pid, name=name, ean=ean,
            mercadona_category=level1_subcat_name,
            internal_category=mapping.internal,
            price_per_100g=price, reason=reason,
        )

    if not _validate_macros(mapping.internal, macros):
        log.warning(
            "    ⚠ macros inválidos para %s (%s): kcal=%.0f prot=%.1f fat=%.1f carbs=%.1f",
            name[:40], mapping.internal,
            macros.get("kcal_per_100g", 0), macros.get("protein_per_100g", 0),
            macros.get("fat_per_100g", 0), macros.get("carbs_per_100g", 0),
        )
        return PendingProduct(
            mercadona_id=pid, name=name, ean=ean,
            mercadona_category=level1_subcat_name,
            internal_category=mapping.internal,
            price_per_100g=price, reason="invalid_macros",
        )

    return ScrapedProduct(
        name=name, category=mapping.internal,
        price_per_100g=price,
        max_grams_per_day=mapping.max_grams_per_day,
        ean=ean, **macros,
    )


# ─────────────────────────────────────────────
# Scraper principal
# ─────────────────────────────────────────────

def scrape(
    max_categories: int | None = None,
):
    """
    Generador que scrapeea el catálogo de Mercadona para categorías alimentarias relevantes.
    Yielde (ready_batch, pending_batch) al terminar cada subcategoría de nivel-1.

    Navegación:
      /categories/           → árbol completo con nivel-1 subcats embebidas
      /categories/{level1}/  → nivel-2 subcats con productos (nivel-1 IDs sí funcionan)
      /products/{pid}/       → detalle individual con EAN

    Args:
        max_categories: límite de nivel-1 subcategorías a procesar (None = sin límite).

    Yields:
        tuple[list[ScrapedProduct], list[PendingProduct]]: productos de la subcategoría actual.
    """
    merc_client = httpx.Client(headers=_HEADERS_MERCADONA)
    off_client  = httpx.Client(headers=_HEADERS_OFF)

    try:
        log.info("Obteniendo árbol de categorías de Mercadona...")
        cat_tree = _get(merc_client, f"{MERCADONA_BASE}/categories/")
        if not cat_tree:
            log.error("No se pudo obtener el árbol de categorías.")
            return

        cats_processed = 0

        for top_cat in cat_tree.get("results", []):
            if top_cat["id"] not in SCRAPE_TOP_LEVEL_IDS:
                continue

            log.info("Sección: [%d] %s", top_cat["id"], top_cat["name"])

            # top_cat["categories"] son los subcats de nivel-1 (sí navegables)
            for level1 in top_cat.get("categories", []):
                level1_id   = level1["id"]
                level1_name = level1["name"]
                mapping     = get_mapping(level1_id)

                if mapping is None:
                    log.debug("  [%d] %s → no mapeada, saltando", level1_id, level1_name)
                    continue

                log.info("  Subcategoría [%d] %s → %s", level1_id, level1_name, mapping.internal)

                # GET /categories/{level1_id}/ → nivel-2 con productos embebidos
                level1_data = _get(
                    merc_client,
                    f"{MERCADONA_BASE}/categories/{level1_id}/",
                    delay=MERCADONA_DELAY,
                )
                if not level1_data:
                    continue

                # Recoger todos los productos de todas las sub-subcategorías
                all_products = [
                    p
                    for level2 in level1_data.get("categories", [])
                    for p in level2.get("products", [])
                ]

                log.info("    %d productos encontrados", len(all_products))

                batch_ready:   list[ScrapedProduct] = []
                batch_pending: list[PendingProduct] = []

                for raw in all_products:
                    pid = str(raw.get("id", ""))

                    # Obtener detalle individual para conseguir EAN
                    detail = _get(
                        merc_client,
                        f"{MERCADONA_BASE}/products/{pid}/",
                        delay=MERCADONA_DELAY,
                    )
                    if detail:
                        raw = detail

                    result = _process_product(raw, level1_name, mapping, off_client)

                    if isinstance(result, ScrapedProduct):
                        log.info(
                            "    ✓ %s (%.3f€/100g, %.0fkcal, %s)",
                            result.name[:40], result.price_per_100g,
                            result.kcal_per_100g, result.category,
                        )
                        batch_ready.append(result)
                    else:
                        log.warning("    ✗ %s → pending: %s", result.name[:40], result.reason)
                        batch_pending.append(result)

                cats_processed += 1
                yield batch_ready, batch_pending

                if max_categories and cats_processed >= max_categories:
                    log.info("Límite de %d subcategorías alcanzado.", max_categories)
                    return

    finally:
        merc_client.close()
        off_client.close()
