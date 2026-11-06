"""
Scraper de Carrefour España usando Playwright.

Flujo por categoría:
  1. Navega a /supermercado/alimentacion/cat20001/c → descubre subcategorías
  2. Para cada subcategoría mapeada → extrae productos del listado paginado
  3. Para cada producto sin macros → visita ficha de detalle (tabla nutricional)
  4. Fallback: OpenFoodFacts con EAN si Carrefour no expone macros
  5a. Todo OK  → ScrapedProduct (supermarket="carrefour") → ProductORM
  5b. Falta algo → PendingProduct

Nota: Playwright supera el bloqueo de Cloudflare renderizando el JS completo.
"""

import logging
import random
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Generator

import httpx
from playwright.sync_api import sync_playwright, Page
from playwright_stealth import Stealth

from app.scraper.mercadona import (
    ScrapedProduct,
    PendingProduct,
    _fetch_off_macros,
    _validate_macros,
)

log = logging.getLogger(__name__)

CARREFOUR_BASE = "https://www.carrefour.es"

PAGE_LOAD_DELAY  = 4.5   # segundos tras navegar (Carrefour renderiza via JS; más = menos detección)
DETAIL_DELAY     = 2.0   # segundos en ficha de producto
MAX_PRODUCTS_CAT = 80    # límite de productos por subcategoría

# ── Mapeo slug de URL → (categoría interna, max_grams_per_day) ─────────────
# Si alguna keyword aparece en el path de la URL la subcategoría queda mapeada.
_SLUG_MAPPINGS: list[tuple[list[str], str, float]] = [
    (["pollo", "pavo", "aves"],                                 "proteina",     300.0),
    (["cerdo", "porcino"],                                      "proteina",     300.0),
    (["ternera", "vacuno", "buey"],                             "proteina",     300.0),
    (["cordero", "conejo", "caza"],                             "proteina",     300.0),
    (["hamburguesa", "carne-picada", "picada"],                 "proteina",     250.0),
    (["embutido", "jamon", "chorizo", "salchicha",
      "mortadela", "sobrasada", "pate", "foie"],               "proteina",     100.0),
    (["pescado", "marisco", "salmon", "merluza",
      "atun", "sardina", "mejillon", "gamba"],                 "proteina",     300.0),
    (["conservas-de-pescado", "conservas-pescado"],             "proteina",     200.0),
    (["huevo"],                                                 "proteina",     300.0),
    (["leche", "bebida-vegetal", "bebidas-vegetales"],          "lacteo",       400.0),
    (["yogur"],                                                 "lacteo",       300.0),
    (["queso"],                                                 "lacteo",       150.0),
    (["fruta"],                                                 "fruta",        400.0),
    (["verdura", "hortaliza", "patata", "cebolla",
      "brocoli", "espinaca", "zanahoria"],                     "verdura",      400.0),
    (["tomate"],                                                "verdura",      300.0),
    (["pasta", "espagueti", "macarron", "fideo"],               "carbohidrato", 250.0),
    (["arroz"],                                                 "carbohidrato", 250.0),
    (["pan-de-molde", "pan-tostado", "tostada", "biscote"],    "carbohidrato", 150.0),
    (["cereal", "muesli", "granola", "avena"],                  "carbohidrato", 150.0),
    (["legumbre", "lenteja", "garbanzo", "judias", "alubias",
      "guisante"],                                              "legumbre",     200.0),
    (["aceite"],                                                "grasa",        30.0),
    (["frutos-secos", "fruto-seco"],                            "grasa",        40.0),
    (["mantequilla", "margarina"],                              "grasa",        30.0),
]


def _slug_to_category(url_path: str) -> tuple[str, float] | None:
    path = url_path.lower()
    for keywords, cat, max_g in _SLUG_MAPPINGS:
        if any(kw in path for kw in keywords):
            return cat, max_g
    return None


# ── Parsing de precio por 100g ─────────────────────────────────────────────

def _parse_price_per_100g(text: str | None) -> float | None:
    """
    Parsea textos como '2,45 €/kg', '0,89 €/100g', '12,50 €/l'.
    Devuelve €/100g o None.
    """
    if not text:
        return None
    text = text.replace("\xa0", " ").strip()
    m = re.search(r"([\d][,.\d]+)", text)
    if not m:
        return None
    try:
        price = float(m.group(1).replace(",", "."))
    except ValueError:
        return None
    tl = text.lower()
    if "/kg" in tl or "/ kg" in tl:
        return round(price / 10, 4)
    if "/100g" in tl or "/ 100g" in tl:
        return round(price, 4)
    if "/l" in tl or "/ l" in tl or "/litro" in tl:
        return round(price / 10, 4)
    if "/100ml" in tl:
        return round(price, 4)
    return None


# ── Extracción de macros de página de detalle ──────────────────────────────

_NUT_PATTERNS: list[tuple[str, str]] = [
    ("kcal",  r"energ[eé]tico[^0-9]{0,80}?([\d][,.\d]*)\s*kcal"),
    ("kcal",  r"([\d][,.\d]*)\s*kcal"),
    ("prot",  r"prote[íi]na[s]?[^0-9]{0,60}?([\d][,.\d]*)\s*g"),
    ("fat",   r"gras[as][^0-9]{0,60}?([\d][,.\d]*)\s*g"),
    ("carbs", r"(?:hidratos?\s+de\s+carbono|carbohidrato[s]?)[^0-9]{0,60}?([\d][,.\d]*)\s*g"),
]


def _parse_nutrition_text(text: str) -> dict | None:
    def _find(pattern: str) -> float | None:
        m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if m:
            try:
                return float(m.group(1).replace(",", "."))
            except (ValueError, AttributeError):
                pass
        return None

    results: dict[str, float | None] = {}
    for key, pat in _NUT_PATTERNS:
        if key not in results:
            results[key] = _find(pat)

    if any(results.get(k) is None for k in ("kcal", "prot", "fat", "carbs")):
        return None
    return {
        "kcal_per_100g":    float(results["kcal"]),
        "protein_per_100g": float(results["prot"]),
        "fat_per_100g":     float(results["fat"]),
        "carbs_per_100g":   float(results["carbs"]),
    }


_DETAIL_NUTRITION_SELECTORS = [
    ".product-nutritional-information",
    "[data-testid*='nutritional']",
    "[data-testid*='nutrition']",
    ".nutritional-info",
    "[class*='NutritionalInfo']",
    "[class*='nutritional']",
    "[class*='nutrition']",
    "table[class*='nutri']",
]

_DETAIL_EAN_JS = """
() => {
    const metaNames = ['product:retailer_item_id','product:ean','og:upc','product:isbn'];
    for (const n of metaNames) {
        const el = document.querySelector(`meta[property="${n}"], meta[name="${n}"]`);
        if (el && /^\\d{8,14}$/.test(el.content)) return el.content;
    }
    for (const el of document.querySelectorAll('[data-ean],[data-barcode],[data-gtin],[data-upc]')) {
        const v = el.dataset.ean || el.dataset.barcode || el.dataset.gtin || el.dataset.upc;
        if (v && /^\\d{8,14}$/.test(v)) return v;
    }
    for (const s of document.querySelectorAll('script[type="application/ld+json"]')) {
        try {
            const d = JSON.parse(s.textContent);
            const items = Array.isArray(d) ? d : [d];
            for (const item of items) {
                const g = item.gtin13 || item.gtin || item.gtin8 || item.sku;
                if (g && /^\\d{8,14}$/.test(String(g))) return String(g);
            }
        } catch {}
    }
    return null;
}
"""

_LISTING_EXTRACT_JS = """
() => {
    const cardSels = [
        '.product-card-list__item',
        'article.product-card-list__item',
        '[data-testid="product-item"]',
        '[data-testid*="product-card"]',
        '.bc-product-tile',
        '[class*="ProductCard"]',
    ];
    let cards = [];
    for (const sel of cardSels) {
        cards = [...document.querySelectorAll(sel)];
        if (cards.length) break;
    }
    return cards.map(card => {
        const nameEl = card.querySelector(
            '.product-card__title,.product-card__title-link,' +
            'h2,h3,[data-testid*="title"],[data-testid*="name"],' +
            '.product-card-list__item-title,.product-title'
        );
        const unitPriceEl = card.querySelector(
            '.product-card__price-per-unit,' +
            '[class*="price-per-unit"],[class*="pricePerUnit"],' +
            '[data-testid*="unit-price"],[data-testid*="unitPrice"],' +
            '.price-per-unit,.unit-price'
        );
        const linkEl = card.querySelector(
            '.product-card__media-link,.product-card__title-link,' +
            'a[href*="/supermercado/"]'
        );
        const ean = card.dataset.ean || card.dataset.gtin || null;
        return {
            name:              nameEl      ? nameEl.textContent.trim()      : null,
            price_per_kg_text: unitPriceEl ? unitPriceEl.textContent.trim() : null,
            url:               linkEl      ? linkEl.href                    : null,
            ean:               ean && /^\\d{8,14}$/.test(ean) ? ean : null,
        };
    }).filter(p => p.name && p.name.length > 1);
}
"""

_LOAD_MORE_JS = """
() => {
    const sels = [
        'button[data-testid*="load-more"]','button[data-testid*="show-more"]',
        '.load-more-button','[class*="loadMore"]',
    ];
    for (const sel of sels) {
        const btn = document.querySelector(sel);
        if (btn) { btn.click(); return true; }
    }
    const btns = [...document.querySelectorAll('button')];
    const kw = ['ver más','cargar más','mostrar más','show more'];
    for (const btn of btns) {
        if (kw.some(k => btn.textContent.toLowerCase().includes(k))) {
            btn.click(); return true;
        }
    }
    return false;
}
"""


# ── Helpers de página ──────────────────────────────────────────────────────

def _navigate(page: Page, url: str, delay: float = PAGE_LOAD_DELAY) -> bool:
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=35_000)
        time.sleep(delay + random.uniform(0, 1.5))
        return True
    except Exception as e:
        log.warning("Error navegando a %s: %s", url, e)
        return False


def _wait_products(page: Page) -> bool:
    product_sels = [
        ".product-card-list__item",
        "article.product-card-list__item",
        "[data-testid='product-item']",
        "[data-testid*='product-card']",
        ".bc-product-tile",
        ".product-card",
    ]
    for sel in product_sels:
        try:
            page.wait_for_selector(sel, timeout=12_000)
            return True
        except Exception:
            continue
    return False


def _scroll_to_load_all(page: Page) -> None:
    """Scroll incrementally so lazy-loaded product cards populate their content."""
    scroll_step = 600
    for _ in range(20):
        before = page.evaluate("() => document.querySelectorAll('.product-card-list__item .product-card__title').length")
        page.evaluate(f"() => window.scrollBy(0, {scroll_step})")
        time.sleep(0.6)
        after = page.evaluate("() => document.querySelectorAll('.product-card-list__item .product-card__title').length")
        if after == before:
            # No new items appeared — at bottom or fully loaded
            at_bottom = page.evaluate(
                "() => (window.scrollY + window.innerHeight) >= document.body.scrollHeight - 200"
            )
            if at_bottom:
                break
    # Scroll back to top so next navigation is clean
    page.evaluate("() => window.scrollTo(0, 0)")


def _extract_detail_info(page: Page, product_url: str) -> tuple[dict | None, str | None]:
    """
    Visita la ficha de producto y extrae (macros_dict, ean).
    Devuelve (None, None) si falla.
    """
    if not _navigate(page, product_url, delay=DETAIL_DELAY):
        return None, None

    macros = None
    ean = None

    try:
        ean = page.evaluate(_DETAIL_EAN_JS)
    except Exception:
        pass

    try:
        # Intentar selectores específicos primero
        for sel in _DETAIL_NUTRITION_SELECTORS:
            el = page.query_selector(sel)
            if el:
                text = el.inner_text()
                macros = _parse_nutrition_text(text)
                if macros:
                    break
        # Fallback: toda la página
        if macros is None:
            body = page.evaluate("() => document.body.innerText")
            if body and re.search(r"energ[eé]tico", body, re.IGNORECASE):
                macros = _parse_nutrition_text(body)
    except Exception as e:
        log.debug("Error extrayendo macros de %s: %s", product_url, e)

    return macros, ean


# ── Descubrimiento de categorías ───────────────────────────────────────────

# Lista fija de categorías verificadas de Carrefour España.
# Todas confirmadas con navegación real: cada URL devuelve > 10 productos con precios €/kg.
# Usar como fuente principal cuando el descubrimiento automático encuentre < 10 categorías.
CARREFOUR_CATEGORIES: list[tuple[str, str, float]] = [
    # ── FRESCOS ────────────────────────────────────────────────────────────────
    ("https://www.carrefour.es/supermercado/frescos/carne/cat20018/c",                              "proteina",     300.0),
    ("https://www.carrefour.es/supermercado/frescos/pescado-y-marisco/cat20014/c",                  "proteina",     300.0),
    ("https://www.carrefour.es/supermercado/frescos/charcuteria/cat20017/c",                        "proteina",     100.0),
    ("https://www.carrefour.es/supermercado/frescos/quesos/cat20020/c",                             "lacteo",       150.0),
    ("https://www.carrefour.es/supermercado/frescos/frutas/cat220006/c",                            "fruta",        400.0),
    ("https://www.carrefour.es/supermercado/frescos/verduras-y-hortalizas/cat220014/c",             "verdura",      400.0),
    # ── LA DESPENSA ────────────────────────────────────────────────────────────
    ("https://www.carrefour.es/supermercado/la-despensa/lacteos/cat20011/c",                        "lacteo",       400.0),
    ("https://www.carrefour.es/supermercado/la-despensa/yogures-y-postres/cat390008/c",             "lacteo",       300.0),
    ("https://www.carrefour.es/supermercado/la-despensa/aceites-y-vinagres/cat33207691/c",          "grasa",        30.0),
    ("https://www.carrefour.es/supermercado/la-despensa/aperitivos/cat390001/c",                    "grasa",        40.0),
    ("https://www.carrefour.es/supermercado/la-despensa/conservas-sopas-y-precocinados/cat20013/c", "proteina",     200.0),
    ("https://www.carrefour.es/supermercado/la-despensa/alimentacion/cat20009/c",                   "carbohidrato", 250.0),
    ("https://www.carrefour.es/supermercado/la-despensa/panaderia-bolleria-y-pasteleria/cat21319201/c", "carbohidrato", 150.0),
    ("https://www.carrefour.es/supermercado/la-despensa/desayuno/cat26100390/c",                    "carbohidrato", 150.0),
    ("https://www.carrefour.es/supermercado/la-despensa/huevos/cat20021/c",                         "proteina",     300.0),
    # ── CONGELADOS ────────────────────────────────────────────────────────────
    ("https://www.carrefour.es/supermercado/congelados/pescados-congelados/cat21449156/c",          "proteina",     300.0),
    ("https://www.carrefour.es/supermercado/congelados/aves-y-carne-congelada/cat21449144/c",       "proteina",     300.0),
    ("https://www.carrefour.es/supermercado/congelados/verduras-congeladas/cat21449175/c",          "verdura",      400.0),
]


def _default_categories() -> list[tuple[str, str, float]]:
    """Devuelve la lista fija de categorías verificadas."""
    return CARREFOUR_CATEGORIES


def _discover_categories(page: Page) -> list[tuple[str, str, float]]:
    """
    Navega a la página de alimentación y extrae todas las subcategorías mapeadas.
    """
    start_url = f"{CARREFOUR_BASE}/supermercado/alimentacion/cat20001/c"
    if not _navigate(page, start_url):
        log.warning("No se pudo acceder a la página principal — usando fallback.")
        return _default_categories()

    try:
        links: list[str] = page.evaluate("""
            () => {
                const seen = new Set();
                const result = [];
                for (const a of document.querySelectorAll('a[href]')) {
                    const h = a.href;
                    if (h.includes('/supermercado/') && h.endsWith('/c') && !seen.has(h)) {
                        seen.add(h);
                        result.push(h);
                    }
                }
                return result;
            }
        """)
    except Exception as e:
        log.warning("Error extrayendo links: %s", e)
        return _default_categories()

    categories: list[tuple[str, str, float]] = []
    for url in links:
        path = url.replace(CARREFOUR_BASE, "")
        mapping = _slug_to_category(path)
        if mapping:
            cat, max_g = mapping
            categories.append((url, cat, max_g))
            log.info("  Categoría descubierta: %s → %s", path, cat)

    if len(categories) < 10:
        log.warning(
            "Solo %d categorías descubiertas automáticamente — usando lista fija (%d categorías).",
            len(categories), len(CARREFOUR_CATEGORIES),
        )
        return CARREFOUR_CATEGORIES

    return categories


# ── Scraping de una subcategoría ───────────────────────────────────────────

def _scrape_category(
    page: Page,
    category_url: str,
    internal_cat: str,
    max_grams: float,
    off_client: httpx.Client,
) -> tuple[list[ScrapedProduct], list[PendingProduct]]:
    ready:   list[ScrapedProduct] = []
    pending: list[PendingProduct] = []
    cat_slug = category_url.rstrip("/").rsplit("/", 2)[-2]

    if not _navigate(page, category_url):
        return ready, pending

    if not _wait_products(page):
        log.warning("  Sin productos en %s", category_url)
        return ready, pending

    # Recoger productos con scroll lazy-load + paginación URL (?currentPage=N)
    all_items: list[dict] = []
    _scroll_to_load_all(page)
    try:
        page_items: list[dict] = page.evaluate(_LISTING_EXTRACT_JS)
        all_items.extend(page_items)
    except Exception:
        pass

    page_num = 2
    while len(all_items) < MAX_PRODUCTS_CAT:
        paginated_url = f"{category_url}?currentPage={page_num}"
        if not _navigate(page, paginated_url):
            break
        if not _wait_products(page):
            break
        _scroll_to_load_all(page)
        try:
            page_items = page.evaluate(_LISTING_EXTRACT_JS)
        except Exception:
            break
        existing = {p.get("url") for p in all_items}
        new_items = [i for i in page_items if i.get("url") not in existing]
        if not new_items:
            break
        all_items.extend(new_items)
        page_num += 1

    log.info("  %d productos encontrados en %s (%d páginas)", len(all_items), cat_slug, page_num - 1)

    for raw in all_items[:MAX_PRODUCTS_CAT]:
        name = (raw.get("name") or "").strip()
        if not name:
            continue

        price = _parse_price_per_100g(raw.get("price_per_kg_text"))
        ean   = raw.get("ean")
        url   = raw.get("url") or ""

        if price is None:
            pending.append(PendingProduct(
                mercadona_id=url or name, name=name, ean=ean,
                mercadona_category=cat_slug,
                internal_category=internal_cat,
                price_per_100g=None, reason="price_not_per_kg",
            ))
            continue

        # Intentar macros de la ficha de Carrefour + EAN si no tenemos
        macros: dict | None = None
        if url and (not ean):
            macros, ean = _extract_detail_info(page, url)

        # Fallback a OpenFoodFacts con EAN
        if macros is None and ean:
            off_macros, reason = _fetch_off_macros(off_client, ean)
            if off_macros:
                macros = off_macros
            else:
                pending.append(PendingProduct(
                    mercadona_id=url or name, name=name, ean=ean,
                    mercadona_category=cat_slug,
                    internal_category=internal_cat,
                    price_per_100g=price, reason=reason or "off_not_found",
                ))
                continue

        if macros is None:
            pending.append(PendingProduct(
                mercadona_id=url or name, name=name, ean=ean,
                mercadona_category=cat_slug,
                internal_category=internal_cat,
                price_per_100g=price, reason="no_ean",
            ))
            continue

        if not _validate_macros(internal_cat, macros):
            log.warning(
                "  ⚠ macros inválidos para %s (%s): kcal=%.0f",
                name[:40], internal_cat, macros.get("kcal_per_100g", 0),
            )
            pending.append(PendingProduct(
                mercadona_id=url or name, name=name, ean=ean,
                mercadona_category=cat_slug,
                internal_category=internal_cat,
                price_per_100g=price, reason="invalid_macros",
            ))
            continue

        log.info(
            "  ✓ %s (%.3f€/100g, %.0fkcal, %s)",
            name[:40], price, macros["kcal_per_100g"], internal_cat,
        )
        ready.append(ScrapedProduct(
            name=name,
            category=internal_cat,
            price_per_100g=price,
            max_grams_per_day=max_grams,
            ean=ean,
            source="carrefour",
            supermarket="carrefour",
            **macros,
        ))

    return ready, pending


# ── Generador principal ────────────────────────────────────────────────────

def scrape(
    max_categories: int | None = None,
) -> Generator[tuple[list[ScrapedProduct], list[PendingProduct]], None, None]:
    """
    Generador que scrapeea el catálogo de Carrefour España.
    Yielde (ready_batch, pending_batch) al terminar cada subcategoría.

    Args:
        max_categories: Limita el número de subcategorías (None = todas).
    """
    off_client = httpx.Client(
        headers={"User-Agent": "CalorIA/0.1 (educational project, contact: dev@caloria.local)"},
        timeout=20,
    )

    with sync_playwright() as pw:
        # hook_playwright_context patches all browser launches in this session
        Stealth().hook_playwright_context(pw)
        browser = pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
            locale="es-ES",
            timezone_id="Europe/Madrid",
        )
        page = context.new_page()

        try:
            log.info("Descubriendo categorías de Carrefour...")
            categories = _discover_categories(page)
            if max_categories:
                categories = categories[:max_categories]
            log.info("%d categorías a procesar.", len(categories))

            for url, internal_cat, max_g in categories:
                log.info("Subcategoría: %s → %s", url.split("/")[-2], internal_cat)
                ready, pending = _scrape_category(page, url, internal_cat, max_g, off_client)
                yield ready, pending

        finally:
            browser.close()
            off_client.close()
