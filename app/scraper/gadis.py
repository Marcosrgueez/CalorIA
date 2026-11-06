"""
Scraper de Gadis España (gadisline.com).

Flujo:
  1. Llama al REST API (catalog.gadisline.com) para paginar todos los productos
     sin necesidad de Playwright en la fase de listado.
  2. Intenta extraer macros directamente del JSON de la API.
  3. Para productos sin macros en la API, visita la ficha con Playwright:
       - Hace click en "Análisis Nutricional" → parsea texto del panel
       - Extrae peso neto del tab "Información"
       - EAN desde meta tags o JSON-LD
  4. Fallback OpenFoodFacts por EAN si la ficha tampoco tiene macros.
  5a. Todo OK  → ScrapedProduct (supermarket="gadis") → ProductORM
  5b. Falta algo → PendingProduct
"""

import json
import logging
import random
import re
import time
import unicodedata
from dataclasses import dataclass
from typing import Generator

import httpx
from playwright.sync_api import Page, sync_playwright
from playwright_stealth import Stealth

from app.scraper.mercadona import (
    PendingProduct,
    ScrapedProduct,
    _fetch_off_macros,
    _validate_macros,
)

log = logging.getLogger(__name__)

GADIS_BASE          = "https://www.gadisline.com"
DETAIL_DELAY        = 2.0
BATCH_SIZE          = 25
MAX_PRODUCTS        = 3000

# ── REST API ───────────────────────────────────────────────────────────────
_API_BASE           = "https://catalog.gadisline.com/api/v3/catalog"
_API_PRODUCTS       = f"{_API_BASE}/products/search"
_API_CATEGORIES     = f"{_API_BASE}/categories/search"
_API_ROWS           = 50          # productos por página (máximo soportado)

_API_HEADERS = {
    "store-id":       "891d5c1e-a7a0-4287-9ea3-30c5703a4f63",
    "site-id":        "56df88f9-479f-4361-891e-e1864dba1ca3",
    "time-zone":      "Europe/Madrid",
    "accept-language": "ES",
    "content-type":   "application/json",
    "accept":         "application/json",
    "origin":         "https://www.gadisline.com",
    "referer":        "https://www.gadisline.com/",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}

# Categoría raíz conocida (alimentacion, shelf-stable, interceptada del navegador)
_ROOT_CAT_ID    = "8a98965c-e5d7-44b2-9b22-1f9a6521d916"
# Categoría de frescos (lácteos, carne fresca, fruta, verdura — interceptada del navegador)
_FRESCOS_CAT_ID = "7225b8a2-70a3-4856-99a5-d10e49d8463f"


# ── Mapeo nombre → (categoría interna, max_grams_per_day) ─────────────────
_NAME_MAPPINGS: list[tuple[list[str], str, float]] = [
    # Aceitunas — deben ir ANTES que "anchoa" (marisco) para evitar falsos positivos
    (["aceituna", "aceitunas", "oliva rellena"],                  "grasa",    40.0),
    (["pechuga", "contramuslo", "muslo", "pollo entero", "pavo entero",
      "pavo filetes", "aves", "codorniz", "pichón", "trasero",
      "alita", "cuarto trasero"],                                  "proteina", 300.0),
    (["lomo de cerdo", "solomillo", "costilla", "chuleta", "panceta",
      "secreto", "pluma", "presa", "papada", "carrilera"],        "proteina", 300.0),
    (["ternera", "vacuno", "buey", "carne picada", "hamburguesa de ternera",
      "filete de res", "redondo de", "aguja", "cadera", "tapa",
      "falda", "osobuco"],                                        "proteina", 300.0),
    (["cordero", "conejo"],                                       "proteina", 300.0),
    (["jamón", "jamon", "chorizo", "salchichón", "salchichon",
      "mortadela", "fuet", "sobrasada", "butifarra", "lacón",
      "lacon", "cecina", "lomo ibérico", "morcilla", "salami",
      "pechuga de pavo cocida", "fiambre"],                       "proteina", 100.0),
    (["salmón", "salmon", "merluza", "atún", "atun", "bacalao",
      "dorada", "lubina", "rape", "rodaballo", "trucha",
      "sardina", "boquerón", "boqueron", "anchoa", "caballa",
      "bonito", "mejillón", "mejillon", "berberecho", "almeja",
      "calamar", "sepia", "pulpo", "gamba", "langostino",
      "cigala", "cangrejo", "marisco", "pescado"],                "proteina", 300.0),
    (["huevo", "huevos"],                                         "proteina", 300.0),
    (["leche entera", "leche semidesnatada", "leche desnatada",
      "leche sin lactosa", "leche uht", "bebida de avena",
      "bebida de soja", "bebida de arroz", "bebida de almendra",
      "bebida vegetal"],                                           "lacteo",   400.0),
    (["yogur", "kéfir", "kefir", "bífidus", "bifidus"],          "lacteo",   300.0),
    (["queso"],                                                   "lacteo",   150.0),
    (["nata", "mantequilla", "margarina"],                        "grasa",    30.0),
    (["aceite"],                                                  "grasa",    30.0),
    (["nuez", "almendra", "avellana", "anacardo", "pistacho",
      "cacahuete", "frutos secos", "mix de frutos"],              "grasa",    40.0),
    (["manzana", "pera", "naranja", "mandarina", "plátano",
      "platano", "fresa", "uva", "melocotón", "melocoton",
      "nectarina", "kiwi", "sandía", "sandia", "melón", "melon",
      "cereza", "ciruela", "mango", "piña", "pina", "papaya",
      "frambuesa", "arándano", "arandano", "granada", "higo",
      "aguacate", "limón", "limon"],                             "fruta",    400.0),
    (["lechuga", "espinaca", "acelga", "brócoli", "brocoli",
      "coliflor", "col", "repollo", "pimiento", "tomate",
      "calabacín", "calabacin", "berenjena", "cebolla", "puerro",
      "zanahoria", "patata", "batata", "boniato", "pepino",
      "apio", "alcachofa", "espárrago", "esparrago",
      "judía verde", "judias verdes", "champiñón", "champinon",
      "seta", "remolacha", "rúcula", "rucula", "canónigos",
      "canonigos", "berro"],                                      "verdura",  400.0),
    (["espagueti", "macarrón", "macarron", "fideo", "tallarín",
      "tallarin", "penne", "fusilli", "rigatoni", "hélices",
      "helices", "plumas", "pasta"],                              "carbohidrato", 250.0),
    (["arroz"],                                                   "carbohidrato", 250.0),
    (["pan de molde", "pan tostado", "biscote", "pan integral",
      "rebanada", "tostada"],                                     "carbohidrato", 150.0),
    (["cereal", "muesli", "granola", "avena", "corn flakes",
      "copos de", "chocapic", "frosties"],                        "carbohidrato", 150.0),
    (["azúcar", "azucar"],                                        "carbohidrato", 30.0),
    (["harina"],                                                  "carbohidrato", 150.0),
    (["chocolate", "cacao", "galleta", "galletas", "bizcocho",
      "cookie", "cookies", "barrita", "barritas", "croissant",
      "magdalena", "bollo"],                                      "carbohidrato", 80.0),
    (["pipas", "aperitivo"],                                       "grasa",    40.0),
    (["lenteja", "garbanzo", "judía", "alubia", "guisante",
      "habas", "legumbre", "soja"],                               "legumbre", 200.0),
]


# Macros por 100g para frescos sin ficha nutricional en la web
_MACRO_FALLBACKS: dict[str, dict] = {
    "plátano":    {"kcal_per_100g": 89,  "protein_per_100g": 1.1, "fat_per_100g": 0.3, "carbs_per_100g": 22.8},
    "platano":    {"kcal_per_100g": 89,  "protein_per_100g": 1.1, "fat_per_100g": 0.3, "carbs_per_100g": 22.8},
    "manzana":    {"kcal_per_100g": 52,  "protein_per_100g": 0.3, "fat_per_100g": 0.2, "carbs_per_100g": 13.8},
    "pera ":      {"kcal_per_100g": 57,  "protein_per_100g": 0.4, "fat_per_100g": 0.1, "carbs_per_100g": 15.5},
    "naranja":    {"kcal_per_100g": 47,  "protein_per_100g": 0.9, "fat_per_100g": 0.1, "carbs_per_100g": 11.8},
    "mandarina":  {"kcal_per_100g": 53,  "protein_per_100g": 0.8, "fat_per_100g": 0.3, "carbs_per_100g": 13.3},
    "fresa":      {"kcal_per_100g": 32,  "protein_per_100g": 0.7, "fat_per_100g": 0.3, "carbs_per_100g": 7.7},
    "arándano":   {"kcal_per_100g": 57,  "protein_per_100g": 0.7, "fat_per_100g": 0.3, "carbs_per_100g": 14.5},
    "arandano":   {"kcal_per_100g": 57,  "protein_per_100g": 0.7, "fat_per_100g": 0.3, "carbs_per_100g": 14.5},
    "uva ":       {"kcal_per_100g": 69,  "protein_per_100g": 0.7, "fat_per_100g": 0.2, "carbs_per_100g": 18.1},
    "melocotón":  {"kcal_per_100g": 39,  "protein_per_100g": 0.9, "fat_per_100g": 0.3, "carbs_per_100g": 9.5},
    "melocoton":  {"kcal_per_100g": 39,  "protein_per_100g": 0.9, "fat_per_100g": 0.3, "carbs_per_100g": 9.5},
    "kiwi":       {"kcal_per_100g": 61,  "protein_per_100g": 1.1, "fat_per_100g": 0.5, "carbs_per_100g": 14.7},
    "limón":      {"kcal_per_100g": 29,  "protein_per_100g": 1.1, "fat_per_100g": 0.3, "carbs_per_100g": 9.3},
    "limon":      {"kcal_per_100g": 29,  "protein_per_100g": 1.1, "fat_per_100g": 0.3, "carbs_per_100g": 9.3},
    "aguacate":   {"kcal_per_100g": 160, "protein_per_100g": 2.0, "fat_per_100g": 14.7,"carbs_per_100g": 8.5},
    "mango":      {"kcal_per_100g": 60,  "protein_per_100g": 0.8, "fat_per_100g": 0.4, "carbs_per_100g": 15.0},
    "sandía":     {"kcal_per_100g": 30,  "protein_per_100g": 0.6, "fat_per_100g": 0.2, "carbs_per_100g": 7.6},
    "sandia":     {"kcal_per_100g": 30,  "protein_per_100g": 0.6, "fat_per_100g": 0.2, "carbs_per_100g": 7.6},
    "melón":      {"kcal_per_100g": 34,  "protein_per_100g": 0.8, "fat_per_100g": 0.2, "carbs_per_100g": 8.2},
    "melon":      {"kcal_per_100g": 34,  "protein_per_100g": 0.8, "fat_per_100g": 0.2, "carbs_per_100g": 8.2},
    "tomate":     {"kcal_per_100g": 18,  "protein_per_100g": 0.9, "fat_per_100g": 0.2, "carbs_per_100g": 3.9},
    "zanahoria":  {"kcal_per_100g": 41,  "protein_per_100g": 0.9, "fat_per_100g": 0.2, "carbs_per_100g": 9.6},
    "cebolla":    {"kcal_per_100g": 40,  "protein_per_100g": 1.1, "fat_per_100g": 0.1, "carbs_per_100g": 9.3},
    "puerro":     {"kcal_per_100g": 61,  "protein_per_100g": 1.5, "fat_per_100g": 0.3, "carbs_per_100g": 14.2},
    "patata":     {"kcal_per_100g": 77,  "protein_per_100g": 2.0, "fat_per_100g": 0.1, "carbs_per_100g": 17.5},
    "batata":     {"kcal_per_100g": 86,  "protein_per_100g": 1.6, "fat_per_100g": 0.1, "carbs_per_100g": 20.1},
    "calabacín":  {"kcal_per_100g": 17,  "protein_per_100g": 1.2, "fat_per_100g": 0.3, "carbs_per_100g": 3.1},
    "calabacin":  {"kcal_per_100g": 17,  "protein_per_100g": 1.2, "fat_per_100g": 0.3, "carbs_per_100g": 3.1},
    "pimiento":   {"kcal_per_100g": 31,  "protein_per_100g": 1.0, "fat_per_100g": 0.3, "carbs_per_100g": 6.0},
    "berenjena":  {"kcal_per_100g": 25,  "protein_per_100g": 1.0, "fat_per_100g": 0.2, "carbs_per_100g": 5.9},
    "lechuga":    {"kcal_per_100g": 15,  "protein_per_100g": 1.4, "fat_per_100g": 0.2, "carbs_per_100g": 2.9},
    "espinaca":   {"kcal_per_100g": 23,  "protein_per_100g": 2.9, "fat_per_100g": 0.4, "carbs_per_100g": 3.6},
    "brócoli":    {"kcal_per_100g": 34,  "protein_per_100g": 2.8, "fat_per_100g": 0.4, "carbs_per_100g": 6.6},
    "brocoli":    {"kcal_per_100g": 34,  "protein_per_100g": 2.8, "fat_per_100g": 0.4, "carbs_per_100g": 6.6},
    "brécol":     {"kcal_per_100g": 34,  "protein_per_100g": 2.8, "fat_per_100g": 0.4, "carbs_per_100g": 6.6},
    "brecol":     {"kcal_per_100g": 34,  "protein_per_100g": 2.8, "fat_per_100g": 0.4, "carbs_per_100g": 6.6},
    "coliflor":   {"kcal_per_100g": 25,  "protein_per_100g": 1.9, "fat_per_100g": 0.3, "carbs_per_100g": 5.0},
    "pepino":     {"kcal_per_100g": 16,  "protein_per_100g": 0.7, "fat_per_100g": 0.1, "carbs_per_100g": 3.6},
    "champiñón":  {"kcal_per_100g": 22,  "protein_per_100g": 3.1, "fat_per_100g": 0.3, "carbs_per_100g": 3.3},
    "champinon":  {"kcal_per_100g": 22,  "protein_per_100g": 3.1, "fat_per_100g": 0.3, "carbs_per_100g": 3.3},
    "pechuga":    {"kcal_per_100g": 110, "protein_per_100g": 23.0,"fat_per_100g": 1.0, "carbs_per_100g": 0.0},
    "pollo":      {"kcal_per_100g": 165, "protein_per_100g": 20.0,"fat_per_100g": 9.0, "carbs_per_100g": 0.0},
    "ternera":    {"kcal_per_100g": 215, "protein_per_100g": 26.0,"fat_per_100g": 12.0,"carbs_per_100g": 0.0},
    "cerdo":      {"kcal_per_100g": 242, "protein_per_100g": 27.0,"fat_per_100g": 14.0,"carbs_per_100g": 0.0},
    "salmón":     {"kcal_per_100g": 208, "protein_per_100g": 20.0,"fat_per_100g": 13.0,"carbs_per_100g": 0.0},
    "salmon":     {"kcal_per_100g": 208, "protein_per_100g": 20.0,"fat_per_100g": 13.0,"carbs_per_100g": 0.0},
    "merluza":    {"kcal_per_100g": 86,  "protein_per_100g": 17.5,"fat_per_100g": 1.5, "carbs_per_100g": 0.0},
    "leche entera":  {"kcal_per_100g": 64, "protein_per_100g": 3.2, "fat_per_100g": 3.6, "carbs_per_100g": 4.8},
    "leche semi":    {"kcal_per_100g": 46, "protein_per_100g": 3.3, "fat_per_100g": 1.5, "carbs_per_100g": 4.8},
    "yogur":      {"kcal_per_100g": 59,  "protein_per_100g": 3.5, "fat_per_100g": 3.2, "carbs_per_100g": 4.7},
    "queso":      {"kcal_per_100g": 350, "protein_per_100g": 22.0,"fat_per_100g": 28.0,"carbs_per_100g": 2.0},
    "huevo":      {"kcal_per_100g": 155, "protein_per_100g": 12.6,"fat_per_100g": 10.6,"carbs_per_100g": 1.1},
}


def _get_fallback_macros(name: str) -> dict | None:
    nl = unicodedata.normalize("NFC", name.lower())
    for keyword, macros in _MACRO_FALLBACKS.items():
        kw = unicodedata.normalize("NFC", keyword.strip())
        if kw in nl:
            return macros
    return None


def _name_to_category(name: str) -> tuple[str, float] | None:
    nl = name.lower()
    for keywords, cat, max_g in _NAME_MAPPINGS:
        if any(kw in nl for kw in keywords):
            return cat, max_g
    return None


# ── Extracción de peso desde el nombre ────────────────────────────────────

def _extract_weight_g(name: str) -> float | None:
    nl = name.lower().replace("\xa0", " ")
    m = re.search(r"([\d]+[,.]?[\d]*)\s*kg\b", nl)
    if m:
        return float(m.group(1).replace(",", ".")) * 1000
    m = re.search(r"([\d]+[,.]?[\d]*)\s*g\b", nl)
    if m:
        val = float(m.group(1).replace(",", "."))
        if val > 5:
            return val
    m = re.search(r"([\d]+[,.]?[\d]*)\s*l\b", nl)
    if m:
        return float(m.group(1).replace(",", ".")) * 1000
    m = re.search(r"([\d]+[,.]?[\d]*)\s*ml\b", nl)
    if m:
        return float(m.group(1).replace(",", "."))
    m = re.search(r"([\d]+[,.]?[\d]*)\s*cl\b", nl)
    if m:
        return float(m.group(1).replace(",", ".")) * 10
    return None


# ── Precio por 100g ────────────────────────────────────────────────────────

def _parse_price_text(text: str | None) -> float | None:
    if not text:
        return None
    text = text.replace("\xa0", " ").strip()
    m = re.search(r"([\d]+[,.][\d]+|[\d]+)\s*€", text)
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", "."))
    except ValueError:
        return None


def _price_per_100g(
    price_text: str | None,
    price_kg_text: str | None,
    product_name: str,
) -> float | None:
    if price_kg_text:
        kg = price_kg_text.replace("\xa0", " ").lower()
        val = _parse_price_text(price_kg_text)
        if val is not None:
            if "/kg" in kg or "el kg" in kg or "/ kg" in kg:
                return round(val / 10, 4)
            if "litro" in kg or "/ litro" in kg or "el litro" in kg:
                return round(val / 10, 4)
            if "100 g" in kg or "100g" in kg or "/100" in kg:
                return round(val, 4)

    unit_price = _parse_price_text(price_text)
    if unit_price is not None:
        weight_g = _extract_weight_g(product_name)
        if weight_g and weight_g > 0:
            return round(unit_price / (weight_g / 100), 4)
    return None


# ── Parsing de macros ──────────────────────────────────────────────────────

_NUT_PATTERNS: list[tuple[str, str]] = [
    ("kcal",  r"[Ee]nerg[íi]a\s*:\s*\(?([0-9][,.\d]*)\s*kcal\)?"),
    ("kcal",  r"energ[eé]tico[^0-9]{0,80}?([\d][,.\d]*)\s*kcal"),
    ("kcal",  r"([\d][,.\d]*)\s*kcal"),
    ("prot",  r"[Pp]rote[íi]nas?\s*:\s*\(?([0-9][,.\d]*)\s*g\)?"),
    ("prot",  r"prote[íi]na[s]?[^0-9]{0,60}?([\d][,.\d]*)\s*g"),
    ("fat",   r"[Gg]rasas\s*:\s*\(?([0-9][,.\d]*)\s*g\)?"),
    ("fat",   r"gras[as][^0-9]{0,60}?([\d][,.\d]*)\s*g"),
    ("carbs", r"[Hh]idratos\s+de\s+carbono\s*:\s*\(?([0-9][,.\d]*)\s*g\)?"),
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
            val = _find(pat)
            if val is not None:
                results[key] = val

    if results.get("kcal") is None:
        return None
    if results.get("fat") is None:
        return None
    return {
        "kcal_per_100g":    float(results["kcal"]),
        "protein_per_100g": float(results.get("prot") or 0.0),
        "fat_per_100g":     float(results["fat"]),
        "carbs_per_100g":   float(results.get("carbs") or 0.0),
    }


# ── Extracción de macros desde JSON de la API ──────────────────────────────

def _macros_from_api_product(product: dict) -> dict | None:
    """
    Intenta extraer valores nutricionales directamente del dict de la API.
    La API de Gadis puede incluir un objeto 'nutritional_information' o similar.
    """
    # Buscar objeto de nutrición en varias claves posibles
    nut: dict = {}
    for key in (
        "nutritional_information", "nutritional_info", "nutrition",
        "nutritional_values", "nutrients", "nutritional_data",
    ):
        candidate = product.get(key)
        if isinstance(candidate, dict):
            nut = candidate
            break
    if not nut and isinstance(product.get("details"), dict):
        nut = product["details"].get("nutrition") or {}

    def _get(obj: dict, *keys: str) -> float | None:
        for k in keys:
            v = obj.get(k)
            if v is not None:
                try:
                    f = float(str(v).replace(",", "."))
                    if f >= 0:
                        return f
                except (ValueError, TypeError):
                    pass
        return None

    kcal  = _get(nut, "energy_kcal", "calories", "kcal", "energyKcal", "energy",
                 "valor_energetico", "energía", "energia")
    prot  = _get(nut, "proteins", "protein", "proteinas", "proteínas")
    fat   = _get(nut, "fats", "fat", "total_fat", "grasas", "totalFat")
    carbs = _get(nut, "carbohydrates", "carbohidratos", "hidratos", "carbs")

    if kcal is not None and fat is not None:
        return {
            "kcal_per_100g":    kcal,
            "protein_per_100g": prot or 0.0,
            "fat_per_100g":     fat,
            "carbs_per_100g":   carbs or 0.0,
        }
    return None


# ── REST API: categorías y productos ──────────────────────────────────────

def _discover_category_ids(client: httpx.Client) -> list[str]:
    """
    Llama a la API de categorías para obtener IDs de primer nivel.
    En la práctica devuelve lista vacía, así que se usa la raíz conocida.
    """
    try:
        resp = client.post(_API_CATEGORIES, headers=_API_HEADERS, json={}, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            cats = data.get("categories") or data.get("results") or data.get("items") or []
            ids = [c["id"] for c in cats if isinstance(c, dict) and c.get("id")]
            if ids:
                log.info("Categorías Gadis descubiertas: %d", len(ids))
                return ids
    except Exception as e:
        log.warning("Categories API: %s", e)
    # Frescos primero (lácteos, carne, fruta, verdura), luego alimentación shelf-stable
    log.info("Usando categorías conocidas: frescos + raíz.")
    return [_FRESCOS_CAT_ID, _ROOT_CAT_ID]


def _fetch_products_page(
    client: httpx.Client,
    category_id: str,
    page_number: int,
) -> tuple[list[dict], int]:
    """
    Pide una página de productos al REST API de Gadis.
    Devuelve (productos, total_pages).
    Estructura real: {elements: [...], page: {total_pages: N, total_elements: M}}
    """
    try:
        resp = client.post(
            _API_PRODUCTS,
            headers=_API_HEADERS,
            params={
                "page_number":   page_number,
                "rows_per_page": _API_ROWS,
                "keep_request":  "false",
                "order_field":   "relevance",
                "sort_type":     "asc",
            },
            json={"minimum_should_match": 1, "category_ids": [category_id]},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        # API real: productos en "elements", paginación en "page"
        products = data.get("elements") or []
        page_info = data.get("page") or {}
        total_pages = int(page_info.get("total_pages") or 1)
        return products, total_pages
    except Exception as e:
        log.warning("API error page=%d cat=%.8s: %s", page_number, category_id, e)
    return [], 0


def _collect_all_products(
    client: httpx.Client,
    category_ids: list[str],
    max_total: int,
) -> list[dict]:
    """Pagina por todas las categorías y devuelve todos los productos únicos."""
    all_products: list[dict] = []
    seen: set[str] = set()

    for cat_id in category_ids:
        # Obtener primera página para saber total_pages
        items, total_pages = _fetch_products_page(client, cat_id, 0)
        log.info("Categoría %.8s: %d páginas totales.", cat_id, total_pages)

        for page in range(total_pages):
            if page > 0:
                items, _ = _fetch_products_page(client, cat_id, page)
            if not items:
                log.info("Página %d vacía, parando.", page)
                break

            new = 0
            for item in items:
                pid = str(item.get("id") or item.get("slug") or "")
                if pid and pid in seen:
                    continue
                if pid:
                    seen.add(pid)
                all_products.append(item)
                new += 1
                if len(all_products) >= max_total:
                    break

            log.info(
                "API cat=%.8s página=%d/%d: +%d (total=%d)",
                cat_id, page, total_pages - 1, new, len(all_products),
            )
            if len(all_products) >= max_total:
                break
            time.sleep(0.3 + random.uniform(0, 0.2))

    return all_products


# ── Normalización de producto de API a formato interno ────────────────────

def _normalize_api_product(product: dict) -> dict:
    """
    Convierte un dict de la API de Gadis al shape usado internamente:
    {name, price_text, price_kg_text, url, api_data}

    Estructura real de la API (interceptada):
      commercial_description: [{language: "ES", value: "Nombre del producto"}]
      price:                  4.25   (precio unitario, float)
      price_kilo_litre:       4.25   (precio por kg/litro, float)
      price_kilo_litre_suffix: [{language: "ES", value: "el litro"}]
      slug:                   "/aceite-oliva-0-4-abril-botella-1-l"
    """
    # Nombre desde commercial_description (filtrar por ES, o tomar el primero)
    descriptions = product.get("commercial_description") or []
    name = ""
    for d in descriptions:
        if isinstance(d, dict) and d.get("language") == "ES":
            name = (d.get("value") or "").strip()
            break
    if not name and descriptions:
        name = (descriptions[0].get("value") or "").strip()

    # URL desde slug
    slug = product.get("slug") or ""
    url  = f"{GADIS_BASE}{slug}" if slug.startswith("/") else (
           f"{GADIS_BASE}/{slug}" if slug else ""
    )

    # Precio unitario
    price_val: float | None = None
    raw_price = product.get("price")
    if raw_price is not None:
        try:
            price_val = float(raw_price)
        except (ValueError, TypeError):
            pass
    price_text = f"{price_val} €" if price_val is not None else None

    # Precio de referencia (price_kilo_litre) + sufijo de unidad
    # Sufijo: "el litro", "el kilo", "la docena", "100g", etc.
    price_kg_text: str | None = None
    ref_val = product.get("price_kilo_litre")
    suffix_list = product.get("price_kilo_litre_suffix") or []
    suffix_str = ""
    for s in suffix_list:
        if isinstance(s, dict) and s.get("language") == "ES":
            suffix_str = (s.get("value") or "").lower()
            break
    if not suffix_str and suffix_list:
        suffix_str = str(suffix_list[0].get("value", "")).lower() if isinstance(suffix_list[0], dict) else ""

    if ref_val is not None:
        # Solo usar price_kilo_litre si el sufijo indica /kg o /litro
        if any(kw in suffix_str for kw in ("kilo", "/kg", "kg")):
            price_kg_text = f"{ref_val} €/kg"
        elif any(kw in suffix_str for kw in ("litro", "litr")):
            price_kg_text = f"{ref_val} €/ litro"
        elif any(kw in suffix_str for kw in ("100g", "100 g", "/100")):
            price_kg_text = f"{ref_val} €/100g"
        # Si el sufijo es "la docena", "la unidad", etc. → no sirve como €/kg

    # Frescos vendidos por peso: nombre termina en "kilo" → precio unitario es €/kg
    if price_kg_text is None and price_val is not None:
        if re.search(r"\bkilo\b", name, re.IGNORECASE):
            price_kg_text = f"{price_val} €/kg"

    return {
        "name":          name,
        "price_text":    price_text,
        "price_kg_text": price_kg_text,
        "url":           url,
        "api_data":      product,
    }


# ── Helpers de página (Playwright) ────────────────────────────────────────

def _navigate(page: Page, url: str, delay: float = 2.5) -> bool:
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=35_000)
        time.sleep(delay + random.uniform(0, 0.8))
        return True
    except Exception as e:
        log.warning("Error navegando a %s: %s", url, e)
        return False


def _click_tab(page: Page, tab_name: str) -> bool:
    try:
        btn = page.locator(f'button[class*=Tabs_tabTitle]:has-text("{tab_name}")').first
        if btn.count() == 0:
            return False
        btn.click()
        time.sleep(1.5)
        return True
    except Exception:
        return False


def _get_tab_text(page: Page) -> str:
    try:
        return page.evaluate(
            '() => document.querySelector("[class*=Tabs_content]")?.innerText || ""'
        )
    except Exception:
        return ""


def _extract_net_weight_from_info(info_text: str) -> float | None:
    m = re.search(
        r"cantidad\s+neta[^\n]*\n\s*([\d][,.\d]*)\s*(g|kg|l|ml|cl)\b",
        info_text, re.IGNORECASE,
    )
    if not m:
        return None
    val  = float(m.group(1).replace(",", "."))
    unit = m.group(2).lower()
    if unit == "kg":  return val * 1000
    if unit == "g":   return val
    if unit == "l":   return val * 1000
    if unit == "ml":  return val
    if unit == "cl":  return val * 10
    return None


def _extract_detail_info(
    page: Page, product_url: str
) -> tuple[dict | None, str | None, float | None]:
    """Visita la ficha y extrae (macros_dict, ean, net_weight_g)."""
    if not _navigate(page, product_url, delay=DETAIL_DELAY):
        return None, None, None

    macros: dict | None = None
    ean: str | None = None
    net_weight_g: float | None = None

    if _click_tab(page, "Análisis Nutricional"):
        nut_text = _get_tab_text(page)
        if nut_text:
            macros = _parse_nutrition_text(nut_text)

    if _click_tab(page, "Información"):
        info_text = _get_tab_text(page)
        if info_text:
            net_weight_g = _extract_net_weight_from_info(info_text)

    try:
        ean = page.evaluate("""
            () => {
                for (const n of ['product:retailer_item_id','product:ean','og:upc']) {
                    const el = document.querySelector(`meta[property="${n}"], meta[name="${n}"]`);
                    if (el && /^\\d{8,14}$/.test(el.content)) return el.content;
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
        """)
    except Exception:
        pass

    if macros is None:
        try:
            body = page.evaluate("() => document.body.innerText")
            if body and re.search(r"energ[íi]a|kcal|prote[íi]na", body, re.IGNORECASE):
                macros = _parse_nutrition_text(body)
        except Exception:
            pass

    return macros, ean, net_weight_g


# ── Generador principal ────────────────────────────────────────────────────

def scrape(
    max_products: int | None = None,
) -> Generator[tuple[list[ScrapedProduct], list[PendingProduct]], None, None]:
    """
    Generador que scrapeea el catálogo de Gadis.
    Fase 1 vía REST API (sin Playwright); Fase 2 vía Playwright solo si faltan macros.
    Yielde (ready_batch, pending_batch) cada BATCH_SIZE productos procesados.
    """
    limit = max_products or MAX_PRODUCTS

    gadis_client = httpx.Client(headers=_API_HEADERS, timeout=20)
    off_client   = httpx.Client(
        headers={"User-Agent": "CalorIA/0.1 (educational project, contact: dev@caloria.local)"},
        timeout=20,
    )

    # ── Fase 1: Recopilar todos los productos vía REST API ─────────────────
    log.info("Descubriendo categorías Gadis vía API...")
    category_ids = _discover_category_ids(gadis_client)

    log.info("Paginando productos (límite=%d)...", limit)
    raw_api_products = _collect_all_products(gadis_client, category_ids, limit)
    log.info("%d productos obtenidos de la API.", len(raw_api_products))

    gadis_client.close()

    if not raw_api_products:
        log.error("La API de Gadis no devolvió productos. Abortando.")
        off_client.close()
        return

    # Normalizar al shape interno
    raw_items = [_normalize_api_product(p) for p in raw_api_products]

    # Separar productos que necesitan visita de detalle (sin macros en API)
    items_with_api_macros: list[tuple[dict, dict]] = []   # (raw, macros)
    items_need_detail:     list[dict] = []

    for raw in raw_items:
        api_macros = _macros_from_api_product(raw["api_data"])
        if api_macros:
            items_with_api_macros.append((raw, api_macros))
        else:
            items_need_detail.append(raw)

    log.info(
        "Con macros en API: %d | Necesitan detalle: %d",
        len(items_with_api_macros), len(items_need_detail),
    )

    # ── Fase 2: Procesar ──────────────────────────────────────────────────
    ready:   list[ScrapedProduct] = []
    pending: list[PendingProduct] = []
    idx = 0

    def _process_raw(raw: dict, macros: dict | None, ean: str | None) -> None:
        name = raw.get("name") or ""
        url  = raw.get("url") or ""

        cat_result = _name_to_category(name)
        if cat_result is None:
            log.debug("Sin categoría para: %.50s", name)
            pending.append(PendingProduct(
                mercadona_id=url or name, name=name, ean=ean,
                mercadona_category="unknown", internal_category="unknown",
                price_per_100g=None, reason="no_category",
            ))
            return

        internal_cat, max_grams = cat_result
        price = _price_per_100g(raw.get("price_text"), raw.get("price_kg_text"), name)

        if price is None:
            pending.append(PendingProduct(
                mercadona_id=url or name, name=name, ean=ean,
                mercadona_category=internal_cat, internal_category=internal_cat,
                price_per_100g=None, reason="no_price_per_100g",
            ))
        elif macros is None:
            fallback = _get_fallback_macros(name)
            if fallback and _validate_macros(internal_cat, fallback):
                log.info("  ✓ [fallback] %.40s (%.3f€/100g %.0fkcal %s)",
                         name, price, fallback["kcal_per_100g"], internal_cat)
                ready.append(ScrapedProduct(
                    name=name, category=internal_cat,
                    price_per_100g=price, max_grams_per_day=max_grams,
                    ean=ean, source="gadis_estimated", supermarket="gadis", **fallback,
                ))
                return
            pending.append(PendingProduct(
                mercadona_id=url or name, name=name, ean=ean,
                mercadona_category=internal_cat, internal_category=internal_cat,
                price_per_100g=price, reason="no_macros",
            ))
        elif not _validate_macros(internal_cat, macros):
            log.warning("  ⚠ macros inválidos %s (%.0fkcal)", name[:40], macros.get("kcal_per_100g", 0))
            pending.append(PendingProduct(
                mercadona_id=url or name, name=name, ean=ean,
                mercadona_category=internal_cat, internal_category=internal_cat,
                price_per_100g=price, reason="invalid_macros",
            ))
        else:
            log.info("  ✓ %.40s (%.3f€/100g %.0fkcal %s)", name, price, macros["kcal_per_100g"], internal_cat)
            ready.append(ScrapedProduct(
                name=name, category=internal_cat,
                price_per_100g=price, max_grams_per_day=max_grams,
                ean=ean, source="gadis", supermarket="gadis", **macros,
            ))

    # Productos con macros de la API (no necesitan Playwright)
    for raw, api_macros in items_with_api_macros:
        _process_raw(raw, api_macros, ean=None)
        idx += 1
        if idx % BATCH_SIZE == 0:
            log.info("  [%d] listos=%d pendientes=%d", idx, len(ready), len(pending))
            yield list(ready), list(pending)
            ready.clear(); pending.clear()

    # Productos que necesitan visita de detalle
    if items_need_detail:
        log.info("Abriendo Playwright para %d fichas de detalle...", len(items_need_detail))
        with sync_playwright() as pw:
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
                for raw in items_need_detail:
                    name = raw.get("name") or ""
                    url  = raw.get("url") or ""
                    macros: dict | None = None
                    ean: str | None = None

                    if url:
                        macros, ean, net_weight_g = _extract_detail_info(page, url)
                        # Refinar precio con peso neto de la ficha
                        if raw.get("price_text") and not raw.get("price_kg_text") and net_weight_g:
                            unit_price = _parse_price_text(raw["price_text"])
                            if unit_price and net_weight_g > 0:
                                raw = dict(raw)
                                raw["price_kg_text"] = f"{round(unit_price / (net_weight_g / 100), 4)} €/100g"

                    # OpenFoodFacts si sigue sin macros
                    if macros is None and ean:
                        off_macros, _ = _fetch_off_macros(off_client, ean)
                        if off_macros:
                            macros = off_macros

                    _process_raw(raw, macros, ean)
                    idx += 1
                    if idx % BATCH_SIZE == 0:
                        log.info("  [%d] listos=%d pendientes=%d", idx, len(ready), len(pending))
                        yield list(ready), list(pending)
                        ready.clear(); pending.clear()
            finally:
                browser.close()

    off_client.close()

    if ready or pending:
        yield list(ready), list(pending)
