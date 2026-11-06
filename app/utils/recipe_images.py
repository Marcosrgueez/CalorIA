import os
from functools import lru_cache

import httpx

UNSPLASH_ACCESS_KEY: str = os.getenv("UNSPLASH_ACCESS_KEY", "")

_TRANSLATIONS: dict[str, str] = {
    "gambón":    "shrimp",
    "gambas":    "shrimp",
    "gamba":     "shrimp",
    "salmón":    "salmon",
    "salmon":    "salmon",
    "atún":      "tuna",
    "merluza":   "hake fish",
    "sardina":   "sardines",
    "caballa":   "mackerel",
    "bacalao":   "cod fish",
    "panga":     "fish fillet",
    "calamar":   "squid",
    "mejillón":  "mussels",
    "sepia":     "cuttlefish",
    "pechuga":   "chicken breast",
    "pollo":     "chicken",
    "pavo":      "turkey",
    "ternera":   "beef",
    "cerdo":     "pork",
    "lomo":      "pork loin",
    "carne picada": "ground meat",
    "huevo":     "eggs",
    "clara":     "egg whites",
    "lentejas":  "lentils",
    "garbanzos": "chickpeas",
    "alubia":    "beans",
    "arroz":     "rice",
    "pasta":     "pasta",
    "ensalada":  "salad",
    "sopa":      "soup",
    "yogur":     "yogurt",
    "avena":     "oatmeal",
    "tostadas":  "toast",
    "revuelto":  "scrambled eggs",
    "tortilla":  "omelette",
    "wrap":      "wrap",
    "sandwich":  "sandwich",
    "bocadillo": "sandwich",
    "espinacas": "spinach",
    "brócoli":   "broccoli",
    "pimientos": "peppers",
}


def _translate_query(name: str) -> str:
    name_lower = name.lower()
    for es, en in _TRANSLATIONS.items():
        if es in name_lower:
            return f"{en} dish healthy food"
    return f"{name} food dish"


@lru_cache(maxsize=300)
def get_recipe_image(recipe_name: str) -> str:
    """Busca foto en Unsplash para la receta. Devuelve URL small o ''."""
    if not UNSPLASH_ACCESS_KEY:
        return ""
    try:
        query = _translate_query(recipe_name)
        r = httpx.get(
            "https://api.unsplash.com/search/photos",
            params={"query": query, "per_page": 1, "orientation": "landscape"},
            headers={"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"},
            timeout=5,
        )
        if r.status_code == 200:
            results = r.json().get("results", [])
            if results:
                return results[0]["urls"]["small"]
    except Exception:
        pass
    return ""
