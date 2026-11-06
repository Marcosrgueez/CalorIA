"""
Scraper de Consum España usando su API REST pública.

La API no requiere autenticación ni Playwright.

Flujo por término de búsqueda:
  1. GET /catalog/product?q=TERM&limit=50 → lista de productos con precio
  2. Extrae precio €/100g desde priceData.prices[0].value.centUnitAmount / 10
  3. EAN viene directamente en el JSON del producto
  4. OpenFoodFacts con EAN → macros (kcal, proteína, grasa, carbohidratos)
  5a. Todo OK  → ScrapedProduct (supermarket="consum") → ProductORM
  5b. Falta algo → PendingProduct

precio €/kg = centUnitAmount  →  precio €/100g = centUnitAmount / 10
"""

import logging
import re
import time
from typing import Generator

import httpx

from app.scraper.mercadona import (
    ScrapedProduct,
    PendingProduct,
    _fetch_off_macros,
    _validate_macros,
)

log = logging.getLogger(__name__)

CONSUM_BASE  = "https://tienda.consum.es/api/rest/V1.0/catalog/product"
CONSUM_DELAY = 1.0   # segundos entre requests

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept":     "application/json",
    "Accept-Language": "es-ES,es;q=0.9",
}

# ── Términos de búsqueda → (query, categoría interna, max_grams/día) ────────
# Cada término genera hasta MAX_PER_TERM productos de esa categoría.
SEARCH_TERMS: list[tuple[str, str, float]] = [
    # ── PROTEÍNA ──────────────────────────────────────────────────────────────
    ("pechuga pollo",   "proteina",     300.0),
    ("muslo pollo",     "proteina",     300.0),
    ("filete ternera",  "proteina",     300.0),
    ("lomo cerdo",      "proteina",     300.0),
    ("salmon",          "proteina",     300.0),
    ("merluza",         "proteina",     300.0),
    ("atun lata",       "proteina",     200.0),
    ("sardina lata",    "proteina",     200.0),
    ("huevo",           "proteina",     300.0),
    ("jamon york",      "proteina",     100.0),
    ("pechuga pavo",    "proteina",     100.0),
    ("gambas",          "proteina",     300.0),
    # ── CARBOHIDRATO ──────────────────────────────────────────────────────────
    ("arroz",           "carbohidrato", 250.0),
    ("pasta",           "carbohidrato", 250.0),
    ("espagueti",       "carbohidrato", 250.0),
    ("macarrones",      "carbohidrato", 250.0),
    ("pan molde",       "carbohidrato", 150.0),
    ("avena",           "carbohidrato", 150.0),
    ("copos maiz",      "carbohidrato", 150.0),
    ("patata",          "carbohidrato", 300.0),
    # ── LÁCTEO ────────────────────────────────────────────────────────────────
    ("leche",           "lacteo",       400.0),
    ("yogur natural",   "lacteo",       300.0),
    ("yogur griego",    "lacteo",       300.0),
    ("queso",           "lacteo",       150.0),
    ("queso fresco",    "lacteo",       200.0),
    # ── VERDURA ───────────────────────────────────────────────────────────────
    ("tomate",          "verdura",      400.0),
    ("espinaca",        "verdura",      400.0),
    ("brocoli",         "verdura",      400.0),
    ("zanahoria",       "verdura",      400.0),
    ("lechuga",         "verdura",      400.0),
    ("pimiento",        "verdura",      300.0),
    ("calabacin",       "verdura",      400.0),
    # ── FRUTA ─────────────────────────────────────────────────────────────────
    ("manzana",         "fruta",        400.0),
    ("platano",         "fruta",        400.0),
    ("naranja",         "fruta",        400.0),
    ("pera",            "fruta",        400.0),
    ("fresa",           "fruta",        400.0),
    # ── GRASA ─────────────────────────────────────────────────────────────────
    ("aceite oliva",    "grasa",        30.0),
    ("aceite girasol",  "grasa",        30.0),
    ("almendra",        "grasa",        40.0),
    ("nuez",            "grasa",        40.0),
    ("mantequilla",     "grasa",        30.0),
    # ── LEGUMBRE ──────────────────────────────────────────────────────────────
    ("lenteja",         "legumbre",     200.0),
    ("garbanzo",        "legumbre",     200.0),
    ("judias blancas",  "legumbre",     200.0),
    ("guisantes",       "legumbre",     200.0),
]

MAX_PER_TERM = 15   # productos máximos por término de búsqueda

# ── Macros genéricos por keyword (fallback cuando OFF no tiene el EAN) ───────
# Valores medios estándar por 100g para cada tipo de alimento.
_MACRO_FALLBACKS: dict[str, dict] = {
    # Carnes
    "pollo":       {"kcal": 165, "protein": 31,  "fat": 3.6,  "carbs": 0},
    "pechuga":     {"kcal": 165, "protein": 31,  "fat": 3.6,  "carbs": 0},
    "muslo":       {"kcal": 209, "protein": 26,  "fat": 11,   "carbs": 0},
    "pavo":        {"kcal": 189, "protein": 29,  "fat": 7,    "carbs": 0},
    "ternera":     {"kcal": 215, "protein": 26,  "fat": 12,   "carbs": 0},
    "vacuno":      {"kcal": 250, "protein": 26,  "fat": 15,   "carbs": 0},
    "cerdo":       {"kcal": 242, "protein": 27,  "fat": 14,   "carbs": 0},
    "lomo":        {"kcal": 182, "protein": 22,  "fat": 10,   "carbs": 0},
    "salmon":      {"kcal": 208, "protein": 20,  "fat": 13,   "carbs": 0},
    "merluza":     {"kcal": 86,  "protein": 17,  "fat": 1.5,  "carbs": 0},
    "atun":        {"kcal": 144, "protein": 23,  "fat": 5,    "carbs": 0},
    "sardina":     {"kcal": 208, "protein": 25,  "fat": 11,   "carbs": 0},
    "bacalao":     {"kcal": 82,  "protein": 18,  "fat": 0.7,  "carbs": 0},
    "gambas":      {"kcal": 85,  "protein": 18,  "fat": 1,    "carbs": 0},
    "mejillon":    {"kcal": 86,  "protein": 12,  "fat": 2,    "carbs": 3.7},
    # Lácteos
    "leche":       {"kcal": 61,  "protein": 3.2, "fat": 3.3,  "carbs": 4.8},
    "yogur":       {"kcal": 59,  "protein": 3.5, "fat": 3.3,  "carbs": 4.7},
    "queso":       {"kcal": 402, "protein": 25,  "fat": 33,   "carbs": 1.3},
    "mantequilla": {"kcal": 717, "protein": 0.9, "fat": 81,   "carbs": 0.1},
    # Huevos
    "huevo":       {"kcal": 155, "protein": 13,  "fat": 11,   "carbs": 1.1},
    # Verduras
    "espinaca":    {"kcal": 23,  "protein": 2.9, "fat": 0.4,  "carbs": 3.6},
    "brocoli":     {"kcal": 34,  "protein": 2.8, "fat": 0.4,  "carbs": 7},
    "tomate":      {"kcal": 18,  "protein": 0.9, "fat": 0.2,  "carbs": 3.9},
    "zanahoria":   {"kcal": 41,  "protein": 0.9, "fat": 0.2,  "carbs": 10},
    "champinon":   {"kcal": 22,  "protein": 3.1, "fat": 0.3,  "carbs": 3.3},
    # Carbohidratos
    "arroz":       {"kcal": 356, "protein": 7,   "fat": 0.9,  "carbs": 78},
    "pasta":       {"kcal": 371, "protein": 13,  "fat": 1.5,  "carbs": 75},
    "pan":         {"kcal": 265, "protein": 9,   "fat": 3.2,  "carbs": 49},
    "avena":       {"kcal": 389, "protein": 17,  "fat": 7,    "carbs": 66},
    # Legumbres
    "lenteja":     {"kcal": 116, "protein": 9,   "fat": 0.4,  "carbs": 20},
    "garbanzo":    {"kcal": 164, "protein": 9,   "fat": 2.6,  "carbs": 27},
    "alubia":      {"kcal": 127, "protein": 8,   "fat": 0.5,  "carbs": 23},
    "guisante":    {"kcal": 81,  "protein": 5.4, "fat": 0.4,  "carbs": 14},
    # Grasas
    "aceite":      {"kcal": 884, "protein": 0,   "fat": 100,  "carbs": 0},
    "nuez":        {"kcal": 654, "protein": 15,  "fat": 65,   "carbs": 14},
    "almendra":    {"kcal": 579, "protein": 21,  "fat": 50,   "carbs": 22},
}


def _get_fallback_macros(name: str) -> dict | None:
    """
    Devuelve macros genéricos por 100g si el nombre del producto contiene
    una keyword conocida. Claves en formato ScrapedProduct (*_per_100g).
    """
    name_lower = name.lower()
    for keyword, m in _MACRO_FALLBACKS.items():
        if keyword in name_lower:
            return {
                "kcal_per_100g":    float(m["kcal"]),
                "protein_per_100g": float(m["protein"]),
                "fat_per_100g":     float(m["fat"]),
                "carbs_per_100g":   float(m["carbs"]),
            }
    return None


# ── Helpers ─────────────────────────────────────────────────────────────────

def _search(client: httpx.Client, query: str, limit: int = 50) -> list[dict]:
    """Llama a la API de Consum y devuelve lista de productos crudos."""
    params = {"q": query, "limit": limit, "locale": "es_ES"}
    time.sleep(CONSUM_DELAY)
    try:
        r = client.get(CONSUM_BASE, params=params, timeout=15)
        r.raise_for_status()
        return r.json().get("products", [])
    except Exception as e:
        log.warning("Error buscando '%s' en Consum: %s", query, e)
        return []


def _extract_price_per_100g(product: dict) -> float | None:
    """
    centUnitAmount está en €/kg → dividir entre 10 para obtener €/100g.
    Devuelve None si no hay precio o no es por kg.
    """
    try:
        pd     = product.get("priceData", {})
        prices = pd.get("prices", [])
        if not prices:
            return None
        unit_type = (pd.get("unitPriceUnitType") or "").lower()
        # Aceptamos "1 kg", "1kg", "kg", "" (asumimos kg cuando unitPriceUnitType vacío
        # y priceUnitType está vacío — productos sólidos vendidos por pieza o peso)
        cent_unit = prices[0].get("value", {}).get("centUnitAmount")
        if cent_unit is None or cent_unit <= 0:
            return None
        return round(float(cent_unit) / 10, 4)
    except Exception:
        return None


def _extract_package_size_g(description: str | None) -> float | None:
    """Extrae gramos del envase desde la descripción, ej. 'Pechuga de Pollo 340 Gr'."""
    if not description:
        return None
    # Busca patrones como "340 Gr", "1.5 Kg", "500g", "1 kg"
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(kg|g|gr)\b", description, re.IGNORECASE)
    if not m:
        return None
    try:
        val  = float(m.group(1).replace(",", "."))
        unit = m.group(2).lower()
        if unit == "kg":
            val *= 1000
        return round(val)
    except ValueError:
        return None


def _extract_package_price(product: dict) -> float | None:
    """Precio total del envase (centAmount)."""
    try:
        prices = product.get("priceData", {}).get("prices", [])
        if not prices:
            return None
        v = prices[0].get("value", {}).get("centAmount")
        return float(v) if v is not None else None
    except Exception:
        return None


# ── Scraping de un término de búsqueda ──────────────────────────────────────

def _scrape_term(
    client: httpx.Client,
    off_client: httpx.Client,
    query: str,
    internal_cat: str,
    max_grams: float,
    seen_names: set[str],
) -> tuple[list[ScrapedProduct], list[PendingProduct]]:
    ready:   list[ScrapedProduct] = []
    pending: list[PendingProduct] = []

    products = _search(client, query, limit=50)
    log.info("  '%s' → %d resultados", query, len(products))

    count = 0
    for raw in products:
        if count >= MAX_PER_TERM:
            break

        name = (raw.get("productData", {}).get("name") or "").strip()
        if not name or name in seen_names:
            continue

        ean  = raw.get("ean") or None
        desc = raw.get("productData", {}).get("description") or ""

        price = _extract_price_per_100g(raw)
        if price is None or price > 5.0:   # precio absurdo → saltar
            pending.append(PendingProduct(
                mercadona_id=f"consum_{ean or name}",
                name=name, ean=ean,
                mercadona_category=query,
                internal_category=internal_cat,
                price_per_100g=price,
                reason="no_unit_price",
            ))
            continue

        # Macros via OpenFoodFacts, con fallback a valores genéricos por keyword
        macros, reason = _fetch_off_macros(off_client, ean)
        estimated = False

        if macros is None:
            macros = _get_fallback_macros(name)
            if macros is not None:
                estimated = True
                log.debug("  ~ %s → macros estimados (fallback)", name[:40])
            else:
                pending.append(PendingProduct(
                    mercadona_id=f"consum_{ean or name}",
                    name=name, ean=ean,
                    mercadona_category=query,
                    internal_category=internal_cat,
                    price_per_100g=price,
                    reason=reason or "off_not_found",
                ))
                continue

        if not _validate_macros(internal_cat, macros):
            log.debug("  ⚠ macros inválidos para %s (%s): kcal=%.0f",
                      name[:40], internal_cat, macros.get("kcal_per_100g", 0))
            pending.append(PendingProduct(
                mercadona_id=f"consum_{ean or name}",
                name=name, ean=ean,
                mercadona_category=query,
                internal_category=internal_cat,
                price_per_100g=price,
                reason="invalid_macros",
            ))
            continue

        package_size_g  = _extract_package_size_g(desc)
        package_price   = _extract_package_price(raw)

        log.info("  %s %s (%.3f€/100g, %.0fkcal, %s)",
                 "~" if estimated else "✓",
                 name[:40], price, macros["kcal_per_100g"], internal_cat)

        seen_names.add(name)
        count += 1
        ready.append(ScrapedProduct(
            name=name,
            category=internal_cat,
            price_per_100g=price,
            max_grams_per_day=max_grams,
            ean=ean,
            source="consum_estimated" if estimated else "consum",
            supermarket="consum",
            **macros,
        ))

        # Guardamos tamaño/precio de envase en el producto si la ORM lo soporta
        # (package_size_g y package_price_eur se asignan en el script de escritura)
        ready[-1].__dict__["_package_size_g"]   = package_size_g
        ready[-1].__dict__["_package_price_eur"] = package_price

    return ready, pending


# ── Generador principal ──────────────────────────────────────────────────────

def scrape(
    max_terms: int | None = None,
) -> Generator[tuple[list[ScrapedProduct], list[PendingProduct]], None, None]:
    """
    Generador que scrapeea el catálogo de Consum España.
    Yielde (ready_batch, pending_batch) al terminar cada término de búsqueda.

    Args:
        max_terms: Limita el número de términos procesados (None = todos).
    """
    off_client = httpx.Client(
        headers={"User-Agent": "CalorIA/0.1 (educational project, contact: dev@caloria.local)"},
        timeout=20,
    )
    consum_client = httpx.Client(headers=_HEADERS, timeout=15, follow_redirects=True)

    terms = SEARCH_TERMS if max_terms is None else SEARCH_TERMS[:max_terms]
    seen_names: set[str] = set()

    try:
        for query, cat, max_g in terms:
            log.info("Término: '%s' → %s", query, cat)
            ready, pending = _scrape_term(
                consum_client, off_client, query, cat, max_g, seen_names,
            )
            yield ready, pending
    finally:
        consum_client.close()
        off_client.close()
