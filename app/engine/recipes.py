"""
Catálogo de recetas predefinidas para CalorIA.

Cada receta define un plato real con sus ingredientes base.
El motor puede usar estas recetas como plantillas para generar
menús coherentes y variados.

resolve_and_verify(db) valida el catálogo contra la BD real:
para cada ingrediente prueba las keywords en orden de preferencia
(con exclusiones) y reporta qué recetas están completamente disponibles.
"""

from __future__ import annotations

import os
import random
from dataclasses import dataclass, field


# ─────────────────────────────────────────────
# MODELO ML DE RECOMENDACIÓN (carga lazy en primer uso)
# ─────────────────────────────────────────────

_ML_MODEL_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "models", "recipe_recommender.pkl"
)
_ml_bundle: dict | None = None
_ml_loaded = False  # evita reintentar si ya falló


def _load_ml_model() -> dict | None:
    global _ml_bundle, _ml_loaded
    if _ml_loaded:
        return _ml_bundle
    _ml_loaded = True
    try:
        import joblib
        if os.path.exists(_ML_MODEL_PATH):
            _ml_bundle = joblib.load(_ML_MODEL_PATH)
    except Exception:
        pass  # joblib no instalado o modelo corrupto — ignorar silenciosamente
    return _ml_bundle


# ─────────────────────────────────────────────
# BLACKLIST DE PRODUCTOS NO APTOS PARA RECETAS
# ─────────────────────────────────────────────

# Productos que no deben aparecer en recetas automáticas aunque sean los más
# baratos de su categoría (preparados, fritos, no ingredientes base, etc.)
PRODUCT_BLACKLIST = [
    "patatas prefritas",   # precocinado frito
    "patatas fritas",      # snack, no verdura
    "salteado de patata",  # preparado
    "relleno fajitas",     # preparado
    "wok de verduras",     # preparado
    "menestra",            # preparado (puede quedarse si hay pocas verduras)
    "ensaladilla",   # preparado con mayonesa, no verdura real
    "margarina",     # no es aceite, evitar como grasa en recetas
    "empanadilla",   # preparado frito, no ingrediente base
    "lasaña",        # plato preparado, no ingrediente
    "rollito",       # preparado frito
    "gyoza",         # preparado oriental
    "croqueta",      # preparado frito
    "nugget",        # procesado
]


# ─────────────────────────────────────────────
# ESTRUCTURAS DE DATOS
# ─────────────────────────────────────────────

@dataclass
class RecipeIngredient:
    preferred_keywords: list[str]                      # keywords en orden de preferencia
    category: str                                      # categoría esperada del producto
    base_grams: float                                  # gramos en la receta base
    exclude_keywords: list[str] = field(default_factory=list)  # términos a excluir del nombre

    @property
    def display_keyword(self) -> str:
        """Keyword principal para mostrar en tablas."""
        return self.preferred_keywords[0] if self.preferred_keywords else "?"


@dataclass
class Recipe:
    name: str
    meal_type: str                          # "desayuno" | "comida" | "cena"
    ingredients: list[RecipeIngredient] = field(default_factory=list)
    instructions: list[str] = field(default_factory=list)
    prep_time_min: int = 15
    image_url: str = ""


# ─────────────────────────────────────────────
# HELPERS DE CONSTRUCCIÓN
# ─────────────────────────────────────────────

def _ing(
    keywords: str | list[str],
    category: str,
    grams: float,
    exclude: list[str] | None = None,
) -> RecipeIngredient:
    """Shorthand para construir RecipeIngredient."""
    kws = [keywords] if isinstance(keywords, str) else keywords
    return RecipeIngredient(
        preferred_keywords=kws,
        category=category,
        base_grams=grams,
        exclude_keywords=exclude or [],
    )


# ─────────────────────────────────────────────
# CATÁLOGO — 29 RECETAS
# ─────────────────────────────────────────────

RECIPES: list[Recipe] = [

    # ── DESAYUNOS ──────────────────────────────────────────────────────────

    Recipe("Avena con leche", "desayuno", [
        _ing("avena",                  "carbohidrato", 80.0),
        _ing("leche",                  "lacteo",       250.0),
    ]),
    Recipe("Avena con fruta", "desayuno", [
        _ing("avena",                  "carbohidrato", 70.0),
        _ing("fruta",                  "fruta",        120.0),
        _ing("leche",                  "lacteo",       200.0),
    ]),
    Recipe("Yogur con avena", "desayuno", [
        _ing("yogur",                  "lacteo",       200.0),
        _ing("avena",                  "carbohidrato", 60.0),
    ]),
    Recipe("Yogur con fruta", "desayuno", [
        _ing("yogur",                  "lacteo",       200.0),
        _ing("fruta",                  "fruta",        120.0),
    ]),
    Recipe("Leche con cereales", "desayuno", [
        _ing("leche",                  "lacteo",       250.0),
        # "cereal" en carbohidrato, excluyendo pan (que también tiene "cereal" en su nombre)
        _ing("cereal",                 "carbohidrato", 60.0, exclude=["pan"]),
    ]),
    Recipe("Tostadas con aceite", "desayuno", [
        # pan de molde preferido; excluir rallado
        _ing("pan",                    "carbohidrato", 100.0, exclude=["rallado"]),
        _ing("aceite",                 "grasa",        10.0),
    ]),
    Recipe("Tostadas con tomate", "desayuno", [
        _ing("pan",                    "carbohidrato", 100.0, exclude=["rallado"]),
        _ing("tomate",                 "verdura",      80.0),
        _ing("aceite",                 "grasa",        10.0),
    ]),
    Recipe("Sandwich desayuno", "desayuno", [
        _ing("pan",                    "carbohidrato", 100.0, exclude=["rallado"]),
        # jamón cocido preferido; fallback a jamón de pavo
        _ing(["jamón cocido", "jamón"],"proteina",     60.0),
    ]),
    Recipe("Avena con bebida de avena", "desayuno", [
        _ing("bebida de avena",        "lacteo",       250.0),
        _ing(["copos de avena", "avena"], "carbohidrato", 60.0),
    ]),
    Recipe("Yogur con cereales", "desayuno", [
        _ing("yogur",                  "lacteo",       200.0),
        _ing(["corn flakes", "cereales copos", "cereal"],
             "carbohidrato",  60.0, exclude=["pan", "molde"]),
    ]),
    Recipe("Yogur griego con mango", "desayuno", [
        _ing(["yogur griego con mango", "yogur griego"], "lacteo", 250.0),
    ]),
    Recipe("Yogur con frutos rojos", "desayuno", [
        _ing("yogur",                  "lacteo",       200.0, exclude=["griego", "mango"]),
        _ing(["frutos rojos", "mix frutos"], "fruta",  120.0),
    ]),
    Recipe("Yogur con tropical", "desayuno", [
        _ing("yogur",                  "lacteo",       200.0, exclude=["griego", "mango"]),
        _ing(["frutas tropical", "mix tropical", "tropical"], "fruta", 120.0),
    ]),
    Recipe("Yogur con arándanos", "desayuno", [
        _ing("yogur",                  "lacteo",       200.0, exclude=["griego", "mango"]),
        _ing(["arándanos", "arandanos"], "fruta",      120.0),
    ]),
    Recipe("Avena con frutos rojos y leche", "desayuno", [
        _ing(["copos de avena", "avena"], "carbohidrato", 70.0),
        _ing(["frutos rojos", "mix frutos"], "fruta",    100.0),
        _ing("leche",                  "lacteo",         150.0),
    ]),
    Recipe("Avena con tropical y leche", "desayuno", [
        _ing(["copos de avena", "avena"], "carbohidrato", 70.0),
        _ing(["frutas tropical", "mix tropical", "tropical"], "fruta", 100.0),
        _ing("leche",                  "lacteo",         150.0),
    ]),
    Recipe("Tostadas con jamón cocido", "desayuno", [
        _ing("pan",                    "carbohidrato", 100.0, exclude=["rallado"]),
        _ing(["jamón cocido", "jamón"], "proteina",     60.0),
    ]),
    Recipe("Leche con galletas maría", "desayuno", [
        _ing("leche",                  "lacteo",       250.0),
        _ing(["galletas maría", "galleta"],
             "carbohidrato",  60.0, exclude=["chocolate", "integral", "digestive"]),
    ]),
    Recipe("Yogur con cereales y frutos rojos", "desayuno", [
        _ing("yogur",                  "lacteo",       150.0, exclude=["griego", "mango"]),
        _ing(["corn flakes", "cereales copos", "cereal"],
             "carbohidrato",  50.0, exclude=["pan", "molde"]),
        _ing(["frutos rojos", "mix frutos"], "fruta",  100.0),
    ]),
    Recipe("Batido de avena con tropical", "desayuno", [
        _ing(["copos de avena", "avena"], "carbohidrato", 80.0),
        _ing("leche",                  "lacteo",         200.0),
        _ing(["frutas tropical", "mix tropical", "tropical"], "fruta", 100.0),
    ]),
    Recipe("Tostadas con jamón serrano", "desayuno", [
        _ing("pan",                             "carbohidrato", 100.0, exclude=["rallado"]),
        _ing(["jamón serrano", "jamón"],        "proteina",      50.0,
             exclude=["cocido", "pavo", "york"]),
        _ing("aceite de oliva",                 "grasa",          5.0),
    ]),
    Recipe("Tostadas con lomo", "desayuno", [
        _ing("pan",                             "carbohidrato", 100.0, exclude=["rallado"]),
        _ing(["lomo de cerdo", "lomo"],         "proteina",      60.0,
             exclude=["paté", "salchicha", "frankfurt"]),
    ]),
    Recipe("Tostadas con aceite y tomate", "desayuno", [
        _ing(["barra de pan tradicional", "barra de pan", "pan de molde", "pan"],
             "carbohidrato", 100.0, exclude=["rallado"]),
        _ing(["tomate triturado", "tomate frito"],
             "verdura",       80.0),
        _ing("aceite de oliva",         "grasa",         15.0),
    ]),
    Recipe("Tostadas con pavo", "desayuno", [
        _ing(["pan de molde", "pan"],
             "carbohidrato", 100.0, exclude=["rallado"]),
        _ing(["pechuga de pavo lonchas", "pavo lonchas", "pavo"],
             "proteina",      60.0, exclude=["salchicha", "frankfurt", "fiambre"]),
    ]),
    Recipe("Tostadas con mortadela", "desayuno", [
        _ing(["pan de molde", "pan"],
             "carbohidrato", 100.0, exclude=["rallado"]),
        _ing(["mortadela"],
             "proteina",      60.0),
    ]),
    Recipe("Pan con aceite", "desayuno", [
        _ing(["barra de pan", "pan"],
             "carbohidrato", 120.0, exclude=["rallado", "molde"]),
        _ing("aceite de oliva",         "grasa",         15.0),
    ]),
    Recipe("Bocadillo de jamón cocido", "desayuno", [
        _ing(["barra de pan", "pan"],
             "carbohidrato", 120.0, exclude=["rallado", "molde"]),
        _ing(["jamón cocido", "jamón cocido", "jamón"],
             "proteina",      80.0, exclude=["serrano", "ibérico", "pavo"]),
    ]),
    Recipe("Bocadillo de lomo", "desayuno", [
        _ing(["barra de pan", "pan"],
             "carbohidrato", 120.0, exclude=["rallado", "molde"]),
        _ing(["lomo de cerdo", "lomo"],
             "proteina",      80.0, exclude=["paté", "salchicha", "frankfurt"]),
    ]),
    Recipe("Yogur natural con miel", "desayuno", [
        _ing(["yogur natural"],
             "lacteo",       250.0, exclude=["griego", "sabores", "bebida", "mango"]),
    ]),
    Recipe("Yogur griego natural", "desayuno", [
        _ing(["yogur griego natural", "yogur griego"],
             "lacteo",       250.0, exclude=["mango", "fresa", "sabor", "coco"]),
    ]),
    Recipe("Porridge de avena con leche", "desayuno", [
        _ing(["copos de avena", "avena"],
             "carbohidrato",  80.0),
        _ing(["leche semidesnatada", "leche"],
             "lacteo",       250.0, exclude=["soja", "avena", "arroz", "bebida", "almendra"]),
    ]),
    Recipe("Muesli con leche", "desayuno", [
        _ing(["muesli", "muesli"],
             "carbohidrato",  70.0),
        _ing(["leche semidesnatada", "leche"],
             "lacteo",       200.0, exclude=["soja", "avena", "arroz", "bebida", "almendra"]),
    ]),
    Recipe("Yogur con nueces", "desayuno", [
        _ing(["yogur griego natural", "yogur"],
             "lacteo",       200.0, exclude=["bebida", "sabores", "mango"]),
        _ing(["nueces naturales", "nuez"],
             "grasa",         30.0),
    ]),
    Recipe("Yogur con almendras", "desayuno", [
        _ing(["yogur griego natural", "yogur"],
             "lacteo",       200.0, exclude=["bebida", "sabores", "mango"]),
        _ing(["almendra", "almendra"],
             "grasa",         30.0),
    ]),
    Recipe("Tostadas con queso y tomate", "desayuno", [
        _ing(["pan de molde", "pan"],
             "carbohidrato", 100.0, exclude=["rallado"]),
        _ing(["queso en lonchas", "queso lonchas", "queso fundido"],
             "lacteo",        40.0, exclude=["rallado"]),
        _ing(["tomate triturado", "tomate"],
             "verdura",       60.0),
    ]),
    Recipe("Batido de leche con avena y fruta", "desayuno", [
        _ing(["leche semidesnatada", "leche"],
             "lacteo",       250.0, exclude=["soja", "avena", "arroz", "bebida", "almendra"]),
        _ing(["copos de avena", "avena"],
             "carbohidrato",  60.0),
        _ing(["mix frutos rojos", "fruta"],
             "fruta",        100.0),
    ]),
    Recipe("Leche con galletas tostadas", "desayuno", [
        _ing(["leche semidesnatada", "leche"],
             "lacteo",       250.0, exclude=["soja", "avena", "arroz", "bebida", "almendra"]),
        _ing(["galletas tostadas", "galletas maría", "galleta"],
             "carbohidrato",  50.0, exclude=["chocolate", "cacao"]),
    ]),

    # ── COMIDAS ────────────────────────────────────────────────────────────

    Recipe("Pollo con arroz y verduras", "comida", [
        # pechuga preferida; fallback a cuartos traseros de pollo
        _ing(["pechuga", "pollo"],     "proteina",     180.0),
        _ing("arroz",                  "carbohidrato", 130.0),
        _ing("espinaca",               "verdura",      80.0),
        _ing("tomate",                 "verdura",      80.0),
        _ing("aceite",                 "grasa",        10.0),
    ]),
    Recipe("Pollo con pasta y verduras", "comida", [
        _ing(["pechuga", "pollo"],     "proteina",     160.0),
        _ing("pasta",                  "carbohidrato", 130.0, exclude=["huevo"]),
        _ing("espinaca",               "verdura",      100.0),
        _ing("aceite",                 "grasa",        10.0),
    ]),
    Recipe("Arroz con atún y verduras", "comida", [
        # atún real (lata); excluir empanadillas, lasaña, empanada
        _ing("atún",                   "proteina",     100.0,
             exclude=["empanadilla", "lasaña", "empanada"]),
        _ing("arroz",                  "carbohidrato", 140.0),
        _ing("tomate",                 "verdura",      100.0),
        _ing("espinaca",               "verdura",      80.0),
        _ing("aceite",                 "grasa",        10.0),
    ]),
    Recipe("Pasta con atún y tomate", "comida", [
        _ing("atún",                   "proteina",     100.0,
             exclude=["empanadilla", "lasaña", "empanada"]),
        _ing("pasta",                  "carbohidrato", 140.0, exclude=["huevo"]),
        _ing("tomate",                 "verdura",      120.0),
        _ing("aceite",                 "grasa",        10.0),
    ]),
    Recipe("Lentejas completas", "comida", [
        _ing("lenteja",                "legumbre",     120.0),
        _ing("tomate",                 "verdura",      100.0),
        _ing("espinaca",               "verdura",      100.0),
        _ing("aceite",                 "grasa",        10.0),
    ]),
    Recipe("Garbanzos con verduras", "comida", [
        _ing("garbanzo",               "legumbre",     120.0),
        _ing("espinaca",               "verdura",      100.0),
        _ing("tomate",                 "verdura",      100.0),
        _ing("aceite",                 "grasa",        10.0),
    ]),
    Recipe("Lentejas con arroz", "comida", [
        _ing("lenteja",                "legumbre",     100.0),
        _ing("arroz",                  "carbohidrato", 100.0),
        _ing("tomate",                 "verdura",      100.0),
        _ing("aceite",                 "grasa",        10.0),
    ]),
    Recipe("Pollo con pan y ensalada", "comida", [
        _ing(["pechuga", "pollo"],     "proteina",     160.0),
        _ing("pan",                    "carbohidrato", 90.0, exclude=["rallado"]),
        _ing("tomate",                 "verdura",      120.0),
        _ing("espinaca",               "verdura",      80.0),
        _ing("aceite",                 "grasa",        10.0),
    ]),
    Recipe("Atún con pan y ensalada", "comida", [
        _ing("atún",                   "proteina",     120.0,
             exclude=["empanadilla", "lasaña", "empanada"]),
        _ing("pan",                    "carbohidrato", 100.0, exclude=["rallado"]),
        _ing("tomate",                 "verdura",      120.0),
        _ing("aceite",                 "grasa",        10.0),
    ]),
    Recipe("Arroz con pavo y verduras", "comida", [
        _ing(["pavo lonchas", "pavo"],
             "proteina",     120.0, exclude=["fiambre", "salchicha"]),
        _ing("arroz",                  "carbohidrato", 130.0),
        _ing("espinaca",               "verdura",      100.0),
        _ing("aceite",                 "grasa",        10.0),
    ]),
    Recipe("Pasta con pavo y verduras", "comida", [
        _ing(["pavo lonchas", "pavo"],
             "proteina",     120.0, exclude=["fiambre", "salchicha"]),
        _ing("pasta",                  "carbohidrato", 130.0, exclude=["huevo"]),
        _ing("tomate",                 "verdura",      100.0),
        _ing("aceite",                 "grasa",        10.0),
    ]),
    Recipe("Arroz con lentejas", "comida", [
        _ing("lenteja",                "legumbre",     120.0),
        _ing("arroz",                  "carbohidrato", 120.0),
        _ing("tomate",                 "verdura",      100.0),
        _ing("aceite",                 "grasa",        10.0),
    ]),
    Recipe("Pasta con lentejas", "comida", [
        _ing("lenteja",                "legumbre",     100.0),
        _ing("pasta",                  "carbohidrato", 130.0, exclude=["huevo"]),
        _ing("tomate",                 "verdura",      100.0),
        _ing("aceite",                 "grasa",        10.0),
    ]),

    # ── COMIDAS alta proteína ──────────────────────────────────────────────

    Recipe("Pechuga doble con arroz", "comida", [
        _ing(["pechuga", "pollo"],     "proteina",     280.0),
        _ing("arroz",                  "carbohidrato", 100.0),
        _ing("tomate",                 "verdura",       80.0),
        _ing("aceite",                 "grasa",         10.0),
    ]),
    Recipe("Pechuga doble con pasta", "comida", [
        _ing(["pechuga", "pollo"],     "proteina",     280.0),
        _ing("pasta",                  "carbohidrato", 100.0, exclude=["huevo"]),
        _ing("espinaca",               "verdura",       80.0),
        _ing("aceite",                 "grasa",         10.0),
    ]),
    Recipe("Atún doble con arroz", "comida", [
        _ing("atún",                   "proteina",     200.0,
             exclude=["empanadilla", "lasaña", "empanada"]),
        _ing("arroz",                  "carbohidrato", 120.0),
        _ing("tomate",                 "verdura",      100.0),
        _ing("aceite",                 "grasa",         10.0),
    ]),
    Recipe("Atún doble con pasta", "comida", [
        _ing("atún",                   "proteina",     200.0,
             exclude=["empanadilla", "lasaña", "empanada"]),
        _ing("pasta",                  "carbohidrato", 120.0, exclude=["huevo"]),
        _ing("espinaca",               "verdura",       80.0),
        _ing("aceite",                 "grasa",         10.0),
    ]),

    # ── COMIDAS proteínas variadas ────────────────────────────────────────

    Recipe("Arroz con carne picada", "comida", [
        _ing(["carne picada cerdo", "carne picada vacuno", "carne picada pollo"],
             "proteina",     160.0),
        _ing(["arroz redondo", "arroz"],        "carbohidrato", 130.0),
        _ing(["tomate triturado", "tomate"],    "verdura",      100.0),
        _ing("aceite de oliva",                 "grasa",         10.0),
    ]),
    Recipe("Pasta con carne picada", "comida", [
        _ing(["carne picada cerdo", "carne picada vacuno", "carne picada pollo"],
             "proteina",     160.0),
        _ing(["pasta maravilla", "pasta"],      "carbohidrato", 130.0, exclude=["huevo"]),
        _ing(["tomate triturado", "tomate"],    "verdura",      100.0),
        _ing("aceite de oliva",                 "grasa",         10.0),
    ]),
    Recipe("Panga con arroz y verduras", "comida", [
        _ing(["filetes de panga", "panga"],     "proteina",     200.0),
        _ing(["arroz redondo", "arroz"],        "carbohidrato", 130.0),
        _ing("espinaca",                        "verdura",      100.0),
        _ing("aceite de oliva",                 "grasa",         10.0),
    ]),
    Recipe("Panga con pasta", "comida", [
        _ing(["filetes de panga", "panga"],     "proteina",     180.0),
        _ing(["pasta maravilla", "pasta"],      "carbohidrato", 130.0, exclude=["huevo"]),
        _ing(["tomate triturado", "tomate"],    "verdura",      100.0),
        _ing("aceite de oliva",                 "grasa",         10.0),
    ]),
    Recipe("Gambas con arroz", "comida", [
        _ing(["gamba pelada", "gamba"],         "proteina",     200.0),
        _ing(["arroz redondo", "arroz"],        "carbohidrato", 130.0),
        _ing(["tomate triturado", "tomate"],    "verdura",      100.0),
        _ing("aceite de oliva",                 "grasa",         10.0),
    ]),
    Recipe("Mejillones con pasta", "comida", [
        _ing(["mejillón", "mejillon"],          "proteina",     200.0,
             exclude=["empanadilla", "lasaña"]),
        _ing(["pasta maravilla", "pasta"],      "carbohidrato", 130.0, exclude=["huevo"]),
        _ing(["tomate triturado", "tomate"],    "verdura",      100.0),
        _ing("aceite de oliva",                 "grasa",         10.0),
    ]),
    Recipe("Solomillo de pavo con arroz", "comida", [
        _ing(["solomillo de pavo", "pechuga de pavo", "pavo"],
             "proteina",     180.0, exclude=["paté", "jamón", "pollo"]),
        _ing(["arroz redondo", "arroz"],        "carbohidrato", 130.0),
        _ing("espinaca",                        "verdura",      100.0),
        _ing("aceite de oliva",                 "grasa",         10.0),
    ]),
    Recipe("Lomo con patatas", "comida", [
        _ing(["lomo de cerdo", "lomo"],         "proteina",     150.0,
             exclude=["paté", "salchicha", "frankfurt"]),
        _ing("patata",                          "verdura",      200.0,
             exclude=["prefrita", "fritas", "gajo", "air", "rellena"]),
        _ing(["tomate triturado", "tomate"],    "verdura",       80.0),
        _ing("aceite de oliva",                 "grasa",         10.0),
    ]),

    # ── COMIDAS nuevas ────────────────────────────────────────────────────

    Recipe("Merluza con arroz y verduras", "comida", [
        _ing(["palitos de merluza", "merluza"], "proteina",     200.0),
        _ing(["arroz redondo", "arroz"],        "carbohidrato", 130.0),
        _ing(["espinaca", "brócoli", "coliflor"], "verdura",    100.0),
        _ing("aceite de oliva",                 "grasa",         10.0),
    ]),
    Recipe("Merluza con pasta", "comida", [
        _ing(["palitos de merluza", "merluza"], "proteina",     180.0),
        _ing(["pasta maravilla", "pasta"],      "carbohidrato", 130.0, exclude=["huevo"]),
        _ing(["tomate triturado", "tomate"],    "verdura",      100.0),
        _ing("aceite de oliva",                 "grasa",         10.0),
    ]),
    Recipe("Pollo con brócoli y arroz", "comida", [
        _ing(["pechuga", "pollo"],              "proteina",     160.0,
             exclude=["salchicha", "frankfurt"]),
        _ing(["arroz redondo", "arroz"],        "carbohidrato", 120.0),
        _ing(["brócoli", "coliflor"],           "verdura",      150.0),
        _ing("aceite de oliva",                 "grasa",         10.0),
    ]),
    Recipe("Pollo con pimientos y arroz", "comida", [
        _ing(["pechuga", "pollo"],              "proteina",     160.0,
             exclude=["salchicha", "frankfurt"]),
        _ing(["arroz redondo", "arroz"],        "carbohidrato", 120.0),
        _ing(["pimiento", "judía verde"],       "verdura",      120.0),
        _ing("aceite de oliva",                 "grasa",         10.0),
    ]),
    Recipe("Sardinas con pasta", "comida", [
        _ing(["sardina", "caballa"],            "proteina",     100.0,
             exclude=["filete de caballa"]),
        _ing(["pasta maravilla", "pasta"],      "carbohidrato", 150.0, exclude=["huevo"]),
        _ing(["tomate triturado", "tomate"],    "verdura",      100.0),
        _ing("aceite de oliva",                 "grasa",         10.0),
    ]),
    Recipe("Quinoa con pollo y verduras", "comida", [
        _ing(["pechuga", "pollo"],              "proteina",     160.0,
             exclude=["salchicha", "frankfurt"]),
        _ing(["quinoa", "arroz"],               "carbohidrato", 100.0),
        _ing(["espinaca", "brócoli"],           "verdura",      100.0),
        _ing("aceite de oliva",                 "grasa",         10.0),
    ]),

    # ── CENAS ──────────────────────────────────────────────────────────────

    Recipe("Lomo con espinacas", "cena", [
        _ing(["lomo de cerdo cocido", "lomo"],
             "proteina",     150.0, exclude=["adobado", "marinado"]),
        _ing(["espinaca"],
             "verdura",      150.0),
        _ing("aceite de oliva",        "grasa",        10.0),
    ]),
    Recipe("Pavo con pan y espinacas", "cena", [
        _ing(["pavo lonchas", "pavo"],
             "proteina",     120.0, exclude=["fiambre", "salchicha"]),
        _ing("pan",                    "carbohidrato", 80.0, exclude=["rallado"]),
        _ing(["espinaca"],
             "verdura",      100.0),
        _ing("aceite de oliva",        "grasa",        10.0),
    ]),
    Recipe("Ensalada con atún", "cena", [
        _ing("atún",                   "proteina",     100.0,
             exclude=["empanadilla", "lasaña", "empanada"]),
        _ing("tomate",                 "verdura",      120.0),
        _ing("espinaca",               "verdura",      100.0),
        _ing("aceite",                 "grasa",        10.0),
    ]),
    Recipe("Pollo con verduras", "cena", [
        _ing(["pechuga", "pollo"],     "proteina",     160.0),
        _ing("espinaca",               "verdura",      120.0),
        _ing("tomate",                 "verdura",      100.0),
        _ing("aceite",                 "grasa",        10.0),
    ]),
    Recipe("Lentejas ligeras", "cena", [
        _ing("lenteja",                "legumbre",     100.0),
        _ing("tomate",                 "verdura",      100.0),
        _ing("aceite",                 "grasa",        10.0),
    ]),
    Recipe("Yogur con frutos secos", "cena", [
        _ing("yogur",                  "lacteo",       200.0),
        _ing("cacahuete",              "grasa",        30.0),
    ]),
    Recipe("Sandwich de cena", "cena", [
        _ing("pan",                    "carbohidrato", 100.0, exclude=["rallado"]),
        _ing(["jamón cocido", "jamón"],"proteina",     80.0),
    ]),
    Recipe("Atún con verduras", "cena", [
        _ing("atún",                   "proteina",     120.0,
             exclude=["empanadilla", "lasaña", "empanada"]),
        _ing("espinaca",               "verdura",      120.0),
        _ing("tomate",                 "verdura",      100.0),
        _ing("aceite",                 "grasa",        10.0),
    ]),

    # ── CENAS alta proteína ────────────────────────────────────────────────

    Recipe("Pechuga con espinacas", "cena", [
        _ing(["pechuga", "pollo"],     "proteina",     200.0),
        _ing("espinaca",               "verdura",      150.0),
        _ing("tomate",                 "verdura",       80.0),
        _ing("aceite",                 "grasa",         10.0),
    ]),
    Recipe("Pechuga con verduras doble", "cena", [
        _ing(["pechuga", "pollo"],     "proteina",     250.0),
        _ing("espinaca",               "verdura",      120.0),
        _ing("aceite",                 "grasa",         10.0),
    ]),
    Recipe("Atún doble con verduras", "cena", [
        _ing("atún",                   "proteina",     200.0,
             exclude=["empanadilla", "lasaña", "empanada"]),
        _ing("espinaca",               "verdura",      120.0),
        _ing("tomate",                 "verdura",      100.0),
        _ing("aceite",                 "grasa",         10.0),
    ]),
    Recipe("Claras con verduras", "cena", [
        _ing("clara",                  "proteina",     250.0),
        _ing("espinaca",               "verdura",      150.0),
        _ing("aceite",                 "grasa",         10.0),
    ]),

    # ── CENAS proteínas variadas ──────────────────────────────────────────

    Recipe("Panga con verduras", "cena", [
        _ing(["filetes de panga", "panga"],     "proteina",  200.0),
        _ing("espinaca",                        "verdura",   150.0),
        _ing("aceite de oliva",                 "grasa",      10.0),
    ]),
    Recipe("Gambas con verduras", "cena", [
        _ing(["gamba pelada", "gamba"],         "proteina",  180.0),
        _ing(["pimiento", "judía verde"],       "verdura",   150.0),
        _ing("aceite de oliva",                 "grasa",      10.0),
    ]),
    Recipe("Mejillones con tomate", "cena", [
        _ing(["mejillón", "mejillon"],          "proteina",  200.0,
             exclude=["empanadilla", "lasaña"]),
        _ing(["tomate triturado", "tomate"],    "verdura",   150.0),
        _ing("aceite de oliva",                 "grasa",      10.0),
    ]),
    Recipe("Calamar con verduras", "cena", [
        _ing(["calamar troceado", "calamar"],   "proteina",  180.0,
             exclude=["salsa", "tinta"]),
        _ing(["pimiento", "judía verde"],       "verdura",   120.0),
        _ing(["tomate triturado", "tomate"],    "verdura",    80.0),
        _ing("aceite de oliva",                 "grasa",      10.0),
    ]),
    Recipe("Carne picada con tomate", "cena", [
        _ing(["carne picada cerdo", "carne picada vacuno", "carne picada pollo"],
             "proteina",  160.0),
        _ing(["tomate triturado", "tomate"],    "verdura",   150.0),
        _ing("aceite de oliva",                 "grasa",      10.0),
    ]),
    Recipe("Solomillo de pavo con espinacas", "cena", [
        _ing(["solomillo de pavo", "pechuga de pavo", "pavo"],
             "proteina",  180.0, exclude=["paté", "jamón", "pollo"]),
        _ing("espinaca",                        "verdura",   150.0),
        _ing("aceite de oliva",                 "grasa",      10.0),
    ]),
    Recipe("Lomo con verduras", "cena", [
        _ing(["lomo de cerdo", "lomo"],         "proteina",  150.0,
             exclude=["paté", "salchicha", "frankfurt"]),
        _ing("espinaca",                        "verdura",   120.0),
        _ing(["tomate triturado", "tomate"],    "verdura",    80.0),
        _ing("aceite de oliva",                 "grasa",      10.0),
    ]),
    Recipe("Jamón serrano con pan", "cena", [
        _ing(["jamón serrano", "jamón"],        "proteina",   80.0,
             exclude=["cocido", "pavo", "york"]),
        _ing("pan",                             "carbohidrato", 100.0, exclude=["rallado"]),
        _ing(["tomate triturado", "tomate"],    "verdura",    80.0),
    ]),

    # ── CENAS nuevas ──────────────────────────────────────────────────────

    Recipe("Merluza con verduras", "cena", [
        _ing(["palitos de merluza", "merluza"], "proteina",  200.0),
        _ing(["espinaca", "brócoli", "coliflor"], "verdura", 150.0),
        _ing("aceite de oliva",                 "grasa",      10.0),
    ]),
    Recipe("Sardinas con tomate", "cena", [
        _ing(["sardina", "caballa"],            "proteina",  120.0,
             exclude=["filete de caballa"]),
        _ing(["tomate triturado", "tomate"],    "verdura",   150.0),
        _ing("aceite de oliva",                 "grasa",      10.0),
    ]),
    Recipe("Pollo con pimientos", "cena", [
        _ing(["pechuga", "pollo"],              "proteina",  160.0,
             exclude=["salchicha", "frankfurt"]),
        _ing(["pimiento", "judía verde"],       "verdura",   150.0),
        _ing("aceite de oliva",                 "grasa",      10.0),
    ]),
    Recipe("Merluza con brócoli", "cena", [
        _ing(["palitos de merluza", "merluza"], "proteina",  180.0),
        _ing(["brócoli", "coliflor"],           "verdura",   150.0),
        _ing("aceite de oliva",                 "grasa",      10.0),
    ]),
    Recipe("Albóndigas con tomate", "cena", [
        _ing(["albóndiga", "albondiga"],        "proteina",  200.0),
        _ing(["tomate triturado", "tomate"],    "verdura",   150.0),
        _ing("aceite de oliva",                 "grasa",      10.0),
    ]),
    Recipe("Revuelto de espinacas", "cena", [
        _ing("clara",                           "proteina",  200.0),
        _ing("espinaca",                        "verdura",   150.0),
        _ing("aceite de oliva",                 "grasa",      10.0),
    ]),
    Recipe("Merluza con patatas", "cena", [
        _ing(["palitos de merluza", "merluza"], "proteina",  180.0),
        _ing("patata",                          "verdura",   150.0,
             exclude=["prefrita", "fritas", "gajo", "air", "rellena"]),
        _ing("aceite de oliva",                 "grasa",      10.0),
    ]),
    Recipe("Pollo con cebolla y pimientos", "cena", [
        _ing(["pechuga", "pollo"],              "proteina",  160.0,
             exclude=["salchicha", "frankfurt"]),
        _ing(["pimiento", "judía verde"],       "verdura",   100.0),
        _ing(["cebolla", "puerro"],             "verdura",    80.0),
        _ing("aceite de oliva",                 "grasa",      10.0),
    ]),
    Recipe("Sardinas con ensalada", "cena", [
        _ing(["sardina", "caballa"],            "proteina",  100.0,
             exclude=["filete de caballa"]),
        _ing("espinaca",                        "verdura",   120.0),
        _ing(["tomate triturado", "tomate"],    "verdura",    80.0),
        _ing("aceite de oliva",                 "grasa",      10.0),
    ]),
    Recipe("Garbanzos con espinacas", "cena", [
        _ing("garbanzo",                        "legumbre",  150.0),
        _ing("espinaca",                        "verdura",   150.0),
        _ing("aceite de oliva",                 "grasa",      10.0),
    ]),
    Recipe("Pavo con verduras", "cena", [
        _ing(["pechuga de pavo", "pavo", "pechuga"], "proteina", 160.0,
             exclude=["paté", "jamón", "pollo"]),
        _ing("espinaca",                        "verdura",   120.0),
        _ing(["tomate triturado", "tomate"],    "verdura",    80.0),
        _ing("aceite de oliva",                 "grasa",      10.0),
    ]),
    Recipe("Atún con pimientos", "cena", [
        _ing("atún",                            "proteina",  120.0,
             exclude=["empanadilla", "lasaña", "empanada"]),
        _ing(["pimiento", "judía verde"],       "verdura",   150.0),
        _ing("aceite de oliva",                 "grasa",      10.0),
    ]),
    Recipe("Yogur con fruta", "cena", [
        _ing("yogur",                           "lacteo",    250.0, exclude=["griego", "mango"]),
        _ing(["frutos rojos", "frutas tropical", "tropical", "mix frutos"],
             "fruta",         150.0),
    ]),
    Recipe("Merluza con brócoli y patatas", "cena", [
        _ing(["palitos de merluza", "merluza"], "proteina",  160.0),
        _ing("brócoli",                         "verdura",   100.0),
        _ing("patata",                          "verdura",   100.0,
             exclude=["prefrita", "fritas", "gajo", "air", "rellena"]),
        _ing("aceite de oliva",                 "grasa",      10.0),
    ]),

    # ── COMIDAS nuevas ──────────────────────────────────────────────────────

    # Surimi
    Recipe("Surimi con arroz y verduras", "comida", [
        _ing(["surimi"],  "proteina",  160.0,
             exclude=["aritos", "muslit", "delicias"]),
        _ing(["arroz redondo"], "carbohidrato", 120.0),
        _ing(["judía verde"], "verdura", 100.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Surimi con pasta y tomate", "comida", [
        _ing(["surimi"],  "proteina",  150.0,
             exclude=["aritos", "muslit"]),
        _ing(["macarrón", "pasta"], "carbohidrato", 120.0),
        _ing(["tomate triturado"], "verdura", 100.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Almejas
    Recipe("Almejas con arroz", "comida", [
        _ing(["almeja"],   "proteina",  150.0),
        _ing(["arroz"],       "carbohidrato", 130.0),
        _ing(["tomate frito"], "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Almejas con pasta", "comida", [
        _ing(["almeja"],   "proteina",  150.0),
        _ing(["tallarines"],     "carbohidrato", 120.0),
        _ing(["pimiento"], "verdura", 100.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Bacalao
    Recipe("Bacalao con arroz y espinacas", "comida", [
        _ing(["bacalao"], "proteina", 150.0),
        _ing(["arroz"],       "carbohidrato", 130.0),
        _ing(["espinaca"], "verdura", 100.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Bacalao con cous cous y pimientos", "comida", [
        _ing(["bacalao"], "proteina", 150.0),
        _ing(["cous cous"], "carbohidrato", 120.0),
        _ing(["pimiento"], "verdura", 120.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Sepia
    Recipe("Sepia con arroz negro", "comida", [
        _ing(["sepia"], "proteina", 150.0),
        _ing(["arroz"],       "carbohidrato", 130.0),
        _ing(["tomate"],   "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Sepia con fideos", "comida", [
        _ing(["sepia"], "proteina", 150.0),
        _ing(["fideo"],        "carbohidrato", 120.0),
        _ing(["cebolla"], "verdura", 100.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Pota
    Recipe("Pota con macarrones", "comida", [
        _ing(["pota", "anillas de pota"], "proteina", 150.0),
        _ing(["macarrón"],   "carbohidrato", 130.0),
        _ing(["tomate frito"], "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Pota con arroz y verduras", "comida", [
        _ing(["pota"], "proteina", 150.0),
        _ing(["arroz basmati", "arroz"], "carbohidrato", 120.0),
        _ing(["guisante"], "verdura", 120.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Brochetas de pollo
    Recipe("Brochetas de pollo con arroz", "comida", [
        _ing(["brochetas de pollo"],
             "proteina",  160.0),
        _ing(["arroz vaporizado", "arroz"], "carbohidrato", 130.0),
        _ing(["tomate"],   "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Brochetas de pollo con cous cous", "comida", [
        _ing(["brochetas de pollo"],
             "proteina",  160.0),
        _ing(["cous cous"], "carbohidrato", 120.0),
        _ing(["cebolla"], "verdura", 100.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Burger de cerdo
    Recipe("Burger de cerdo con pasta", "comida", [
        _ing(["Burger de cerdo", "burger cerdo"],        "proteina",  160.0),
        _ing(["pasta penne", "pasta"], "carbohidrato", 120.0),
        _ing(["tomate frito"], "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Burger de cerdo con arroz", "comida", [
        _ing(["Burger de cerdo", "burger cerdo"],        "proteina",  160.0),
        _ing(["arroz integral", "arroz"], "carbohidrato", 130.0),
        _ing(["brócoli"],  "verdura", 120.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Burger de vacuno
    Recipe("Burger de vacuno con macarrones", "comida", [
        _ing(["Burger de vacuno y cerdo", "burger de vacuno", "burger vacuno"], "proteina", 160.0),
        _ing(["macarrón"],   "carbohidrato", 120.0),
        _ing(["tomate"],   "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Burger de vacuno con arroz y guisantes", "comida", [
        _ing(["Burger de vacuno y cerdo", "burger vacuno"], "proteina", 160.0),
        _ing(["arroz"],       "carbohidrato", 130.0),
        _ing(["guisante"], "verdura", 120.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Alas de pollo
    Recipe("Alas de pollo con arroz", "comida", [
        _ing(["alas de pollo"], "proteina", 180.0,
             exclude=["barbacoa"]),
        _ing(["arroz"],       "carbohidrato", 130.0),
        _ing(["judía verde"], "verdura", 100.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Alas de pollo con spaghetti", "comida", [
        _ing(["alas de pollo"], "proteina", 180.0),
        _ing(["spaghetti integral", "spaghetti"], "carbohidrato", 120.0),
        _ing(["tomate frito"], "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Chopped
    Recipe("Chopped con pasta y verduras", "comida", [
        _ing(["chopped"],           "proteina",  150.0,
             exclude=["cerdo", "cocido"]),
        _ing(["hélices", "pasta"],  "carbohidrato", 120.0),
        _ing(["espinaca"], "verdura", 100.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Chopped cerdo
    Recipe("Chopped cerdo con arroz y maíz", "comida", [
        _ing(["chopped cerdo"], "proteina", 150.0),
        _ing(["arroz"],       "carbohidrato", 130.0),
        _ing(["maíz dulce"], "verdura", 100.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Mortadela
    Recipe("Mortadela con macarrones y verduras", "comida", [
        _ing(["mortadela"], "proteina", 150.0,
             exclude=["pavo", "aceitunas"]),
        _ing(["macarrón"],   "carbohidrato", 130.0),
        _ing(["brócoli"], "verdura", 120.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Lacón
    Recipe("Lacón con arroz y espinacas", "comida", [
        _ing(["lacón"],   "proteina",  150.0),
        _ing(["arroz"],    "carbohidrato", 130.0),
        _ing(["espinaca"], "verdura", 100.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Magro de cerdo
    Recipe("Magro de cerdo con arroz basmati", "comida", [
        _ing(["magro de cerdo", "magro"], "proteina", 160.0),
        _ing(["arroz basmati", "arroz"], "carbohidrato", 130.0),
        _ing(["pimiento"], "verdura", 100.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Magro de cerdo con fideos", "comida", [
        _ing(["magro de cerdo", "magro"], "proteina", 160.0),
        _ing(["fideo"],       "carbohidrato", 120.0),
        _ing(["tomate"],   "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Gambón
    Recipe("Gambón con arroz basmati", "comida", [
        _ing(["gambón", "colas de gambón"], "proteina", 160.0),
        _ing(["arroz basmati", "arroz"], "carbohidrato", 130.0),
        _ing(["guisante"], "verdura", 100.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Gambón con pasta y verduras", "comida", [
        _ing(["gambón"],      "proteina",  160.0),
        _ing(["pasta penne", "pasta"], "carbohidrato", 120.0),
        _ing(["espinaca"], "verdura", 100.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Caballa
    Recipe("Caballa con arroz integral", "comida", [
        _ing(["caballa"], "proteina", 130.0),
        _ing(["arroz integral", "arroz"], "carbohidrato", 130.0),
        _ing(["tomate"],   "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Caballa con pasta y tomate", "comida", [
        _ing(["caballa"], "proteina", 130.0),
        _ing(["hélices", "pasta"],  "carbohidrato", 120.0),
        _ing(["tomate frito"], "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Bonito
    Recipe("Bonito con arroz y pimientos", "comida", [
        _ing(["bonito", "migas de bonito"], "proteina", 130.0),
        _ing(["arroz"],       "carbohidrato", 130.0),
        _ing(["pimiento"], "verdura", 120.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Carrilladas
    Recipe("Carrilladas con macarrones", "comida", [
        _ing(["carrilladas"], "proteina", 150.0),
        _ing(["macarrón"],   "carbohidrato", 120.0),
        _ing(["tomate"],   "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Carrilladas con arroz y verduras", "comida", [
        _ing(["carrilladas"], "proteina", 150.0),
        _ing(["arroz"],       "carbohidrato", 130.0),
        _ing(["judía verde"], "verdura", 100.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Cous cous + diversos
    Recipe("Pollo con cous cous y brócoli", "comida", [
        _ing(["pechuga"],   "proteina",  160.0,
             exclude=["pavo", "braseada", "finas", "empanada"]),
        _ing(["cous cous"], "carbohidrato", 120.0),
        _ing(["brócoli"], "verdura", 120.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Pechuga con tallarines y espinacas", "comida", [
        _ing(["pechuga"],   "proteina",  160.0,
             exclude=["pavo", "braseada", "finas"]),
        _ing(["tallarines"],     "carbohidrato", 120.0),
        _ing(["espinaca"], "verdura", 100.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Pechuga con spaghetti y tomate", "comida", [
        _ing(["pechuga"],   "proteina",  160.0,
             exclude=["pavo", "braseada", "finas"]),
        _ing(["spaghetti integral", "spaghetti"], "carbohidrato", 120.0),
        _ing(["tomate frito"], "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Pechuga con arroz para microondas", "comida", [
        _ing(["pechuga"],   "proteina",  160.0,
             exclude=["pavo", "braseada", "finas"]),
        _ing(["arroz para microondas", "arroz"], "carbohidrato", 150.0),
        _ing(["tomate"],   "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Pechuga con arroz vaporizado y guisantes", "comida", [
        _ing(["pechuga"],   "proteina",  160.0,
             exclude=["pavo", "braseada", "finas"]),
        _ing(["arroz vaporizado", "arroz"], "carbohidrato", 130.0),
        _ing(["guisante"], "verdura", 120.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Pechuga con arroz basmati y cebolla", "comida", [
        _ing(["pechuga"],   "proteina",  160.0,
             exclude=["pavo", "braseada", "finas"]),
        _ing(["arroz basmati", "arroz"], "carbohidrato", 130.0),
        _ing(["cebolla"], "verdura", 100.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Alubias comidas
    Recipe("Alubia blanca con arroz y verduras", "comida", [
        _ing(["alubia blanca"], "legumbre", 130.0),
        _ing(["arroz"],       "carbohidrato", 100.0),
        _ing(["tomate"],   "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Alubia negra con pasta y pimiento", "comida", [
        _ing(["alubia negra"], "legumbre",  130.0),
        _ing(["macarrón"],   "carbohidrato", 110.0),
        _ing(["pimiento"], "verdura", 100.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Alubia pinta con arroz integral", "comida", [
        _ing(["alubia pinta"], "legumbre",  130.0),
        _ing(["arroz integral", "arroz"], "carbohidrato", 120.0),
        _ing(["tomate frito"], "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Alubia roja con fideos", "comida", [
        _ing(["alubia roja"],   "legumbre",  130.0),
        _ing(["fideo"],        "carbohidrato", 110.0),
        _ing(["cebolla"], "verdura", 100.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Mejillones comidas
    Recipe("Mejillones con arroz y tomate", "comida", [
        _ing(["mejillones en escabeche",
              "mejillones"], "proteina", 150.0),
        _ing(["arroz"],       "carbohidrato", 130.0),
        _ing(["tomate"],   "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Mejillones con pasta y espinacas", "comida", [
        _ing(["mejillones"], "proteina", 150.0),
        _ing(["pasta penne", "pasta"], "carbohidrato", 120.0),
        _ing(["espinaca"], "verdura", 100.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Calamar comidas
    Recipe("Calamar con arroz negro", "comida", [
        _ing(["calamar"], "proteina", 150.0,
             exclude=["tinta", "americana"]),
        _ing(["arroz"],       "carbohidrato", 130.0),
        _ing(["tomate frito"], "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Calamar con fideos y cebolla", "comida", [
        _ing(["calamar"], "proteina", 150.0,
             exclude=["tinta", "americana"]),
        _ing(["fideo"],       "carbohidrato", 120.0),
        _ing(["cebolla"], "verdura", 100.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Solomillo pavo comidas
    Recipe("Solomillo de pavo con tallarines", "comida", [
        _ing(["Solomillo de pavo", "solomillo pavo"],    "proteina",  160.0),
        _ing(["tallarines"],     "carbohidrato", 120.0),
        _ing(["espinaca"], "verdura", 100.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Solomillo de pavo con cous cous y brócoli", "comida", [
        _ing(["Solomillo de pavo", "solomillo pavo"],    "proteina",  160.0),
        _ing(["cous cous"], "carbohidrato", 120.0),
        _ing(["brócoli"], "verdura", 120.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Lomo comidas
    Recipe("Lomo con pasta y tomate", "comida", [
        _ing(["lomo"], "proteina", 150.0,
             exclude=["cabecero", "embuchado", "asado", "pavo"]),
        _ing(["pasta"],             "carbohidrato", 120.0),
        _ing(["tomate"],   "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Lomo con arroz integral y judías", "comida", [
        _ing(["lomo"], "proteina", 150.0,
             exclude=["cabecero", "embuchado", "asado", "pavo"]),
        _ing(["arroz integral", "arroz"], "carbohidrato", 130.0),
        _ing(["judía verde"], "verdura", 100.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Tortillas de trigo
    Recipe("Wrap de pollo con verduras", "comida", [
        _ing(["pechuga"],   "proteina",  150.0,
             exclude=["pavo", "braseada", "finas"]),
        _ing(["tortillas de trigo"], "carbohidrato", 80.0),
        _ing(["pimiento"], "verdura", 120.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Wrap de atún con espinacas", "comida", [
        _ing(["atún claro al natural", "atún"],
             "proteina",  120.0, exclude=["empanadilla", "lasaña", "empanada"]),
        _ing(["tortillas de trigo"], "carbohidrato", 80.0),
        _ing(["espinaca"], "verdura", 100.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Spaghetti + proteínas
    Recipe("Spaghetti con atún y tomate", "comida", [
        _ing(["atún"],
             "proteina",  120.0, exclude=["empanadilla", "lasaña", "empanada"]),
        _ing(["spaghetti integral", "spaghetti"], "carbohidrato", 130.0),
        _ing(["tomate frito"], "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Spaghetti con sardinas y tomate", "comida", [
        _ing(["sardinas"], "proteina", 130.0),
        _ing(["spaghetti integral", "spaghetti"], "carbohidrato", 130.0),
        _ing(["tomate frito"], "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Menestra + proteínas
    Recipe("Pollo con menestra y arroz", "comida", [
        _ing(["pechuga"],   "proteina",  160.0,
             exclude=["pavo", "braseada", "finas"]),
        _ing(["arroz"],       "carbohidrato", 120.0),
        _ing(["menestra"], "verdura", 150.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Merluza con menestra y macarrón", "comida", [
        _ing(["filetes de merluza", "merluza"], "proteina", 160.0),
        _ing(["macarrón"],   "carbohidrato", 120.0),
        _ing(["menestra"], "verdura", 150.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Habas
    Recipe("Pollo con habas y arroz", "comida", [
        _ing(["pechuga"],   "proteina",  160.0,
             exclude=["pavo", "braseada", "finas"]),
        _ing(["arroz"],       "carbohidrato", 120.0),
        _ing(["habitas muy tiernas", "habas"],
             "verdura",  130.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Edamame
    Recipe("Pollo con edamame y arroz basmati", "comida", [
        _ing(["pechuga"],   "proteina",  160.0,
             exclude=["pavo", "braseada", "finas"]),
        _ing(["arroz basmati", "arroz"], "carbohidrato", 130.0),
        _ing(["edamame"], "verdura", 120.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Salmón con edamame y arroz", "comida", [
        _ing(["salmón", "medallones de salmón"],
             "proteina",  150.0),
        _ing(["arroz integral", "arroz"], "carbohidrato", 120.0),
        _ing(["edamame"], "verdura", 120.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Coles de bruselas
    Recipe("Pollo con coles de bruselas y pasta", "comida", [
        _ing(["pechuga"],   "proteina",  160.0,
             exclude=["pavo", "braseada", "finas"]),
        _ing(["pasta penne", "pasta"], "carbohidrato", 120.0),
        _ing(["coles de bruselas"], "verdura", 130.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Champiñones
    Recipe("Pollo con champiñones y arroz", "comida", [
        _ing(["pechuga"],   "proteina",  160.0,
             exclude=["pavo", "braseada", "finas"]),
        _ing(["arroz"],       "carbohidrato", 130.0),
        _ing(["champiñón laminado", "champiñón"],
             "verdura",  120.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Ternera con champiñones y spaghetti", "comida", [
        _ing(["Preparado de carne picada vacuno", "Preparado de carne picada vacuno y cerdo",
              "carne picada"], "proteina", 160.0,
             exclude=["cerdo"]),
        _ing(["spaghetti integral", "spaghetti"], "carbohidrato", 120.0),
        _ing(["champiñón laminado"], "verdura", 120.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Espárragos
    Recipe("Pollo con espárragos y arroz", "comida", [
        _ing(["pechuga"],   "proteina",  160.0,
             exclude=["pavo", "braseada", "finas"]),
        _ing(["arroz"],       "carbohidrato", 130.0),
        _ing(["espárragos blancos",
              "espárrago"], "verdura", 120.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Alcachofas
    Recipe("Pollo con alcachofas y pasta", "comida", [
        _ing(["pechuga"],   "proteina",  160.0,
             exclude=["pavo", "braseada", "finas"]),
        _ing(["macarrón"],   "carbohidrato", 120.0),
        _ing(["corazones de alcachofa",
              "alcachofa"], "verdura", 120.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # ── CENAS nuevas ───────────────────────────────────────────────────────

    # Surimi cenas
    Recipe("Surimi con judías verdes", "cena", [
        _ing(["surimi"],  "proteina",  160.0,
             exclude=["aritos", "muslit"]),
        _ing(["judía verde"], "verdura", 150.0),
        _ing(["tomate"],   "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Bacalao cenas
    Recipe("Bacalao con espinacas y tomate", "cena", [
        _ing(["bacalao"], "proteina", 150.0),
        _ing(["espinaca"], "verdura", 150.0),
        _ing(["tomate"],   "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Bacalao con pimientos y tomate", "cena", [
        _ing(["bacalao"], "proteina", 150.0),
        _ing(["pimiento"], "verdura", 150.0),
        _ing(["tomate frito"], "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Sepia cenas
    Recipe("Sepia con espinacas", "cena", [
        _ing(["sepia"], "proteina", 160.0),
        _ing(["espinaca"], "verdura", 150.0),
        _ing(["tomate"],   "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Sepia con pimientos y cebolla", "cena", [
        _ing(["sepia"], "proteina", 160.0),
        _ing(["pimiento"], "verdura", 130.0),
        _ing(["cebolla"], "verdura", 100.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Pota cenas
    Recipe("Pota con brócoli y tomate", "cena", [
        _ing(["pota"], "proteina", 160.0),
        _ing(["brócoli"],  "verdura", 160.0),
        _ing(["tomate frito"], "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Almejas cenas
    Recipe("Almejas con espinacas", "cena", [
        _ing(["almeja"],   "proteina",  150.0),
        _ing(["espinaca"], "verdura", 150.0),
        _ing(["tomate"],   "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Alas de pollo cenas
    Recipe("Alas de pollo con brócoli", "cena", [
        _ing(["alas de pollo"], "proteina", 200.0),
        _ing(["brócoli"], "verdura", 150.0),
        _ing(["tomate"],   "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Alas de pollo con espinacas", "cena", [
        _ing(["alas de pollo"], "proteina", 200.0),
        _ing(["espinaca"], "verdura", 150.0),
        _ing(["tomate frito"], "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Gambón cenas
    Recipe("Gambón con brócoli y tomate", "cena", [
        _ing(["gambón", "colas de gambón"], "proteina", 180.0),
        _ing(["brócoli"], "verdura", 160.0),
        _ing(["tomate frito"], "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Gambón con espinacas y pimientos", "cena", [
        _ing(["gambón"],      "proteina",  180.0),
        _ing(["espinaca"], "verdura", 130.0),
        _ing(["pimiento"], "verdura", 130.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Gambón con edamame", "cena", [
        _ing(["gambón"],      "proteina",  180.0),
        _ing(["edamame"], "verdura", 150.0),
        _ing(["tomate"],   "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Caballa cenas
    Recipe("Caballa con brócoli", "cena", [
        _ing(["caballa"], "proteina", 140.0),
        _ing(["brócoli"], "verdura", 180.0),
        _ing(["tomate"],   "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Caballa con judías verdes y tomate", "cena", [
        _ing(["caballa"], "proteina", 140.0),
        _ing(["judía verde"], "verdura", 160.0),
        _ing(["tomate frito"], "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Bonito cenas
    Recipe("Bonito con pimientos y espinacas", "cena", [
        _ing(["bonito"], "proteina", 130.0),
        _ing(["pimiento"], "verdura", 130.0),
        _ing(["espinaca"], "verdura", 120.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Mejillones cenas
    Recipe("Mejillones con guisantes y tomate", "cena", [
        _ing(["mejillones"], "proteina", 160.0),
        _ing(["guisante"], "verdura", 150.0),
        _ing(["tomate frito"], "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Mejillones con espinacas", "cena", [
        _ing(["mejillones"], "proteina", 160.0),
        _ing(["espinaca"], "verdura", 170.0),
        _ing(["tomate"],   "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Calamar cenas
    Recipe("Calamar con pimientos", "cena", [
        _ing(["calamar"], "proteina", 160.0,
             exclude=["tinta", "americana"]),
        _ing(["pimiento"], "verdura", 150.0),
        _ing(["tomate frito"], "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Calamar con espinacas y tomate", "cena", [
        _ing(["calamar"], "proteina", 160.0,
             exclude=["tinta", "americana"]),
        _ing(["espinaca"], "verdura", 150.0),
        _ing(["tomate"],   "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Brochetas cenas
    Recipe("Brochetas de pollo con verduras asadas", "cena", [
        _ing(["brochetas de pollo"],
             "proteina",  160.0),
        _ing(["salteado de verduras asadas", "verduras asadas"], "verdura", 180.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Magro cerdo cenas
    Recipe("Magro de cerdo con guisantes", "cena", [
        _ing(["magro de cerdo", "magro"], "proteina", 170.0),
        _ing(["guisante"], "verdura", 160.0),
        _ing(["tomate"],   "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Magro de cerdo con champiñones", "cena", [
        _ing(["magro de cerdo", "magro"], "proteina", 170.0),
        _ing(["champiñón"], "verdura", 160.0),
        _ing(["tomate frito"], "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Lacón cenas
    Recipe("Lacón con brócoli", "cena", [
        _ing(["lacón"],   "proteina",  160.0),
        _ing(["brócoli"], "verdura", 180.0),
        _ing(["tomate"],   "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Lacón con judías verdes", "cena", [
        _ing(["lacón"],   "proteina",  160.0),
        _ing(["judía verde"], "verdura", 170.0),
        _ing(["tomate frito"], "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Burger cenas
    Recipe("Burger de pollo con pimientos", "cena", [
        _ing(["Burger de pollo", "burger pollo"],        "proteina",  160.0,
             exclude=["gruesa", "crunchy"]),
        _ing(["pimiento"], "verdura", 160.0),
        _ing(["tomate"],   "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Burger de vacuno con espinacas", "cena", [
        _ing(["Burger de vacuno y cerdo", "burger vacuno"], "proteina", 160.0),
        _ing(["espinaca"], "verdura", 160.0),
        _ing(["tomate"],   "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Alubias cenas
    Recipe("Alubia blanca con espinacas", "cena", [
        _ing(["alubia blanca"], "legumbre", 150.0),
        _ing(["espinaca"], "verdura", 150.0),
        _ing(["tomate frito"], "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Alubia negra con acelgas", "cena", [
        _ing(["alubia negra"], "legumbre",  150.0),
        _ing(["acelgas"],  "verdura",  180.0),
        _ing(["tomate"],   "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Alubia pinta con judías verdes", "cena", [
        _ing(["alubia pinta"], "legumbre",  150.0),
        _ing(["judía verde"], "verdura", 170.0),
        _ing(["tomate"],   "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Alubia roja con brócoli", "cena", [
        _ing(["alubia roja"],   "legumbre",  150.0),
        _ing(["brócoli"], "verdura", 170.0),
        _ing(["tomate frito"], "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Alubia cocida con pimientos", "cena", [
        _ing(["alubia cocida", "alubia"], "legumbre", 150.0),
        _ing(["pimiento"], "verdura", 160.0),
        _ing(["tomate"],   "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Acelegas cenas
    Recipe("Pechuga con acelgas", "cena", [
        _ing(["pechuga"],   "proteina",  160.0,
             exclude=["pavo", "braseada", "finas"]),
        _ing(["acelgas"],  "verdura",  180.0),
        _ing(["tomate"],   "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Salmón con acelgas", "cena", [
        _ing(["medallones de salmón", "salmón"],
             "proteina",  150.0),
        _ing(["acelgas"],  "verdura",  180.0),
        _ing(["tomate frito"], "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Alcachofas cenas
    Recipe("Merluza con alcachofas", "cena", [
        _ing(["filetes de merluza", "merluza"], "proteina", 160.0),
        _ing(["corazones de alcachofa",
              "alcachofa baby"], "verdura", 160.0),
        _ing(["tomate"],   "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Pollo con alcachofas y espinacas", "cena", [
        _ing(["pechuga"],   "proteina",  160.0,
             exclude=["pavo", "braseada", "finas"]),
        _ing(["corazones de alcachofa"],
             "verdura",  130.0),
        _ing(["espinaca"], "verdura", 120.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Maíz dulce cenas
    Recipe("Atún con maíz y pimientos", "cena", [
        _ing(["atún claro al natural", "atún"],
             "proteina",  120.0, exclude=["empanadilla", "lasaña"]),
        _ing(["maíz dulce", "maíz"],
             "verdura",  150.0),
        _ing(["pimiento"], "verdura", 100.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Pollo con maíz y brócoli", "cena", [
        _ing(["pechuga"],   "proteina",  160.0,
             exclude=["pavo", "braseada", "finas"]),
        _ing(["maíz dulce", "maíz"],
             "verdura",  130.0),
        _ing(["brócoli"], "verdura", 130.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Coles de Bruselas cenas
    Recipe("Salmón con coles de bruselas", "cena", [
        _ing(["medallones de salmón", "salmón"],
             "proteina",  150.0),
        _ing(["coles de bruselas"], "verdura", 180.0),
        _ing(["tomate"],   "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Pechuga con coles de bruselas y tomate", "cena", [
        _ing(["pechuga"],   "proteina",  160.0,
             exclude=["pavo", "braseada", "finas"]),
        _ing(["coles de bruselas"], "verdura", 170.0),
        _ing(["tomate frito"], "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Espárragos cenas
    Recipe("Pollo con espárragos y pimientos", "cena", [
        _ing(["pechuga"],   "proteina",  160.0,
             exclude=["pavo", "braseada", "finas"]),
        _ing(["espárragos blancos",
              "espárrago"], "verdura", 130.0),
        _ing(["pimiento"], "verdura", 120.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Bacalao con espárragos", "cena", [
        _ing(["bacalao"], "proteina", 150.0),
        _ing(["espárragos blancos medianos",
              "espárrago"], "verdura", 160.0),
        _ing(["tomate"],   "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Champiñones cenas
    Recipe("Pechuga con champiñones y espinacas", "cena", [
        _ing(["pechuga"],   "proteina",  160.0,
             exclude=["pavo", "braseada", "finas"]),
        _ing(["champiñón"], "verdura", 130.0),
        _ing(["espinaca"], "verdura", 130.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Atún con champiñones y pimientos", "cena", [
        _ing(["atún"],
             "proteina",  120.0, exclude=["empanadilla", "lasaña"]),
        _ing(["champiñón"], "verdura", 130.0),
        _ing(["pimiento"], "verdura", 130.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Habas cenas
    Recipe("Pollo con habas y pimientos", "cena", [
        _ing(["pechuga"],   "proteina",  160.0,
             exclude=["pavo", "braseada", "finas"]),
        _ing(["habitas muy tiernas", "habas"],
             "verdura",  150.0),
        _ing(["pimiento"], "verdura", 100.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Merluza con habas y tomate", "cena", [
        _ing(["filetes de merluza", "merluza"], "proteina", 160.0),
        _ing(["habitas muy tiernas", "habas"],
             "verdura",  150.0),
        _ing(["tomate frito"], "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Garbanzo + verduras cenas
    Recipe("Garbanzos con brócoli y tomate", "cena", [
        _ing(["garbanzo cocido"],  "legumbre", 160.0),
        _ing(["brócoli"],   "verdura",  150.0),
        _ing(["tomate frito"],        "verdura",   80.0),
        _ing("aceite de oliva",                                  "grasa",    10.0),
    ]),

    # Lomo cenas
    Recipe("Lomo con champiñones", "cena", [
        _ing(["lomo"], "proteina", 160.0,
             exclude=["cabecero", "embuchado", "asado", "pavo"]),
        _ing(["champiñón"], "verdura", 160.0),
        _ing(["tomate frito"], "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Lomo con espárragos y tomate", "cena", [
        _ing(["lomo"], "proteina", 160.0,
             exclude=["cabecero", "embuchado", "asado", "pavo"]),
        _ing(["espárragos blancos",
              "espárrago"], "verdura", 150.0),
        _ing(["tomate"],   "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # Carrilladas cenas
    Recipe("Carrilladas con espinacas", "cena", [
        _ing(["carrilladas"], "proteina", 150.0),
        _ing(["espinaca"], "verdura", 160.0),
        _ing(["tomate"],   "verdura",    80.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),
    Recipe("Carrilladas con brócoli y pimientos", "cena", [
        _ing(["carrilladas"], "proteina", 150.0),
        _ing(["brócoli"], "verdura", 150.0),
        _ing(["pimiento"], "verdura", 100.0),
        _ing("aceite de oliva",                           "grasa",      10.0),
    ]),

    # ── DESAYUNOS nuevos ───────────────────────────────────────────────────

    # Cous cous desayunos (base de cereales)
    Recipe("Leche con galletas y fruta", "desayuno", [
        _ing(["leche entera", "leche"], "lacteo", 250.0,
             exclude=["coco", "condensada", "polvo"]),
        _ing(["galletas maría", "galletas"],
             "carbohidrato", 50.0, exclude=["chocolate", "cacao", "rellena"]),
        _ing(["Naranjas", "naranja"],                    "fruta",     120.0),
    ]),
    Recipe("Leche desnatada con cereales copos de maíz", "desayuno", [
        _ing(["leche desnatada", "leche"], "lacteo", 250.0,
             exclude=["coco", "condensada", "polvo"]),
        _ing(["copos de maíz", "cereales copos"],        "carbohidrato",  60.0),
    ]),
    Recipe("Yogur con galletas digestive", "desayuno", [
        _ing(["yogur natural", "yogur"], "lacteo", 200.0,
             exclude=["griego", "bebida", "kéfir"]),
        _ing(["galletas digestive"], "carbohidrato", 50.0),
        _ing(["Naranjas", "mandarina"],                  "fruta",     100.0),
    ]),
    Recipe("Bebida de avena con muesli", "desayuno", [
        _ing(["bebida de avena"], "lacteo", 250.0),
        _ing(["muesli"],  "carbohidrato",  65.0),
    ]),
    Recipe("Yogur griego con galletas y fruta", "desayuno", [
        _ing(["yogur griego"], "lacteo", 200.0),
        _ing(["galletas tostadas"], "carbohidrato", 50.0),
        _ing(["arándanos"], "fruta", 100.0),
    ]),
    Recipe("Bebida de soja con pan integral", "desayuno", [
        _ing(["bebida de soja"], "lacteo", 250.0),
        _ing(["pan de molde integral",
              "pan integral"],   "carbohidrato", 70.0,
             exclude=["corteza", "semillas", "espelta"]),
    ]),
    Recipe("Leche con tortillas de trigo", "desayuno", [
        _ing(["leche semidesnatada", "leche"], "lacteo", 250.0,
             exclude=["coco", "condensada", "polvo"]),
        _ing(["tortillas de trigo"], "carbohidrato", 70.0),
        _ing(["Naranjas", "mandarina"],                  "fruta",     120.0),
    ]),
    Recipe("Yogur con crackers y fruta", "desayuno", [
        _ing(["yogur natural", "yogur"], "lacteo", 200.0,
             exclude=["griego", "bebida", "kéfir"]),
        _ing(["crackers"],  "carbohidrato", 50.0),
        _ing(["melocotón"], "fruta", 120.0),
    ]),
    Recipe("Leche con pan de molde y fruta", "desayuno", [
        _ing(["leche entera", "leche"], "lacteo", 250.0,
             exclude=["coco", "condensada", "polvo"]),
        _ing(["pan de molde blanco", "pan de molde"],
             "carbohidrato", 70.0, exclude=["integral", "cereales", "semillas"]),
        _ing(["Naranjas", "mandarina"],                  "fruta",     100.0),
    ]),
    Recipe("Queso fresco con pan y fruta", "desayuno", [
        _ing(["queso fresco Burgos",
              "queso fresco"], "lacteo", 200.0,
             exclude=["cabra", "brie", "camembert", "azul"]),
        _ing(["pan de molde blanco", "pan de molde"],
             "carbohidrato", 70.0, exclude=["integral", "cereales"]),
        _ing(["Naranjas", "piña en su jugo"],             "fruta",     120.0),
    ]),
    Recipe("Bebida de almendras con avena y fruta", "desayuno", [
        _ing(["bebida de almendras"], "lacteo", 250.0),
        _ing(["copos de avena"], "carbohidrato", 70.0),
        _ing(["frutos rojos"],
             "fruta",  120.0),
    ]),
    Recipe("Postre lácteo con pan tostado", "desayuno", [
        _ing(["postre lácteo natural", "postre lácteo"], "lacteo", 250.0,
             exclude=["infantil", "crecimiento"]),
        _ing(["pan tostado 100% integral", "pan tostado"],
             "carbohidrato", 60.0, exclude=["chocolate"]),
    ]),
    Recipe("Kéfir con avena y fruta", "desayuno", [
        _ing(["kéfir natural", "kéfir"],
             "lacteo",  250.0),
        _ing(["copos de avena"], "carbohidrato", 70.0),
        _ing(["arándanos",
              "frutos rojos"], "fruta", 100.0),
    ]),
    Recipe("Yogur sabores con pan", "desayuno", [
        _ing(["yogur sabores"], "lacteo", 200.0,
             exclude=["griego", "bifidus"]),
        _ing(["pan de molde blanco", "pan de molde"],
             "carbohidrato", 70.0, exclude=["integral", "cereales"]),
    ]),
    Recipe("Bebida de arroz con galletas", "desayuno", [
        _ing(["bebida de arroz"],
             "lacteo",  250.0),
        _ing(["galletas maría", "galletas"],
             "carbohidrato", 60.0, exclude=["chocolate", "cacao"]),
        _ing(["macedonia"],
             "fruta",  120.0),
    ]),

    # ── COMIDAS ADICIONALES ───────────────────────────────────────────────

    Recipe("Arroz con bacalao y pimientos", "comida", [
        _ing(["bacalao desalado", "bacalao"],
             "proteina",     150.0, exclude=["croqueta", "buñuelo"]),
        _ing(["arroz"],
             "carbohidrato", 130.0),
        _ing(["pimiento"],
             "verdura",      100.0),
        _ing("aceite de oliva",         "grasa",         10.0),
    ]),
    Recipe("Pasta con caballa y tomate", "comida", [
        _ing(["filetes de caballa", "caballa"],
             "proteina",     120.0),
        _ing(["pasta maravilla", "pasta"],
             "carbohidrato", 140.0, exclude=["huevo"]),
        _ing(["tomate frito"],
             "verdura",       80.0),
        _ing("aceite de oliva",         "grasa",         10.0),
    ]),
    Recipe("Arroz con mejillones y verduras", "comida", [
        _ing(["mejillones en escabeche", "mejillones"],
             "proteina",     150.0),
        _ing(["arroz"],
             "carbohidrato", 130.0),
        _ing(["pimiento"],
             "verdura",      100.0),
        _ing("aceite de oliva",         "grasa",         10.0),
    ]),
    Recipe("Quinoa con bacalao y espinacas", "comida", [
        _ing(["bacalao desalado", "bacalao"],
             "proteina",     150.0, exclude=["croqueta", "buñuelo"]),
        _ing(["quinoa", "arroz"],
             "carbohidrato", 100.0),
        _ing(["espinaca"],
             "verdura",      120.0),
        _ing("aceite de oliva",         "grasa",         10.0),
    ]),
    Recipe("Pasta con berberechos y tomate", "comida", [
        _ing(["berberecho al natural", "berberecho"],
             "proteina",     120.0),
        _ing(["pasta maravilla", "pasta"],
             "carbohidrato", 140.0, exclude=["huevo"]),
        _ing(["tomate"],
             "verdura",      100.0),
        _ing("aceite de oliva",         "grasa",         10.0),
    ]),
    Recipe("Arroz con sepia y verduras", "comida", [
        _ing(["sepia limpia", "sepia"],
             "proteina",     150.0),
        _ing(["arroz"],
             "carbohidrato", 130.0),
        _ing(["menestra"],
             "verdura",      120.0),
        _ing("aceite de oliva",         "grasa",         10.0),
    ]),
    Recipe("Arroz con pota y pimientos", "comida", [
        _ing(["pota en su tinta", "pota"],
             "proteina",     150.0),
        _ing(["arroz"],
             "carbohidrato", 130.0),
        _ing(["pimiento"],
             "verdura",      100.0),
        _ing("aceite de oliva",         "grasa",         10.0),
    ]),
    Recipe("Pasta con surimi y tomate", "comida", [
        _ing(["surimi", "palitos de cangrejo"],
             "proteina",     120.0),
        _ing(["pasta maravilla", "pasta"],
             "carbohidrato", 140.0, exclude=["huevo"]),
        _ing(["tomate"],
             "verdura",      100.0),
        _ing("aceite de oliva",         "grasa",         10.0),
    ]),
    Recipe("Lentejas con lomo y zanahoria", "comida", [
        _ing(["lomo de cerdo cocido", "lomo"],
             "proteina",     120.0, exclude=["adobado", "marinado"]),
        _ing(["lenteja"],
             "legumbre",     150.0),
        _ing(["espinaca"],
             "verdura",      100.0),
        _ing("aceite de oliva",         "grasa",         10.0),
    ]),
    Recipe("Garbanzos con pollo y pimientos", "comida", [
        _ing(["pechuga", "pollo"],
             "proteina",     160.0, exclude=["salchicha", "frankfurt"]),
        _ing(["garbanzo cocido", "garbanzo"],
             "legumbre",     160.0),
        _ing(["pimiento"],
             "verdura",      100.0),
        _ing("aceite de oliva",         "grasa",         10.0),
    ]),
    Recipe("Alubias con merluza y brócoli", "comida", [
        _ing(["merluza del cabo", "merluza"],
             "proteina",     160.0, exclude=["croqueta", "rebozado"]),
        _ing(["judía blanca", "alubia blanca", "judía"],
             "legumbre",     150.0),
        _ing(["brócoli"],
             "verdura",      150.0),
        _ing("aceite de oliva",         "grasa",         10.0),
    ]),
    Recipe("Alubias negras con pechuga y espinacas", "comida", [
        _ing(["pechuga", "pollo"],
             "proteina",     160.0, exclude=["salchicha", "frankfurt"]),
        _ing(["judía negra", "alubia negra"],
             "legumbre",     150.0),
        _ing(["espinaca"],
             "verdura",      120.0),
        _ing("aceite de oliva",         "grasa",         10.0),
    ]),
    Recipe("Arroz con gambas y verduras", "comida", [
        _ing(["gamba pelada cruda", "gamba pelada"],
             "proteina",     150.0),
        _ing(["arroz"],
             "carbohidrato", 130.0),
        _ing(["menestra"],
             "verdura",      120.0),
        _ing("aceite de oliva",         "grasa",         10.0),
    ]),
    Recipe("Pasta con gambón y tomate", "comida", [
        _ing(["langostino pelado", "gambón"],
             "proteina",     150.0),
        _ing(["pasta maravilla", "pasta"],
             "carbohidrato", 130.0, exclude=["huevo"]),
        _ing(["tomate frito"],
             "verdura",       80.0),
        _ing("aceite de oliva",         "grasa",         10.0),
    ]),
    Recipe("Quinoa con atún y pimientos", "comida", [
        _ing(["atún en aceite", "atún"],
             "proteina",     100.0, exclude=["empanadilla", "lasaña"]),
        _ing(["quinoa", "arroz"],
             "carbohidrato", 100.0),
        _ing(["pimiento"],
             "verdura",      100.0),
        _ing("aceite de oliva",         "grasa",         10.0),
    ]),
    Recipe("Arroz con bonito y tomate", "comida", [
        _ing(["bonito del norte", "bonito"],
             "proteina",     100.0),
        _ing(["arroz"],
             "carbohidrato", 140.0),
        _ing(["tomate"],
             "verdura",      100.0),
        _ing("aceite de oliva",         "grasa",         10.0),
    ]),
    Recipe("Pasta con bonito y espinacas", "comida", [
        _ing(["bonito del norte", "bonito"],
             "proteina",     100.0),
        _ing(["pasta maravilla", "pasta"],
             "carbohidrato", 140.0, exclude=["huevo"]),
        _ing(["espinaca"],
             "verdura",      120.0),
        _ing("aceite de oliva",         "grasa",         10.0),
    ]),
    Recipe("Alubias pintas con pavo y brócoli", "comida", [
        _ing(["pavo lonchas", "pavo"],
             "proteina",     120.0, exclude=["fiambre", "salchicha"]),
        _ing(["judía pinta", "alubia pinta"],
             "legumbre",     150.0),
        _ing(["brócoli"],
             "verdura",      150.0),
        _ing("aceite de oliva",         "grasa",         10.0),
    ]),
    Recipe("Arroz con almejas y pimientos", "comida", [
        _ing(["almeja hacendado", "almeja"],
             "proteina",     120.0),
        _ing(["arroz"],
             "carbohidrato", 140.0),
        _ing(["pimiento"],
             "verdura",      100.0),
        _ing("aceite de oliva",         "grasa",         10.0),
    ]),
    Recipe("Quinoa con sardinas y verduras", "comida", [
        _ing(["sardinas en aceite", "sardinas"],
             "proteina",     100.0),
        _ing(["quinoa", "arroz"],
             "carbohidrato", 100.0),
        _ing(["espinaca"],
             "verdura",      120.0),
        _ing("aceite de oliva",         "grasa",         10.0),
    ]),

    # ── CENAS ADICIONALES ────────────────────────────────────────────────

    Recipe("Bacalao con brócoli y tomate", "cena", [
        _ing(["bacalao desalado", "bacalao"],
             "proteina",     160.0, exclude=["croqueta", "buñuelo"]),
        _ing(["brócoli"],
             "verdura",      150.0),
        _ing(["tomate"],
             "verdura",       80.0),
        _ing("aceite de oliva",         "grasa",         10.0),
    ]),
    Recipe("Sepia con pimientos y tomate", "cena", [
        _ing(["sepia limpia", "sepia"],
             "proteina",     160.0),
        _ing(["pimiento"],
             "verdura",      150.0),
        _ing(["tomate frito"],
             "verdura",       80.0),
        _ing("aceite de oliva",         "grasa",         10.0),
    ]),
    Recipe("Gambas con espinacas y tomate", "cena", [
        _ing(["gamba pelada cruda", "gamba pelada"],
             "proteina",     160.0),
        _ing(["espinaca"],
             "verdura",      150.0),
        _ing(["tomate"],
             "verdura",       80.0),
        _ing("aceite de oliva",         "grasa",         10.0),
    ]),
    Recipe("Gambón con brócoli y pimientos", "cena", [
        _ing(["langostino pelado", "gambón"],
             "proteina",     160.0),
        _ing(["brócoli"],
             "verdura",      150.0),
        _ing(["pimiento"],
             "verdura",      100.0),
        _ing("aceite de oliva",         "grasa",         10.0),
    ]),
    Recipe("Surimi con pasta y tomate", "cena", [
        _ing(["surimi", "palitos de cangrejo"],
             "proteina",     120.0),
        _ing(["pasta maravilla", "pasta"],
             "carbohidrato", 130.0, exclude=["huevo"]),
        _ing(["tomate frito"],
             "verdura",       80.0),
        _ing("aceite de oliva",         "grasa",         10.0),
    ]),
    Recipe("Pota con verduras y tomate", "cena", [
        _ing(["pota en su tinta", "pota"],
             "proteina",     160.0),
        _ing(["menestra"],
             "verdura",      150.0),
        _ing(["tomate frito"],
             "verdura",       80.0),
        _ing("aceite de oliva",         "grasa",         10.0),
    ]),
    Recipe("Mejillones con brócoli y arroz", "cena", [
        _ing(["mejillones en escabeche", "mejillones"],
             "proteina",     150.0),
        _ing(["brócoli"],
             "verdura",      150.0),
        _ing(["arroz"],
             "carbohidrato", 100.0),
        _ing("aceite de oliva",         "grasa",         10.0),
    ]),
    Recipe("Caballa con espinacas y patata", "cena", [
        _ing(["filetes de caballa", "caballa"],
             "proteina",     120.0),
        _ing(["espinaca"],
             "verdura",      150.0),
        _ing(["patata"],
             "carbohidrato", 150.0),
        _ing("aceite de oliva",         "grasa",         10.0),
    ]),
    Recipe("Bonito con habas y tomate", "cena", [
        _ing(["bonito del norte", "bonito"],
             "proteina",     120.0),
        _ing(["habas baby", "habas"],
             "verdura",      150.0),
        _ing(["tomate"],
             "verdura",       80.0),
        _ing("aceite de oliva",         "grasa",         10.0),
    ]),
    Recipe("Atún con espárragos y tomate", "cena", [
        _ing(["atún en aceite", "atún"],
             "proteina",     120.0, exclude=["empanadilla", "lasaña"]),
        _ing(["espárrago verde", "espárrago"],
             "verdura",      150.0),
        _ing(["tomate frito"],
             "verdura",       80.0),
        _ing("aceite de oliva",         "grasa",         10.0),
    ]),
    Recipe("Pollo con coles de bruselas y tomate", "cena", [
        _ing(["pechuga", "pollo"],
             "proteina",     160.0, exclude=["salchicha", "frankfurt"]),
        _ing(["coles de bruselas", "coles"],
             "verdura",      150.0),
        _ing(["tomate frito"],
             "verdura",       80.0),
        _ing("aceite de oliva",         "grasa",         10.0),
    ]),
    Recipe("Merluza con alcachofas y tomate", "cena", [
        _ing(["merluza del cabo", "merluza"],
             "proteina",     160.0, exclude=["croqueta", "rebozado"]),
        _ing(["alcachofa troceada", "alcachofa"],
             "verdura",      150.0),
        _ing(["tomate frito"],
             "verdura",       80.0),
        _ing("aceite de oliva",         "grasa",         10.0),
    ]),
    Recipe("Pechuga con acelgas y tomate", "cena", [
        _ing(["pechuga", "pollo"],
             "proteina",     160.0, exclude=["salchicha", "frankfurt"]),
        _ing(["acelga troceada", "acelga"],
             "verdura",      160.0),
        _ing(["tomate"],
             "verdura",       80.0),
        _ing("aceite de oliva",         "grasa",         10.0),
    ]),
    Recipe("Carrilladas con menestra", "cena", [
        _ing(["carrilladas de cerdo", "carrilladas"],
             "proteina",     150.0),
        _ing(["menestra"],
             "verdura",      160.0),
        _ing(["tomate frito"],
             "verdura",       80.0),
        _ing("aceite de oliva",         "grasa",         10.0),
    ]),
    Recipe("Lomo con coles de bruselas", "cena", [
        _ing(["lomo de cerdo cocido", "lomo"],
             "proteina",     160.0, exclude=["adobado", "marinado"]),
        _ing(["coles de bruselas", "coles"],
             "verdura",      160.0),
        _ing(["tomate frito"],
             "verdura",       80.0),
        _ing("aceite de oliva",         "grasa",         10.0),
    ]),
    Recipe("Pavo con alcachofas y tomate", "cena", [
        _ing(["pavo lonchas", "pavo"],
             "proteina",     150.0, exclude=["fiambre", "salchicha"]),
        _ing(["alcachofa troceada", "alcachofa"],
             "verdura",      160.0),
        _ing(["tomate"],
             "verdura",       80.0),
        _ing("aceite de oliva",         "grasa",         10.0),
    ]),
    Recipe("Salmón con brócoli y limón", "cena", [
        _ing(["filetes de salmón", "salmón"],
             "proteina",     150.0),
        _ing(["brócoli"],
             "verdura",      160.0),
        _ing(["tomate"],
             "verdura",       80.0),
        _ing("aceite de oliva",         "grasa",         10.0),
    ]),
    Recipe("Salmón con espinacas y arroz", "cena", [
        _ing(["filetes de salmón", "salmón"],
             "proteina",     150.0),
        _ing(["espinaca"],
             "verdura",      150.0),
        _ing(["arroz"],
             "carbohidrato", 100.0),
        _ing("aceite de oliva",         "grasa",         10.0),
    ]),
    Recipe("Salmón con habas y tomate", "cena", [
        _ing(["filetes de salmón", "salmón"],
             "proteina",     150.0),
        _ing(["habas baby", "habas"],
             "verdura",      150.0),
        _ing(["tomate frito"],
             "verdura",       80.0),
        _ing("aceite de oliva",         "grasa",         10.0),
    ]),
    Recipe("Berberechos con pasta y tomate", "cena", [
        _ing(["berberecho al natural", "berberecho"],
             "proteina",     120.0),
        _ing(["pasta maravilla", "pasta"],
             "carbohidrato", 130.0, exclude=["huevo"]),
        _ing(["tomate frito"],
             "verdura",       80.0),
        _ing("aceite de oliva",         "grasa",         10.0),
    ]),

    # ── NUEVOS DESAYUNOS GENÉRICOS ─────────────────────────────────────────

    Recipe("Tostadas con aguacate", "desayuno", [
        _ing(["pan de molde", "pan"],          "carbohidrato", 100.0, exclude=["rallado"]),
        _ing(["aguacate"],                     "fruta",         80.0),
        _ing("aceite",                         "grasa",          5.0),
    ]),
    Recipe("Tortilla francesa", "desayuno", [
        _ing(["huevo", "huevos"],              "proteina",     150.0),
        _ing("aceite",                         "grasa",         10.0),
    ]),
    Recipe("Granola con yogur griego", "desayuno", [
        _ing(["yogur griego"],                 "lacteo",       200.0),
        _ing(["granola", "muesli"],            "carbohidrato",  60.0),
        _ing(["frutos rojos", "fruta"],        "fruta",         80.0),
    ]),
    Recipe("Batido de plátano con avena", "desayuno", [
        _ing(["plátano", "platano"],           "fruta",        120.0),
        _ing(["copos de avena", "avena"],      "carbohidrato",  60.0),
        _ing(["leche"],                        "lacteo",       200.0),
    ]),
    Recipe("Tostadas con queso fresco y tomate", "desayuno", [
        _ing(["pan de molde", "pan"],          "carbohidrato", 100.0, exclude=["rallado"]),
        _ing(["queso fresco", "queso"],        "lacteo",        60.0, exclude=["rallado"]),
        _ing(["tomate triturado", "tomate"],   "verdura",       60.0),
    ]),
    Recipe("Bowl de frutas con yogur", "desayuno", [
        _ing(["yogur"],                        "lacteo",       200.0),
        _ing(["frutos rojos", "manzana", "fruta"], "fruta",   150.0),
    ]),
    Recipe("Avena con canela y manzana", "desayuno", [
        _ing(["copos de avena", "avena"],      "carbohidrato",  80.0),
        _ing(["manzana"],                      "fruta",        120.0),
        _ing(["leche"],                        "lacteo",       200.0),
    ]),
    Recipe("Tostadas con hummus", "desayuno", [
        _ing(["pan de molde", "pan"],          "carbohidrato", 100.0, exclude=["rallado"]),
        _ing(["garbanzo cocido", "garbanzo"],  "legumbre",      60.0),
        _ing("aceite",                         "grasa",          5.0),
    ]),
    Recipe("Yogur con cereales y miel", "desayuno", [
        _ing(["yogur"],                        "lacteo",       200.0),
        _ing(["cereales", "corn flakes", "copos de avena"],
             "carbohidrato", 50.0, exclude=["pan", "molde"]),
    ]),
    Recipe("Pan con aceite y jamón serrano", "desayuno", [
        _ing(["pan de molde", "pan"],          "carbohidrato", 100.0, exclude=["rallado"]),
        _ing("aceite",                         "grasa",         10.0),
        _ing(["jamón serrano", "jamón"],       "proteina",      50.0,
             exclude=["cocido", "pavo", "york"]),
    ]),

    # ── NUEVAS COMIDAS GENÉRICAS ───────────────────────────────────────────

    Recipe("Lentejas con verduras al curry", "comida", [
        _ing(["lenteja"],                      "legumbre",     120.0),
        _ing(["zanahoria", "espinaca"],        "verdura",      100.0),
        _ing(["tomate triturado", "tomate"],   "verdura",       80.0),
        _ing("aceite",                         "grasa",         10.0),
    ]),
    Recipe("Garbanzos con espinacas y tomate", "comida", [
        _ing(["garbanzo"],                     "legumbre",     130.0),
        _ing(["espinaca"],                     "verdura",      120.0),
        _ing(["tomate triturado", "tomate"],   "verdura",       80.0),
        _ing("aceite",                         "grasa",         10.0),
    ]),
    Recipe("Pasta con tomate y atún al horno", "comida", [
        _ing(["atún"],                         "proteina",     100.0,
             exclude=["empanadilla", "lasaña", "empanada"]),
        _ing(["pasta maravilla", "pasta"],     "carbohidrato", 130.0, exclude=["huevo"]),
        _ing(["tomate triturado", "tomate"],   "verdura",      100.0),
        _ing("aceite",                         "grasa",         10.0),
    ]),
    Recipe("Arroz con pollo al curry", "comida", [
        _ing(["pechuga", "pollo"],             "proteina",     160.0),
        _ing(["arroz"],                        "carbohidrato", 130.0),
        _ing(["pimiento"],                     "verdura",      100.0),
        _ing("aceite",                         "grasa",         10.0),
    ]),
    Recipe("Ensalada de pasta con atún y tomate", "comida", [
        _ing(["atún"],                         "proteina",     120.0,
             exclude=["empanadilla", "lasaña", "empanada"]),
        _ing(["pasta maravilla", "pasta"],     "carbohidrato", 120.0, exclude=["huevo"]),
        _ing(["tomate"],                       "verdura",      120.0),
        _ing("aceite",                         "grasa",         10.0),
    ]),
    Recipe("Pisto con huevo", "comida", [
        _ing(["huevo", "huevos"],              "proteina",     120.0),
        _ing(["calabacín"],                    "verdura",      120.0,
             exclude=["empanada", "relleno"]),
        _ing(["pimiento"],                     "verdura",       80.0),
        _ing(["tomate triturado", "tomate"],   "verdura",       80.0),
        _ing("aceite",                         "grasa",         10.0),
    ]),
    Recipe("Crema de verduras con pollo", "comida", [
        _ing(["pechuga", "pollo"],             "proteina",     150.0),
        _ing(["brócoli", "coliflor", "espinaca"], "verdura",  150.0),
        _ing(["zanahoria", "cebolla"],         "verdura",       80.0),
        _ing("aceite",                         "grasa",         10.0),
    ]),
    Recipe("Arroz tres delicias con huevo", "comida", [
        _ing(["huevo", "huevos"],              "proteina",     100.0),
        _ing(["arroz"],                        "carbohidrato", 130.0),
        _ing(["zanahoria", "guisante"],        "verdura",       80.0),
        _ing("aceite",                         "grasa",         10.0),
    ]),
    Recipe("Fideuá con gambas", "comida", [
        _ing(["gamba pelada", "gamba", "langostino"], "proteina", 180.0),
        _ing(["fideo"],                        "carbohidrato", 120.0),
        _ing(["tomate triturado", "tomate"],   "verdura",       80.0),
        _ing("aceite",                         "grasa",         10.0),
    ]),
    Recipe("Judías verdes con jamón", "comida", [
        _ing(["jamón cocido", "jamón"],        "proteina",      80.0),
        _ing(["judía verde"],                  "verdura",      200.0),
        _ing(["tomate triturado", "tomate"],   "verdura",       80.0),
        _ing("aceite",                         "grasa",         10.0),
    ]),

    # ── NUEVAS CENAS GENÉRICAS ─────────────────────────────────────────────

    Recipe("Revuelto de champiñones", "cena", [
        _ing(["huevo", "huevos"],              "proteina",     150.0),
        _ing(["champiñón"],                    "verdura",      150.0),
        _ing("aceite",                         "grasa",         10.0),
    ]),
    Recipe("Tortilla de patatas", "cena", [
        _ing(["huevo", "huevos"],              "proteina",     150.0),
        _ing(["patata"],                       "verdura",      200.0,
             exclude=["prefrita", "fritas", "gajo", "air"]),
        _ing("aceite",                         "grasa",         10.0),
    ]),
    Recipe("Sopa de fideos con pollo", "cena", [
        _ing(["pechuga", "pollo"],             "proteina",     120.0),
        _ing(["fideo"],                        "carbohidrato",  80.0),
        _ing(["tomate triturado", "tomate"],   "verdura",       80.0),
        _ing("aceite",                         "grasa",         10.0),
    ]),
    Recipe("Ensalada de atún con huevo", "cena", [
        _ing(["atún"],                         "proteina",     100.0,
             exclude=["empanadilla", "lasaña", "empanada"]),
        _ing(["huevo", "huevos"],              "proteina",      60.0),
        _ing(["tomate"],                       "verdura",      120.0),
        _ing("aceite",                         "grasa",         10.0),
    ]),
    Recipe("Crema de calabaza", "cena", [
        _ing(["calabacín"],                    "verdura",      200.0,
             exclude=["empanada", "relleno"]),
        _ing(["leche", "nata"],                "lacteo",       100.0),
        _ing("aceite",                         "grasa",         10.0),
    ]),
    Recipe("Pechuga a la plancha con ensalada", "cena", [
        _ing(["pechuga", "pollo"],             "proteina",     180.0),
        _ing(["espinaca"],                     "verdura",      120.0),
        _ing(["tomate"],                       "verdura",       80.0),
        _ing("aceite",                         "grasa",         10.0),
    ]),
    Recipe("Merluza al horno con patatas", "cena", [
        _ing(["filetes de merluza", "merluza"], "proteina",    180.0),
        _ing(["patata"],                        "verdura",     150.0,
             exclude=["prefrita", "fritas", "gajo", "air"]),
        _ing("aceite",                          "grasa",        10.0),
    ]),
    Recipe("Tortilla de espinacas", "cena", [
        _ing(["huevo", "huevos"],              "proteina",     150.0),
        _ing(["espinaca"],                     "verdura",      150.0),
        _ing("aceite",                         "grasa",         10.0),
    ]),
    Recipe("Gazpacho con huevo duro", "cena", [
        _ing(["huevo", "huevos"],              "proteina",     100.0),
        _ing(["tomate triturado", "tomate"],   "verdura",      150.0),
        _ing("aceite",                         "grasa",         10.0),
    ]),
    Recipe("Rollitos de pavo con queso", "cena", [
        _ing(["pavo lonchas", "pavo"],         "proteina",     120.0,
             exclude=["salchicha", "frankfurt", "fiambre"]),
        _ing(["queso en lonchas", "queso"],    "lacteo",        60.0, exclude=["rallado"]),
        _ing(["pan de molde", "pan"],          "carbohidrato",  60.0, exclude=["rallado"]),
    ]),

    # ── NUEVAS PROTEÍNAS INFRARREPRESENTADAS ──────────────────────────────

    # TERNERA Y VACUNO
    Recipe("Filete de ternera con patatas", "comida", [
        _ing(["filete de ternera", "ternera", "vacuno"], "proteina", 180.0),
        _ing(["patata"],                       "verdura",      200.0,
             exclude=["prefrita", "fritas", "gajo", "air"]),
        _ing("aceite",                         "grasa",         10.0),
    ]),
    Recipe("Ternera con champiñones", "comida", [
        _ing(["filete de ternera", "ternera"], "proteina",     180.0),
        _ing(["champiñón"],                    "verdura",      150.0),
        _ing("aceite",                         "grasa",         10.0),
    ]),
    Recipe("Hamburguesa de vacuno con ensalada", "comida", [
        _ing(["Burger de vacuno", "carne picada"], "proteina", 200.0),
        _ing(["tomate"],                       "verdura",      100.0),
        _ing(["pan de molde", "pan"],          "carbohidrato",  60.0, exclude=["rallado"]),
        _ing("aceite",                         "grasa",         10.0),
    ]),
    Recipe("Albóndigas de ternera con tomate", "cena", [
        _ing(["carne picada", "ternera"],      "proteina",     180.0),
        _ing(["tomate triturado", "tomate frito"], "verdura",  150.0),
        _ing("aceite",                         "grasa",         10.0),
    ]),
    Recipe("Ternera salteada con verduras", "cena", [
        _ing(["filete de ternera", "ternera"], "proteina",     160.0),
        _ing(["pimiento"],                     "verdura",      120.0),
        _ing(["arroz", "arroz redondo"],       "carbohidrato",  80.0),
        _ing("aceite",                         "grasa",         10.0),
    ]),

    # CERDO FRESCO
    Recipe("Lomo de cerdo con patatas", "comida", [
        _ing(["lomo de cerdo", "lomo"],        "proteina",     180.0),
        _ing(["patata"],                       "verdura",      150.0,
             exclude=["prefrita", "fritas", "gajo", "air"]),
        _ing("aceite",                         "grasa",         10.0),
    ]),
    Recipe("Chuletas de cerdo con verduras", "comida", [
        _ing(["lomo de cerdo", "cerdo"],       "proteina",     200.0),
        _ing(["pimiento"],                     "verdura",      120.0),
        _ing(["tomate"],                       "verdura",       80.0),
        _ing("aceite",                         "grasa",         10.0),
    ]),
    Recipe("Solomillo de cerdo con champiñones", "cena", [
        _ing(["lomo de cerdo", "solomillo"],   "proteina",     180.0),
        _ing(["champiñón"],                    "verdura",      150.0),
        _ing("aceite",                         "grasa",         10.0),
    ]),

    # SALMÓN FRESCO
    Recipe("Salmón al horno con patatas", "comida", [
        _ing(["salmón", "filetes de salmón"],  "proteina",     180.0),
        _ing(["patata"],                       "verdura",      200.0,
             exclude=["prefrita", "fritas", "gajo", "air"]),
        _ing("aceite",                         "grasa",         10.0),
    ]),
    Recipe("Salmón con quinoa y espinacas", "comida", [
        _ing(["salmón", "filetes de salmón"],  "proteina",     160.0),
        _ing(["quinoa"],                       "carbohidrato",  80.0),
        _ing(["espinaca"],                     "verdura",      100.0),
        _ing("aceite",                         "grasa",         10.0),
    ]),
    Recipe("Salmón a la plancha con arroz", "cena", [
        _ing(["salmón", "filetes de salmón"],  "proteina",     160.0),
        _ing(["arroz basmati", "arroz"],       "carbohidrato",  80.0),
        _ing(["espinaca"],                     "verdura",       80.0),
        _ing("aceite",                         "grasa",         10.0),
    ]),
    Recipe("Salmón con brócoli al vapor", "cena", [
        _ing(["salmón", "filetes de salmón"],  "proteina",     160.0),
        _ing(["brócoli"],                      "verdura",      200.0),
        _ing("aceite",                         "grasa",         10.0),
    ]),

    # MERLUZA FRESCA
    Recipe("Merluza al horno con verduras", "comida", [
        _ing(["filetes de merluza", "merluza"], "proteina",    200.0),
        _ing(["pimiento"],                      "verdura",     100.0),
        _ing(["tomate"],                        "verdura",     100.0),
        _ing("aceite",                          "grasa",        10.0),
    ]),
    Recipe("Merluza con patatas a la gallega", "comida", [
        _ing(["filetes de merluza", "merluza"], "proteina",    200.0),
        _ing(["patata"],                        "verdura",     200.0,
             exclude=["prefrita", "fritas", "gajo", "air"]),
        _ing("aceite",                          "grasa",        15.0),
    ]),
    Recipe("Merluza en salsa verde", "cena", [
        _ing(["filetes de merluza", "merluza"], "proteina",    180.0),
        _ing(["guisante"],                      "verdura",     100.0),
        _ing("aceite",                          "grasa",        10.0),
    ]),

    # PAVO FRESCO
    Recipe("Pavo con calabacín y arroz", "comida", [
        _ing(["pechuga de pavo", "pavo", "pechuga"], "proteina", 180.0),
        _ing(["calabacín"],                    "verdura",      150.0),
        _ing(["arroz", "arroz redondo"],       "carbohidrato",  80.0),
        _ing("aceite",                         "grasa",         10.0),
    ]),
    Recipe("Pavo al curry con arroz basmati", "comida", [
        _ing(["pechuga de pavo", "pavo", "pechuga"], "proteina", 180.0),
        _ing(["arroz basmati", "arroz"],       "carbohidrato",  90.0),
        _ing(["espinaca"],                     "verdura",       80.0),
        _ing("aceite",                         "grasa",         10.0),
    ]),
    Recipe("Pavo salteado con pimientos", "cena", [
        _ing(["pechuga de pavo", "pavo", "pechuga"], "proteina", 160.0),
        _ing(["pimiento"],                     "verdura",      150.0),
        _ing(["pasta", "macarrón"],            "carbohidrato",  80.0),
        _ing("aceite",                         "grasa",         10.0),
    ]),
    Recipe("Pavo con espárragos", "cena", [
        _ing(["pechuga de pavo", "pavo", "pechuga"], "proteina", 160.0),
        _ing(["espárrago", "judía verde"],     "verdura",      150.0),
        _ing("aceite",                         "grasa",         10.0),
    ]),
    Recipe("Pavo con berenjena y tomate", "cena", [
        _ing(["pechuga de pavo", "pavo", "pechuga"], "proteina", 160.0),
        _ing(["berenjena"],                    "verdura",      150.0),
        _ing(["tomate triturado", "tomate"],   "verdura",      100.0),
        _ing("aceite",                         "grasa",         10.0),
    ]),

    # ── NUEVAS VERDURAS INFRARREPRESENTADAS ───────────────────────────────

    # CALABACÍN como protagonista
    Recipe("Pasta con calabacín y atún", "comida", [
        _ing(["atún"],                         "proteina",     120.0,
             exclude=["empanadilla", "lasaña", "empanada"]),
        _ing(["pasta", "macarrón"],            "carbohidrato", 100.0),
        _ing(["calabacín"],                    "verdura",      200.0),
        _ing("aceite",                         "grasa",         10.0),
    ]),
    Recipe("Arroz con calabacín y gambas", "comida", [
        _ing(["gambón", "gamba pelada"],       "proteina",     150.0),
        _ing(["arroz", "arroz redondo"],       "carbohidrato",  90.0),
        _ing(["calabacín"],                    "verdura",      180.0),
        _ing("aceite",                         "grasa",         10.0),
    ]),
    Recipe("Calabacín relleno de carne", "cena", [
        _ing(["carne picada", "ternera"],      "proteina",     160.0),
        _ing(["calabacín"],                    "verdura",      200.0),
        _ing(["tomate triturado", "tomate frito"], "verdura",   80.0),
        _ing("aceite",                         "grasa",         10.0),
    ]),
    Recipe("Tortilla de calabacín", "cena", [
        _ing(["huevo", "huevos"],              "proteina",     150.0),
        _ing(["calabacín"],                    "verdura",      200.0),
        _ing("aceite",                         "grasa",         15.0),
    ]),

    # ZANAHORIA como protagonista
    Recipe("Pollo con zanahoria y arroz", "comida", [
        _ing(["pechuga", "pollo"],             "proteina",     160.0),
        _ing(["arroz", "arroz redondo"],       "carbohidrato",  90.0),
        _ing(["zanahoria"],                    "verdura",      150.0),
        _ing("aceite",                         "grasa",         10.0),
    ]),
    Recipe("Crema de zanahoria con pollo", "cena", [
        _ing(["pechuga", "pollo"],             "proteina",     130.0),
        _ing(["zanahoria"],                    "verdura",      250.0),
        _ing("aceite",                         "grasa",         10.0),
    ]),
    Recipe("Merluza con zanahoria al vapor", "cena", [
        _ing(["filetes de merluza", "merluza"], "proteina",    180.0),
        _ing(["zanahoria"],                     "verdura",     150.0),
        _ing(["patata"],                        "verdura",     100.0,
             exclude=["prefrita", "fritas", "gajo", "air"]),
        _ing("aceite",                          "grasa",        10.0),
    ]),

    # BERENJENA como protagonista
    Recipe("Berenjena rellena de atún", "cena", [
        _ing(["atún"],                         "proteina",     120.0,
             exclude=["empanadilla", "lasaña", "empanada"]),
        _ing(["berenjena"],                    "verdura",      200.0),
        _ing(["tomate triturado", "tomate"],   "verdura",       80.0),
        _ing("aceite",                         "grasa",         10.0),
    ]),
    Recipe("Pisto con berenjena y huevo", "cena", [
        _ing(["huevo", "huevos"],              "proteina",     100.0),
        _ing(["berenjena"],                    "verdura",      150.0),
        _ing(["pimiento"],                     "verdura",      100.0),
        _ing(["tomate triturado", "tomate frito"], "verdura",   80.0),
        _ing("aceite",                         "grasa",         15.0),
    ]),
    Recipe("Pasta con berenjena y carne", "comida", [
        _ing(["carne picada", "ternera"],      "proteina",     150.0),
        _ing(["pasta", "macarrón"],            "carbohidrato", 100.0),
        _ing(["berenjena"],                    "verdura",      150.0),
        _ing(["tomate triturado"],             "verdura",       80.0),
        _ing("aceite",                         "grasa",         10.0),
    ]),

    # CEBOLLA Y PUERRO como protagonistas
    Recipe("Sopa de cebolla con pollo", "cena", [
        _ing(["pechuga", "pollo"],             "proteina",     130.0),
        _ing(["cebolla"],                      "verdura",      200.0),
        _ing(["pan de molde", "pan"],          "carbohidrato",  40.0, exclude=["rallado"]),
        _ing("aceite",                         "grasa",         10.0),
    ]),
    Recipe("Tortilla de cebolla y pimiento", "cena", [
        _ing(["huevo", "huevos"],              "proteina",     150.0),
        _ing(["cebolla"],                      "verdura",      150.0),
        _ing(["pimiento"],                     "verdura",      100.0),
        _ing("aceite",                         "grasa",         15.0),
    ]),

    # COLIFLOR
    Recipe("Coliflor con bechamel y jamón", "comida", [
        _ing(["jamón cocido", "pavo lonchas"], "proteina",     100.0),
        _ing(["coliflor", "menestra"],         "verdura",      300.0),
        _ing(["leche semidesnatada", "leche"], "lacteo",       100.0),
        _ing("aceite",                         "grasa",         10.0),
    ]),
    Recipe("Arroz con coliflor y gambas", "comida", [
        _ing(["gambón", "gamba pelada"],       "proteina",     150.0),
        _ing(["arroz", "arroz redondo"],       "carbohidrato",  90.0),
        _ing(["coliflor", "menestra"],         "verdura",      200.0),
        _ing("aceite",                         "grasa",         10.0),
    ]),

    # PATATA como protagonista
    Recipe("Tortilla española con jamón", "cena", [
        _ing(["huevo", "huevos"],              "proteina",     150.0),
        _ing(["patata"],                       "verdura",      200.0,
             exclude=["prefrita", "fritas", "gajo", "air"]),
        _ing(["jamón cocido", "lomo de cerdo cocido"], "proteina", 60.0),
        _ing("aceite",                         "grasa",         20.0),
    ]),
    Recipe("Patatas bravas con huevo", "cena", [
        _ing(["huevo", "huevos"],              "proteina",     100.0),
        _ing(["patata"],                       "verdura",      250.0,
             exclude=["prefrita", "fritas", "gajo", "air"]),
        _ing(["tomate frito"],                 "verdura",       60.0),
        _ing("aceite",                         "grasa",         20.0),
    ]),

    # ESPÁRRAGOS Y JUDÍA VERDE
    Recipe("Espárragos con jamón y huevo", "cena", [
        _ing(["huevo", "huevos"],              "proteina",     100.0),
        _ing(["jamón cocido", "pavo lonchas"], "proteina",      80.0),
        _ing(["espárrago", "judía verde"],     "verdura",      200.0),
        _ing("aceite",                         "grasa",         10.0),
    ]),
    Recipe("Alcachofas con pollo", "comida", [
        _ing(["pechuga", "pollo"],             "proteina",     160.0),
        _ing(["alcachofa", "menestra"],        "verdura",      200.0),
        _ing(["arroz", "arroz redondo"],       "carbohidrato",  80.0),
        _ing("aceite",                         "grasa",         10.0),
    ]),
    Recipe("Judías verdes con salmón", "cena", [
        _ing(["salmón", "filetes de salmón"],  "proteina",     160.0),
        _ing(["judía verde"],                  "verdura",      200.0),
        _ing("aceite",                         "grasa",         10.0),
    ]),
    Recipe("Puerro con bacalao", "cena", [
        _ing(["bacalao"],                      "proteina",     180.0),
        _ing(["puerro", "cebolla"],            "verdura",      200.0),
        _ing(["patata"],                       "verdura",      100.0,
             exclude=["prefrita", "fritas", "gajo", "air"]),
        _ing("aceite",                         "grasa",         10.0),
    ]),

    # ── NUEVOS DESAYUNOS VARIADOS ─────────────────────────────────────────

    # CON PROTEÍNA
    Recipe("Tortilla francesa con jamón", "desayuno", [
        _ing(["huevo", "huevos"],              "proteina",     120.0),
        _ing(["jamón cocido", "pavo lonchas"], "proteina",      60.0),
        _ing(["pan de molde", "pan"],          "carbohidrato",  60.0, exclude=["rallado"]),
        _ing("aceite",                         "grasa",         10.0),
    ]),
    Recipe("Tostadas con salmón ahumado", "desayuno", [
        _ing(["salmón", "filetes de salmón"],  "proteina",      80.0),
        _ing(["pan de molde", "pan"],          "carbohidrato",  80.0, exclude=["rallado"]),
        _ing("aceite",                         "grasa",         10.0),
    ]),
    Recipe("Revuelto de huevo con champiñones", "desayuno", [
        _ing(["huevo", "huevos"],              "proteina",     150.0),
        _ing(["champiñón"],                    "verdura",      100.0),
        _ing(["pan de molde", "pan"],          "carbohidrato",  60.0, exclude=["rallado"]),
        _ing("aceite",                         "grasa",         10.0),
    ]),
    Recipe("Yogur griego con frutos secos", "desayuno", [
        _ing(["yogur griego", "yogur"],        "lacteo",       200.0),
        _ing(["nuez", "almendra"],             "grasa",         30.0),
        _ing(["copos de avena", "avena"],      "carbohidrato",  40.0),
    ]),
    Recipe("Tostadas con pavo y queso", "desayuno", [
        _ing(["pavo lonchas", "jamón cocido"], "proteina",      80.0,
             exclude=["salchicha", "frankfurt", "fiambre"]),
        _ing(["pan de molde", "pan"],          "carbohidrato",  80.0, exclude=["rallado"]),
        _ing(["queso fresco", "queso"],        "lacteo",        40.0, exclude=["rallado"]),
    ]),

    # CON FRUTA
    Recipe("Batido de yogur con plátano", "desayuno", [
        _ing(["yogur natural", "yogur"],       "lacteo",       200.0),
        _ing(["plátano", "fruta"],             "fruta",        100.0),
        _ing(["copos de avena", "avena"],      "carbohidrato",  40.0),
    ]),
    Recipe("Bowl de avena con frutos rojos", "desayuno", [
        _ing(["copos de avena", "avena"],      "carbohidrato",  80.0),
        _ing(["leche semidesnatada", "leche"], "lacteo",       200.0),
        _ing(["fruta"],                        "fruta",         80.0),
    ]),
    Recipe("Tostadas con queso fresco y fruta", "desayuno", [
        _ing(["pan de molde", "pan"],          "carbohidrato",  80.0, exclude=["rallado"]),
        _ing(["queso fresco", "queso"],        "lacteo",        60.0, exclude=["rallado"]),
        _ing(["fruta"],                        "fruta",         80.0),
    ]),
    Recipe("Yogur con mango y granola", "desayuno", [
        _ing(["yogur natural", "yogur"],       "lacteo",       200.0),
        _ing(["fruta"],                        "fruta",        100.0),
        _ing(["copos de avena", "muesli"],     "carbohidrato",  40.0),
        _ing(["nuez", "almendra"],             "grasa",         20.0),
    ]),
    Recipe("Smoothie de leche con avena y fruta", "desayuno", [
        _ing(["leche semidesnatada", "leche"], "lacteo",       250.0),
        _ing(["copos de avena", "avena"],      "carbohidrato",  50.0),
        _ing(["fruta"],                        "fruta",        100.0),
    ]),

    # SALADOS
    Recipe("Huevos revueltos con tomate", "desayuno", [
        _ing(["huevo", "huevos"],              "proteina",     150.0),
        _ing(["tomate triturado", "tomate"],   "verdura",       80.0),
        _ing(["pan de molde", "pan"],          "carbohidrato",  60.0, exclude=["rallado"]),
        _ing("aceite",                         "grasa",         10.0),
    ]),
    Recipe("Pan con aceite y tomate", "desayuno", [
        _ing(["pan de molde", "pan"],          "carbohidrato", 100.0, exclude=["rallado"]),
        _ing(["tomate"],                       "verdura",       80.0),
        _ing("aceite",                         "grasa",         15.0),
    ]),
    Recipe("Tostadas con aguacate y huevo", "desayuno", [
        _ing(["huevo", "huevos"],              "proteina",     100.0),
        _ing(["pan de molde", "pan"],          "carbohidrato",  80.0, exclude=["rallado"]),
        _ing(["aguacate", "nuez"],             "grasa",         60.0),
    ]),
    Recipe("Crêpe de avena con jamón", "desayuno", [
        _ing(["huevo", "huevos"],              "proteina",     100.0),
        _ing(["copos de avena", "avena"],      "carbohidrato",  60.0),
        _ing(["jamón cocido", "pavo lonchas"], "proteina",      60.0),
        _ing(["leche semidesnatada", "leche"], "lacteo",        80.0),
    ]),
    Recipe("Tostadas con queso fresco y tomate", "desayuno", [
        _ing(["pan de molde", "pan"],          "carbohidrato",  80.0, exclude=["rallado"]),
        _ing(["queso fresco", "queso"],        "lacteo",        80.0, exclude=["rallado"]),
        _ing(["tomate"],                       "verdura",       60.0),
    ]),

    # DULCES
    Recipe("Porridge de avena con fruta", "desayuno", [
        _ing(["copos de avena", "avena"],      "carbohidrato",  80.0),
        _ing(["leche semidesnatada", "leche"], "lacteo",       200.0),
        _ing(["fruta"],                        "fruta",         80.0),
    ]),
    Recipe("Cereales con leche y plátano", "desayuno", [
        _ing(["cereal"],                       "carbohidrato",  60.0, exclude=["pan"]),
        _ing(["leche semidesnatada", "leche"], "lacteo",       200.0),
        _ing(["plátano", "fruta"],             "fruta",         80.0),
    ]),
    Recipe("Tostadas con mantequilla de frutos secos", "desayuno", [
        _ing(["pan de molde", "pan"],          "carbohidrato",  80.0, exclude=["rallado"]),
        _ing(["nuez", "almendra"],             "grasa",         40.0),
        _ing(["fruta"],                        "fruta",         80.0),
    ]),
    Recipe("Kéfir con muesli y nueces", "desayuno", [
        _ing(["kéfir", "yogur"],               "lacteo",       200.0),
        _ing(["muesli", "copos de avena"],     "carbohidrato",  60.0),
        _ing(["nuez", "almendra"],             "grasa",         25.0),
    ]),
    Recipe("Galletas con leche y frutos secos", "desayuno", [
        _ing(["leche semidesnatada", "leche"], "lacteo",       250.0),
        _ing(["galletas", "galleta"],          "carbohidrato",  60.0),
        _ing(["nuez", "almendra"],             "grasa",         20.0),
    ]),

    # ── NUEVAS RECETAS — VARIEDAD MÁXIMA ─────────────────────────────

    # ── COMIDAS CON TERNERA Y VACUNO ──────────────────────────────────
    Recipe("Estofado de ternera con patatas", "comida", [
        _ing(["filete de ternera", "ternera"],        "proteina",     200.0),
        _ing(["patata"],                               "verdura",      200.0),
        _ing(["zanahoria"],                            "verdura",      100.0),
        _ing(["aceite de oliva"],                      "grasa",         10.0),
    ]),
    Recipe("Ternera con judías verdes", "comida", [
        _ing(["filete de ternera", "ternera"],        "proteina",     180.0),
        _ing(["judía verde"],                          "verdura",      200.0),
        _ing(["tomate triturado", "tomate"],           "verdura",       80.0),
        _ing(["aceite de oliva"],                      "grasa",         10.0),
    ]),
    Recipe("Carne picada con macarrones", "comida", [
        _ing(["carne picada", "ternera"],              "proteina",     160.0),
        _ing(["macarrón", "pasta"],                    "carbohidrato", 100.0),
        _ing(["tomate triturado"],                     "verdura",       80.0),
        _ing(["aceite de oliva"],                      "grasa",         10.0),
    ]),
    Recipe("Vacuno con arroz y pimientos", "comida", [
        _ing(["Burger de vacuno", "carne picada"],     "proteina",     180.0),
        _ing(["arroz", "arroz redondo"],               "carbohidrato",  90.0),
        _ing(["pimiento"],                             "verdura",      120.0),
        _ing(["aceite de oliva"],                      "grasa",         10.0),
    ]),
    Recipe("Ternera con espinacas y pasta", "comida", [
        _ing(["filete de ternera", "ternera"],        "proteina",     180.0),
        _ing(["pasta", "macarrón"],                    "carbohidrato",  90.0),
        _ing(["espinaca"],                             "verdura",      100.0),
        _ing(["aceite de oliva"],                      "grasa",         10.0),
    ]),
    Recipe("Hamburguesa de ternera con patatas", "comida", [
        _ing(["carne picada", "Burger de vacuno"],     "proteina",     200.0),
        _ing(["patata"],                               "verdura",      200.0),
        _ing(["tomate"],                               "verdura",       80.0),
        _ing(["aceite de oliva"],                      "grasa",         15.0),
    ]),

    # ── COMIDAS CON CERDO FRESCO ──────────────────────────────────────
    Recipe("Cerdo con lentejas", "comida", [
        _ing(["lomo de cerdo", "cerdo"],              "proteina",     160.0),
        _ing(["lenteja"],                              "legumbre",     120.0),
        _ing(["zanahoria"],                            "verdura",      100.0),
        _ing(["aceite de oliva"],                      "grasa",         10.0),
    ]),
    Recipe("Cerdo con quinoa y verduras", "comida", [
        _ing(["lomo de cerdo", "cerdo"],              "proteina",     160.0),
        _ing(["quinoa"],                               "carbohidrato",  80.0),
        _ing(["pimiento"],                             "verdura",      120.0),
        _ing(["aceite de oliva"],                      "grasa",         10.0),
    ]),
    Recipe("Lomo de cerdo con arroz basmati", "comida", [
        _ing(["lomo de cerdo"],                        "proteina",     180.0),
        _ing(["arroz basmati", "arroz"],               "carbohidrato",  90.0),
        _ing(["espinaca"],                             "verdura",       80.0),
        _ing(["aceite de oliva"],                      "grasa",         10.0),
    ]),
    Recipe("Cerdo con garbanzos al curry", "comida", [
        _ing(["lomo de cerdo", "cerdo"],              "proteina",     160.0),
        _ing(["garbanzo"],                             "legumbre",     120.0),
        _ing(["espinaca"],                             "verdura",       80.0),
        _ing(["aceite de oliva"],                      "grasa",         10.0),
    ]),

    # ── COMIDAS CON PESCADO VARIADO ───────────────────────────────────
    Recipe("Dorada al horno con patatas", "comida", [
        _ing(["filetes de merluza", "merluza"],        "proteina",     200.0),
        _ing(["patata"],                               "verdura",      200.0),
        _ing(["tomate"],                               "verdura",       80.0),
        _ing(["aceite de oliva"],                      "grasa",         10.0),
    ]),
    Recipe("Caballa con arroz integral", "comida", [
        _ing(["caballa", "sardina"],                   "proteina",     160.0),
        _ing(["arroz integral", "arroz"],              "carbohidrato",  90.0),
        _ing(["tomate triturado"],                     "verdura",       80.0),
        _ing(["aceite de oliva"],                      "grasa",         10.0),
    ]),
    Recipe("Atún fresco con pasta", "comida", [
        _ing(["atún", "atún claro al natural"],        "proteina",     150.0),
        _ing(["pasta", "spaghetti integral"],          "carbohidrato", 100.0),
        _ing(["tomate frito"],                         "verdura",       80.0),
        _ing(["aceite de oliva"],                      "grasa",         10.0),
    ]),
    Recipe("Bacalao con garbanzos", "comida", [
        _ing(["bacalao"],                              "proteina",     180.0),
        _ing(["garbanzo"],                             "legumbre",     150.0),
        _ing(["espinaca"],                             "verdura",       80.0),
        _ing(["aceite de oliva"],                      "grasa",         10.0),
    ]),
    Recipe("Sardinas con pasta y tomate", "comida", [
        _ing(["sardina"],                              "proteina",     150.0),
        _ing(["pasta", "macarrón"],                    "carbohidrato", 100.0),
        _ing(["tomate frito"],                         "verdura",       80.0),
        _ing(["aceite de oliva"],                      "grasa",         10.0),
    ]),
    Recipe("Salmón con lentejas rojas", "comida", [
        _ing(["salmón", "filetes de salmón"],          "proteina",     160.0),
        _ing(["lenteja"],                              "legumbre",     120.0),
        _ing(["espinaca"],                             "verdura",       80.0),
        _ing(["aceite de oliva"],                      "grasa",         10.0),
    ]),

    # ── COMIDAS DE LEGUMBRES ──────────────────────────────────────────
    Recipe("Garbanzos con arroz y curry", "comida", [
        _ing(["garbanzo"],                             "legumbre",     180.0),
        _ing(["arroz", "arroz redondo"],               "carbohidrato",  90.0),
        _ing(["espinaca"],                             "verdura",       80.0),
        _ing(["aceite de oliva"],                      "grasa",         10.0),
    ]),
    Recipe("Lentejas con quinoa", "comida", [
        _ing(["lenteja"],                              "legumbre",     150.0),
        _ing(["quinoa"],                               "carbohidrato",  80.0),
        _ing(["zanahoria"],                            "verdura",      100.0),
        _ing(["aceite de oliva"],                      "grasa",         10.0),
    ]),
    Recipe("Alubias con verduras", "comida", [
        _ing(["alubia"],                               "legumbre",     180.0),
        _ing(["pimiento"],                             "verdura",      100.0),
        _ing(["tomate triturado"],                     "verdura",       80.0),
        _ing(["aceite de oliva"],                      "grasa",         10.0),
    ]),
    Recipe("Huevos con patatas y pimiento", "comida", [
        _ing(["huevo"],                                "proteina",     150.0),
        _ing(["patata"],                               "verdura",      200.0),
        _ing(["pimiento"],                             "verdura",      100.0),
        _ing(["aceite de oliva"],                      "grasa",         15.0),
    ]),

    # ── CENAS CON TERNERA ─────────────────────────────────────────────
    Recipe("Ternera con brócoli salteado", "cena", [
        _ing(["filete de ternera", "ternera"],        "proteina",     160.0),
        _ing(["brócoli"],                              "verdura",      200.0),
        _ing(["aceite de oliva"],                      "grasa",         10.0),
    ]),
    Recipe("Albóndigas con espinacas", "cena", [
        _ing(["carne picada", "ternera"],              "proteina",     160.0),
        _ing(["espinaca"],                             "verdura",      150.0),
        _ing(["tomate frito"],                         "verdura",       60.0),
        _ing(["aceite de oliva"],                      "grasa",         10.0),
    ]),
    Recipe("Carne picada con calabacín", "cena", [
        _ing(["carne picada", "ternera"],              "proteina",     160.0),
        _ing(["calabacín"],                            "verdura",      200.0),
        _ing(["tomate triturado"],                     "verdura",       80.0),
        _ing(["aceite de oliva"],                      "grasa",         10.0),
    ]),

    # ── CENAS CON CERDO ───────────────────────────────────────────────
    Recipe("Cerdo con judías verdes", "cena", [
        _ing(["lomo de cerdo", "cerdo"],              "proteina",     160.0),
        _ing(["judía verde"],                          "verdura",      200.0),
        _ing(["aceite de oliva"],                      "grasa",         10.0),
    ]),
    Recipe("Lomo con pimientos asados", "cena", [
        _ing(["lomo de cerdo"],                        "proteina",     160.0),
        _ing(["pimiento"],                             "verdura",      180.0),
        _ing(["aceite de oliva"],                      "grasa",         10.0),
    ]),
    Recipe("Cerdo con coliflor al vapor", "cena", [
        _ing(["lomo de cerdo", "cerdo"],              "proteina",     160.0),
        _ing(["coliflor", "menestra"],                 "verdura",      200.0),
        _ing(["aceite de oliva"],                      "grasa",         10.0),
    ]),

    # ── CENAS CON PESCADO ─────────────────────────────────────────────
    Recipe("Caballa con espinacas", "cena", [
        _ing(["caballa", "sardina"],                   "proteina",     160.0),
        _ing(["espinaca"],                             "verdura",      150.0),
        _ing(["aceite de oliva"],                      "grasa",         10.0),
    ]),
    Recipe("Atún con aguacate y tomate", "cena", [
        _ing(["atún", "atún claro al natural"],        "proteina",     140.0),
        _ing(["tomate"],                               "verdura",      100.0),
        _ing(["aguacate"],                             "grasa",         60.0),
    ]),
    Recipe("Sardinas con verduras asadas", "cena", [
        _ing(["sardina"],                              "proteina",     160.0),
        _ing(["pimiento"],                             "verdura",      150.0),
        _ing(["tomate"],                               "verdura",       80.0),
        _ing(["aceite de oliva"],                      "grasa",         10.0),
    ]),
    Recipe("Bacalao con pimientos", "cena", [
        _ing(["bacalao"],                              "proteina",     180.0),
        _ing(["pimiento"],                             "verdura",      150.0),
        _ing(["tomate frito"],                         "verdura",       60.0),
        _ing(["aceite de oliva"],                      "grasa",         10.0),
    ]),
    Recipe("Merluza con champiñones", "cena", [
        _ing(["filetes de merluza", "merluza"],        "proteina",     180.0),
        _ing(["champiñón", "champiñones"],             "verdura",      150.0),
        _ing(["aceite de oliva"],                      "grasa",         10.0),
    ]),

    # ── CENAS CON HUEVO VARIADAS ──────────────────────────────────────
    Recipe("Revuelto de gambas", "cena", [
        _ing(["huevo"],                                "proteina",     120.0),
        _ing(["gambón", "gamba pelada"],               "proteina",     100.0),
        _ing(["espinaca"],                             "verdura",       80.0),
        _ing(["aceite de oliva"],                      "grasa",         10.0),
    ]),
    Recipe("Revuelto de salmón ahumado", "cena", [
        _ing(["huevo"],                                "proteina",     120.0),
        _ing(["salmón", "filetes de salmón"],          "proteina",      80.0),
        _ing(["espinaca"],                             "verdura",       80.0),
        _ing(["aceite de oliva"],                      "grasa",         10.0),
    ]),
    Recipe("Tortilla de atún y pimiento", "cena", [
        _ing(["huevo"],                                "proteina",     150.0),
        _ing(["atún", "atún claro al natural"],        "proteina",      80.0),
        _ing(["pimiento"],                             "verdura",      100.0),
        _ing(["aceite de oliva"],                      "grasa",         10.0),
    ]),
    Recipe("Huevos al plato con tomate", "cena", [
        _ing(["huevo"],                                "proteina",     150.0),
        _ing(["tomate triturado", "tomate frito"],     "verdura",      150.0),
        _ing(["pan de molde", "pan"],                  "carbohidrato",  60.0),
        _ing(["aceite de oliva"],                      "grasa",         10.0),
    ]),
    Recipe("Revuelto de bacalao con patatas", "cena", [
        _ing(["huevo"],                                "proteina",     120.0),
        _ing(["bacalao"],                              "proteina",      80.0),
        _ing(["patata"],                               "verdura",      150.0),
        _ing(["aceite de oliva"],                      "grasa",         15.0),
    ]),

    # ── DESAYUNOS CON PROTEÍNA ────────────────────────────────────────
    Recipe("Tortilla de claras con espinacas", "desayuno", [
        _ing(["clara", "huevo"],                       "proteina",     200.0),
        _ing(["espinaca"],                             "verdura",       80.0),
        _ing(["pan de molde", "pan"],                  "carbohidrato",  60.0),
        _ing(["aceite de oliva"],                      "grasa",         10.0),
    ]),
    Recipe("Batido proteico de yogur y avena", "desayuno", [
        _ing(["yogur griego natural", "yogur griego"], "lacteo",       200.0),
        _ing(["copos de avena", "avena"],              "carbohidrato",  50.0),
        _ing(["frutos rojos", "fruta"],                "fruta",         80.0),
    ]),
    Recipe("Tostadas con sardinas", "desayuno", [
        _ing(["sardina"],                              "proteina",     100.0),
        _ing(["pan de molde", "pan"],                  "carbohidrato",  80.0),
        _ing(["tomate"],                               "verdura",       60.0),
        _ing(["aceite de oliva"],                      "grasa",         10.0),
    ]),
    Recipe("Huevos cocidos con tostadas", "desayuno", [
        _ing(["huevo"],                                "proteina",     150.0),
        _ing(["pan de molde", "pan"],                  "carbohidrato",  80.0),
        _ing(["tomate"],                               "verdura",       60.0),
    ]),
    Recipe("Bocadillo de atún con tomate", "desayuno", [
        _ing(["atún", "atún claro al natural"],        "proteina",     100.0),
        _ing(["pan de molde", "pan"],                  "carbohidrato", 100.0),
        _ing(["tomate"],                               "verdura",       60.0),
    ]),
    Recipe("Tostadas con queso fresco y fruta", "desayuno", [
        _ing(["queso fresco", "queso"],                "lacteo",       100.0),
        _ing(["pan de molde", "pan"],                  "carbohidrato",  80.0),
        _ing(["fruta"],                                "fruta",         80.0),
    ]),
    Recipe("Revuelto de huevo con jamón", "desayuno", [
        _ing(["huevo"],                                "proteina",     150.0),
        _ing(["jamón cocido", "jamón serrano"],        "proteina",      60.0),
        _ing(["pan de molde", "pan"],                  "carbohidrato",  60.0),
        _ing(["aceite de oliva"],                      "grasa",         10.0),
    ]),
    Recipe("Bocadillo de pavo y queso", "desayuno", [
        _ing(["pavo lonchas", "jamón cocido"],         "proteina",      80.0),
        _ing(["pan de molde", "pan"],                  "carbohidrato", 100.0),
        _ing(["queso fresco", "queso"],                "lacteo",        40.0),
    ]),
    Recipe("Tostadas con caballa", "desayuno", [
        _ing(["caballa", "sardina"],                   "proteina",     100.0),
        _ing(["pan de molde", "pan"],                  "carbohidrato",  80.0),
        _ing(["tomate"],                               "verdura",       60.0),
        _ing(["aceite de oliva"],                      "grasa",         10.0),
    ]),
    Recipe("Porridge proteico con claras", "desayuno", [
        _ing(["clara", "huevo"],                       "proteina",     120.0),
        _ing(["copos de avena", "avena"],              "carbohidrato",  60.0),
        _ing(["leche semidesnatada", "leche"],         "lacteo",       150.0),
    ]),
    Recipe("Tostadas con bonito y tomate", "desayuno", [
        _ing(["atún", "atún claro al natural"],        "proteina",     100.0),
        _ing(["pan de molde", "pan"],                  "carbohidrato",  80.0),
        _ing(["tomate"],                               "verdura",       60.0),
        _ing(["aceite de oliva"],                      "grasa",         10.0),
    ]),

    # ── DESAYUNOS VARIADOS ────────────────────────────────────────────
    Recipe("Bol de kéfir con granola", "desayuno", [
        _ing(["kéfir", "yogur"],                       "lacteo",       200.0),
        _ing(["granola", "copos de avena"],            "carbohidrato",  50.0),
        _ing(["fruta"],                                "fruta",         80.0),
    ]),
    Recipe("Tostadas con crema de frutos secos", "desayuno", [
        _ing(["pan de molde", "pan"],                  "carbohidrato",  80.0),
        _ing(["nuez", "almendra"],                     "grasa",         40.0),
        _ing(["fruta"],                                "fruta",         80.0),
    ]),
    Recipe("Yogur con muesli y plátano", "desayuno", [
        _ing(["yogur natural", "yogur"],               "lacteo",       200.0),
        _ing(["muesli", "copos de avena"],             "carbohidrato",  60.0),
        _ing(["plátano", "fruta"],                     "fruta",         80.0),
    ]),
    Recipe("Leche con pan integral y aceite", "desayuno", [
        _ing(["leche semidesnatada", "leche"],         "lacteo",       250.0),
        _ing(["pan de molde", "pan"],                  "carbohidrato",  80.0),
        _ing(["aceite de oliva"],                      "grasa",         10.0),
    ]),
    Recipe("Batido de leche con plátano", "desayuno", [
        _ing(["leche semidesnatada", "leche"],         "lacteo",       250.0),
        _ing(["plátano", "fruta"],                     "fruta",        120.0),
        _ing(["copos de avena", "avena"],              "carbohidrato",  30.0),
    ]),
    Recipe("Yogur con semillas y fruta", "desayuno", [
        _ing(["yogur griego natural", "yogur"],        "lacteo",       200.0),
        _ing(["nuez", "almendra"],                     "grasa",         25.0),
        _ing(["fruta"],                                "fruta",        100.0),
    ]),
]

# Índices por tipo de comida para acceso rápido
RECIPES_BY_MEAL: dict[str, list[Recipe]] = {
    "desayuno": [r for r in RECIPES if r.meal_type == "desayuno"],
    "comida":   [r for r in RECIPES if r.meal_type == "comida"],
    "cena":     [r for r in RECIPES if r.meal_type == "cena"],
}

# Lookup name → Recipe para acceso O(1)
RECIPES_BY_NAME: dict[str, Recipe] = {r.name: r for r in RECIPES}


# ─────────────────────────────────────────────
# INSTRUCCIONES Y TIEMPOS DE PREPARACIÓN
# ─────────────────────────────────────────────
# Mapa nombre_receta → (instrucciones, prep_time_min)
# Solo se cubren las recetas más habituales; el resto usa defaults ([], 15).

_RECIPE_METADATA: dict[str, tuple[list[str], int]] = {
    # ── DESAYUNOS ─────────────────────────────────────────────────────────
    "Avena con leche": ([
        "Vierte la leche en un cazo o microondas y caliéntala 1-2 min.",
        "Añade los copos de avena y mezcla bien.",
        "Deja reposar 2 min para que la avena se hidrate.",
        "Endulza al gusto y sirve.",
    ], 5),
    "Avena con fruta": ([
        "Vierte la leche fría sobre los copos de avena en un bol.",
        "Deja reposar 2 min hasta que absorba.",
        "Lava y trocea la fruta.",
        "Incorpora la fruta sobre la avena y sirve.",
    ], 5),
    "Yogur con avena": ([
        "Vierte el yogur en un bol.",
        "Añade los copos de avena encima.",
        "Mezcla ligeramente y sirve.",
    ], 3),
    "Porridge de avena con leche": ([
        "Mezcla la avena con la leche en un cazo a fuego medio.",
        "Remueve constantemente durante 3-4 min hasta que espese.",
        "Retira del fuego, deja reposar 1 min y sirve.",
    ], 8),
    "Tostadas con aceite": ([
        "Tuesta el pan en tostadora o plancha hasta que dore.",
        "Rocía aceite de oliva por encima.",
        "Añade sal al gusto y sirve.",
    ], 5),
    "Tostadas con tomate": ([
        "Tuesta el pan hasta que quede crujiente.",
        "Parte el tomate y frótalo sobre el pan, o usa tomate triturado.",
        "Rocía aceite de oliva y añade una pizca de sal.",
    ], 5),
    "Sandwich desayuno": ([
        "Corta el pan de molde o la barra por la mitad.",
        "Coloca las lonchas de jamón cocido.",
        "Cierra el sandwich y sirve.",
    ], 3),
    "Tostadas con jamón cocido": ([
        "Tuesta el pan hasta que dore.",
        "Coloca las lonchas de jamón cocido sobre el pan.",
        "Sirve inmediatamente.",
    ], 5),
    "Tostadas con pavo": ([
        "Tuesta el pan de molde.",
        "Coloca las lonchas de pavo.",
        "Opcionalmente añade unas gotas de aceite de oliva.",
    ], 5),

    # ── COMIDAS ───────────────────────────────────────────────────────────
    "Pollo con arroz y verduras": ([
        "Corta la pechuga en trozos medianos y salpimienta.",
        "Calienta el aceite en una sartén a fuego medio-alto.",
        "Saltea el pollo 5-6 min hasta dorar. Reserva.",
        "En la misma sartén sofríe el tomate 3 min.",
        "Añade el arroz y el doble de agua. Tapa y cuece 12 min a fuego bajo.",
        "Incorpora las espinacas y el pollo reservado. Mezcla 2 min.",
        "Ajusta de sal y sirve.",
    ], 25),
    "Pollo con pasta y verduras": ([
        "Cuece la pasta en agua con sal según las instrucciones del envase.",
        "Mientras, calienta el aceite y saltea la pechuga troceada 5-6 min.",
        "Añade las espinacas y saltea 2 min hasta que marchiten.",
        "Escurre la pasta y mézclala con el pollo y las verduras.",
        "Ajusta de sal y sirve.",
    ], 20),
    "Arroz con atún y verduras": ([
        "Cuece el arroz en agua con sal durante 12-15 min. Escurre.",
        "En un bol, mezcla el atún escurrido con el tomate troceado.",
        "Añade las espinacas crudas o salteadas.",
        "Mezcla todo con el arroz, aliña con aceite y sirve.",
    ], 20),
    "Pasta con atún y tomate": ([
        "Cuece la pasta según el paquete. Escurre y reserva.",
        "En un bol mezcla el atún escurrido con el tomate troceado.",
        "Añade aceite, sal y pimienta al gusto.",
        "Mezcla con la pasta y sirve frío o templado.",
    ], 15),
    "Lentejas completas": ([
        "Si usas lentejas en conserva, escúrrelas y enjuágalas.",
        "Calienta el aceite en una cazuela a fuego medio.",
        "Sofríe el tomate 3-4 min.",
        "Añade las lentejas y las espinacas. Mezcla bien.",
        "Cuece 5 min a fuego suave. Ajusta de sal y sirve.",
    ], 15),
    "Garbanzos con verduras": ([
        "Si usas garbanzos en conserva, escúrrelos y enjuágalos.",
        "Calienta el aceite y sofríe el tomate 3 min.",
        "Incorpora los garbanzos y las espinacas.",
        "Rehoga todo 5 min a fuego medio. Ajusta de sal y sirve.",
    ], 15),
    "Lentejas con arroz": ([
        "Cuece el arroz en agua con sal 12 min. Escurre.",
        "En una sartén, calienta aceite y sofríe el tomate 3 min.",
        "Añade las lentejas escurridas y mezcla 3 min.",
        "Sirve las lentejas sobre el arroz.",
    ], 20),
    "Gambas con arroz": ([
        "Cuece el arroz en agua con sal durante 12 min. Escurre.",
        "Calienta el aceite en una sartén a fuego alto.",
        "Saltea las gambas 2-3 min hasta que cambien de color.",
        "Añade el tomate y rehoga 2 min.",
        "Sirve las gambas sobre el arroz.",
    ], 20),
    "Gambón con arroz basmati": ([
        "Lava y cuece el arroz basmati en agua con sal 10-12 min. Escurre.",
        "Calienta el aceite y saltea los gambones a fuego alto 2-3 min por lado.",
        "Añade los guisantes y rehoga 2 min.",
        "Sirve los gambones sobre el arroz con los guisantes.",
    ], 20),
    "Gambón con pasta y verduras": ([
        "Cuece la pasta en agua con sal. Escurre.",
        "Saltea los gambones en aceite a fuego alto 2-3 min por lado.",
        "Añade las espinacas y rehoga 2 min.",
        "Mezcla con la pasta, ajusta de sal y sirve.",
    ], 20),
    "Merluza con arroz y verduras": ([
        "Cuece el arroz en agua con sal 12-15 min. Escurre.",
        "Calienta el aceite en una sartén y cocina la merluza 3-4 min por lado.",
        "En la misma sartén saltea las espinacas o brócoli 3 min.",
        "Sirve la merluza sobre el arroz con las verduras.",
    ], 25),
    "Merluza con pasta": ([
        "Cuece la pasta en agua con sal. Escurre.",
        "Cocina la merluza en aceite 3-4 min por lado. Desmiga.",
        "Sofríe el tomate 3 min. Incorpora la merluza desmigada.",
        "Mezcla con la pasta, ajusta de sal y sirve.",
    ], 20),
    "Pollo con brócoli y arroz": ([
        "Cuece el arroz en agua con sal 12 min. Escurre.",
        "Cuece el brócoli al vapor o en agua 5 min. Escurre.",
        "Calienta el aceite y saltea la pechuga troceada 5-6 min.",
        "Incorpora el brócoli y saltea 2 min.",
        "Sirve sobre el arroz.",
    ], 25),
    "Pollo con pimientos y arroz": ([
        "Cuece el arroz en agua con sal 12 min. Escurre.",
        "Calienta el aceite y saltea la pechuga 5-6 min hasta dorar.",
        "Añade el pimiento en tiras y saltea 4 min.",
        "Sirve el pollo con pimientos sobre el arroz.",
    ], 25),
    "Arroz con carne picada": ([
        "Calienta el aceite en una sartén. Sofríe el tomate 3 min.",
        "Añade la carne picada y cocina 6-8 min removiendo hasta que pierda el color rosado.",
        "Incorpora el arroz y el doble de agua. Tapa y cuece 12 min a fuego bajo.",
        "Remueve al final y ajusta de sal.",
    ], 25),
    "Pasta con carne picada": ([
        "Cuece la pasta en agua con sal. Escurre y reserva.",
        "Calienta el aceite y sofríe el tomate 3 min.",
        "Añade la carne picada y cocina 6-8 min.",
        "Mezcla la pasta con la salsa. Ajusta de sal y sirve.",
    ], 20),
    "Pechuga doble con arroz": ([
        "Cuece el arroz en agua con sal 12-15 min. Escurre.",
        "Salpimienta la pechuga y calienta el aceite a fuego medio-alto.",
        "Cocina la pechuga 5-6 min por lado hasta que esté hecha.",
        "Deja reposar 2 min, corta en filetes y sirve con el arroz.",
    ], 25),
    "Pechuga doble con pasta": ([
        "Cuece la pasta en agua con sal. Escurre.",
        "Salpimienta y cocina la pechuga en aceite 5-6 min por lado.",
        "Saltea las espinacas en la misma sartén 2 min.",
        "Sirve la pechuga fileteada sobre la pasta con espinacas.",
    ], 20),
    "Salmón con edamame y arroz": ([
        "Cuece el arroz en agua con sal 12-15 min. Escurre.",
        "Descongela el edamame según el envase.",
        "Cocina el salmón en aceite 3-4 min por lado.",
        "Sirve el salmón sobre el arroz con el edamame.",
    ], 22),
    "Bacalao con arroz y espinacas": ([
        "Cuece el arroz en agua con sal 12-15 min. Escurre.",
        "Saltea el bacalao en aceite 3-4 min por lado.",
        "Añade las espinacas y rehoga 2 min.",
        "Sirve el bacalao sobre el arroz con espinacas.",
    ], 22),

    # ── CENAS ─────────────────────────────────────────────────────────────
    "Pechuga con espinacas": ([
        "Calienta el aceite en una sartén a fuego medio.",
        "Salpimienta la pechuga y cocínala 5-6 min por lado.",
        "En la misma sartén, saltea las espinacas 2-3 min.",
        "Sirve la pechuga con las espinacas al lado.",
    ], 15),
    "Pechuga con verduras doble": ([
        "Calienta el aceite en una sartén a fuego medio.",
        "Salpimienta la pechuga y cocínala 5-6 min por lado.",
        "Saltea las espinacas en la misma sartén 2-3 min.",
        "Sirve la pechuga fileteada con las verduras.",
    ], 15),
    "Ensalada con atún": ([
        "Lava y trocea las espinacas y el tomate.",
        "Escurre el atún de la lata.",
        "Mezcla todos los ingredientes en un bol.",
        "Aliña con aceite de oliva, sal y vinagre al gusto.",
    ], 10),
    "Pollo con verduras": ([
        "Calienta el aceite en una sartén a fuego medio-alto.",
        "Trocea la pechuga y salpimienta.",
        "Saltea el pollo 5-6 min hasta dorar.",
        "Añade las espinacas y el tomate. Rehoga 3 min.",
        "Ajusta de sal y sirve.",
    ], 15),
    "Atún con verduras": ([
        "Lava y trocea las espinacas y el tomate.",
        "Calienta el aceite en una sartén y saltea las verduras 3-4 min.",
        "Añade el atún escurrido y mezcla 1 min.",
        "Sirve templado o frío.",
    ], 10),
    "Atún con pimientos": ([
        "Saltea los pimientos en aceite 5-6 min a fuego medio.",
        "Añade el atún escurrido y rehoga 1 min.",
        "Ajusta de sal y sirve.",
    ], 12),
    "Gambas con verduras": ([
        "Calienta el aceite en una sartén a fuego alto.",
        "Saltea los pimientos 3-4 min.",
        "Añade las gambas y cocina 2-3 min hasta que se vuelvan rosadas.",
        "Ajusta de sal y sirve.",
    ], 15),
    "Merluza con verduras": ([
        "Calienta el aceite en una sartén a fuego medio.",
        "Cocina la merluza 3-4 min por lado.",
        "Saltea las espinacas o brócoli en la misma sartén 3 min.",
        "Ajusta de sal y sirve.",
    ], 15),
    "Merluza con brócoli": ([
        "Cuece el brócoli al vapor 5 min. Escurre.",
        "Calienta el aceite y cocina la merluza 3-4 min por lado.",
        "Sirve la merluza con el brócoli al lado.",
    ], 15),
    "Lomo con espinacas": ([
        "Calienta el aceite en una sartén a fuego medio.",
        "Dora el lomo 3-4 min por lado.",
        "En la misma sartén, saltea las espinacas 2-3 min.",
        "Sirve el lomo con las espinacas.",
    ], 15),
    "Lomo con verduras": ([
        "Calienta el aceite a fuego medio.",
        "Dora el lomo 3-4 min por lado. Reserva.",
        "Saltea las espinacas y el tomate 3 min en la misma sartén.",
        "Sirve el lomo con las verduras.",
    ], 15),
    "Claras con verduras": ([
        "Bate ligeramente las claras con una pizca de sal.",
        "Calienta el aceite en sartén antiadherente a fuego medio.",
        "Saltea las espinacas 2 min. Añade las claras y revuelve suavemente.",
        "Cuece hasta que las claras estén hechas. Sirve.",
    ], 10),
    "Revuelto de espinacas": ([
        "Bate ligeramente las claras con sal.",
        "Calienta el aceite y saltea las espinacas 2 min.",
        "Vierte las claras y remueve a fuego medio hasta que cuajen.",
        "Sirve inmediatamente.",
    ], 10),
    "Pechuga con espinacas": ([
        "Calienta el aceite en una sartén a fuego medio.",
        "Salpimienta la pechuga y cocínala 5-6 min por lado.",
        "Saltea las espinacas y el tomate 2-3 min.",
        "Sirve la pechuga fileteada con las verduras.",
    ], 15),
    "Sardinas con tomate": ([
        "Abre las latas de sardinas y escurre el aceite.",
        "Trocea el tomate o usa triturado y calienta 3 min con el aceite.",
        "Añade las sardinas y mezcla suavemente 1-2 min.",
        "Sirve solo o con pan.",
    ], 10),
    "Carne picada con tomate": ([
        "Calienta el aceite y sofríe el tomate triturado 3 min.",
        "Añade la carne picada y cocina 6-8 min removiendo.",
        "Ajusta de sal y pimienta. Sirve.",
    ], 15),
    "Garbanzos con espinacas": ([
        "Escurre y enjuaga los garbanzos.",
        "Calienta el aceite y saltea las espinacas 2 min.",
        "Añade los garbanzos y rehoga 3-4 min.",
        "Ajusta de sal y sirve.",
    ], 12),
    "Pava con verduras": ([
        "Calienta el aceite en sartén a fuego medio.",
        "Saltea el pavo 3-4 min.",
        "Añade las espinacas y el tomate. Rehoga 3 min.",
        "Ajusta de sal y sirve.",
    ], 12),
}

# Aplica metadata a los Recipe objects del catálogo
# Para las que no tienen entrada en _RECIPE_METADATA se generan instrucciones automáticas.
from app.engine.recipe_namer import generate_instructions as _gen_instructions_static

for _r in RECIPES:
    _meta = _RECIPE_METADATA.get(_r.name)
    if _meta:
        _r.instructions, _r.prep_time_min = _meta
    else:
        _ing_info = [(_i.preferred_keywords[0], _i.category) for _i in _r.ingredients]
        _r.instructions, _r.prep_time_min = _gen_instructions_static(_ing_info, _r.meal_type)


# ─────────────────────────────────────────────
# RESOLUCIÓN Y VERIFICACIÓN CONTRA BD REAL
# ─────────────────────────────────────────────

def resolve_ingredient(ing: RecipeIngredient, db, supermarket: str = "todos") -> "tuple[str, object | None]":
    """
    Resuelve un ingrediente contra la BD.

    Prueba cada keyword de preferred_keywords en orden hasta encontrar
    un producto que cumpla categoría y no contenga ningún exclude_keyword.

    Devuelve (keyword_usada, ProductORM | None).
    """
    from app.models.diet import ProductORM
    from sqlalchemy import func

    for kw in ing.preferred_keywords:
        q = (
            db.query(ProductORM)
            .filter(
                func.lower(ProductORM.name).contains(kw.lower()),
                ProductORM.category == ing.category,
            )
        )
        if supermarket != "todos":
            if supermarket.startswith("multi:"):
                sms = supermarket[6:].split(",")
            else:
                sms = [supermarket]
            q = q.filter(ProductORM.supermarket.in_(sms))
        for excl in ing.exclude_keywords:
            q = q.filter(~func.lower(ProductORM.name).contains(excl.lower()))
        prod = q.order_by(ProductORM.price_per_100g.asc()).first()
        if prod is not None:
            return kw, prod

    return ing.preferred_keywords[0], None


def resolve_recipe(recipe: Recipe, db, supermarket: str = "todos") -> "list[tuple[RecipeIngredient, str, object | None]]":
    """
    Resuelve todos los ingredientes de una receta.
    Devuelve lista de (ingrediente, keyword_usada, ProductORM | None).
    """
    return [
        (ing, kw_used, prod)
        for ing in recipe.ingredients
        for kw_used, prod in [resolve_ingredient(ing, db, supermarket)]
    ]


def resolve_and_verify(db) -> None:
    """
    Valida el catálogo de recetas contra los productos reales en la BD.
    Imprime una tabla completa y un resumen por tipo de comida.
    """
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    W = 74
    print(f"\n{'═'*W}")
    print(f"  VERIFICACIÓN DE RECETAS CONTRA BD REAL")
    print(f"{'═'*W}")

    stats: dict[str, dict[str, int]] = {
        "desayuno": {"ok": 0, "ko": 0},
        "comida":   {"ok": 0, "ko": 0},
        "cena":     {"ok": 0, "ko": 0},
    }

    for meal_type in ("desayuno", "comida", "cena"):
        recipes = RECIPES_BY_MEAL[meal_type]
        label = meal_type.upper()
        print(f"\n  ── {label} {'─'*(W-6-len(label))}")

        for recipe in recipes:
            resolved = resolve_recipe(recipe, db)
            missing = [(ing, kw) for ing, kw, prod in resolved if prod is None]
            available = len(missing) == 0

            status = "✓" if available else "✗"
            print(f"\n  {status} {recipe.name}")

            total_kcal = 0.0
            total_cost = 0.0
            for ing, kw_used, prod in resolved:
                if prod is not None:
                    kcal = prod.kcal_per_100g / 100 * ing.base_grams
                    cost = prod.price_per_100g / 100 * ing.base_grams
                    total_kcal += kcal
                    total_cost += cost
                    # Mostrar keyword usada y si fue fallback
                    kw_label = kw_used
                    if kw_used != ing.preferred_keywords[0]:
                        kw_label = f"{kw_used} (↓fallback)"
                    print(
                        f"      [{kw_label:<20}] {prod.name[:36]:<36}"
                        f"  {ing.base_grams:>5.0f}g"
                        f"  {kcal:>5.0f} kcal"
                        f"  {cost:>5.2f}€"
                    )
                else:
                    tried = " > ".join(ing.preferred_keywords)
                    print(
                        f"      [{ing.display_keyword:<20}] *** NO ENCONTRADO"
                        f" (cat={ing.category}, probado: {tried}) ***"
                    )

            if available:
                print(
                    f"      {'─'*62}\n"
                    f"      {'TOTAL':<58}"
                    f"  {total_kcal:>5.0f} kcal"
                    f"  {total_cost:>5.2f}€"
                )
                stats[meal_type]["ok"] += 1
            else:
                ko_display = ", ".join(ing.display_keyword for ing, _ in missing)
                print(f"      ↳ NO DISPONIBLE — faltan: {ko_display}")
                stats[meal_type]["ko"] += 1

    # ── Resumen manuales ──────────────────────────────────────────────────
    print(f"\n{'═'*W}")
    print(f"  RESUMEN — RECETAS MANUALES")
    print(f"{'═'*W}")
    total_ok = total_ko = 0
    for meal_type in ("desayuno", "comida", "cena"):
        ok = stats[meal_type]["ok"]
        ko = stats[meal_type]["ko"]
        total = ok + ko
        total_ok += ok
        total_ko += ko
        bar_ok = "█" * ok
        bar_ko = "░" * ko
        print(f"  {meal_type.capitalize():<10}  {bar_ok}{bar_ko}  {ok}/{total} disponibles")
    print(f"  {'─'*W}")
    print(f"  {'TOTAL':<10}  {total_ok}/{total_ok + total_ko} recetas manuales disponibles")
    print(f"{'═'*W}")

    # ── Resumen automáticas ───────────────────────────────────────────────
    print(f"\n{'═'*W}")
    print(f"  RESUMEN — RECETAS AUTOMÁTICAS (generate_auto_recipes)")
    print(f"{'═'*W}")
    auto_recipes = generate_auto_recipes(db)
    manual_names = {r.name for r in RECIPES}
    auto_unique = [r for r in auto_recipes if r.name not in manual_names]

    auto_stats: dict[str, int] = {"desayuno": 0, "comida": 0, "cena": 0}
    for r in auto_unique:
        if r.meal_type in auto_stats:
            auto_stats[r.meal_type] += 1

    for meal_type in ("desayuno", "comida", "cena"):
        n = auto_stats[meal_type]
        bar = "█" * min(n, 50)
        print(f"  {meal_type.capitalize():<10}  {bar}  {n} recetas automáticas")

    grand_manual = total_ok
    grand_auto   = len(auto_unique)
    grand_total  = grand_manual + grand_auto
    print(f"  {'─'*W}")
    print(f"  {'Manuales':<14} {grand_manual}")
    print(f"  {'Automáticas':<14} {grand_auto}")
    print(f"  {'TOTAL GLOBAL':<14} {grand_total} recetas disponibles")
    print(f"{'═'*W}\n")


# ─────────────────────────────────────────────
# GENERACIÓN AUTOMÁTICA DE RECETAS DESDE LA BD
# ─────────────────────────────────────────────

def generate_auto_recipes(db) -> list[Recipe]:
    """
    Genera recetas automáticas combinando todos los productos válidos de la BD.

    Estrategia de cobertura:
    - Itera TODOS los productos de cada categoría (sin límite top-N).
    - Usa rotación modular para emparejar proteínas con distintos carbohidratos
      y verduras, garantizando que cada producto aparezca en al menos una receta.
    - Añade patrones explícitos para productos poco usados (surimi, almejas,
      pota, boquerones, chipirones, magro, lacón; edamame, habas, espárragos,
      alcachofas, champiñones; cous cous, quinoa, arroz integral, tortillas, etc.).

    Selección final diversa:
    - Agrupa candidatos por proteína/lácteo principal.
    - Toma en round-robin 1 receta por proteína hasta llenar el cupo,
      luego una segunda ronda, etc. → máx 5 recetas/proteína en comida,
      3 en cena, 4 por lácteo en desayuno.
    - Cupo total: 100 comidas + 100 cenas + 100 desayunos = 300 auto-recetas.

    Se descartan recetas con coste base > 5 € y duplicados con RECIPES.
    """
    from app.models.diet import ProductORM
    from sqlalchemy import func

    MAX_COST_BASE        = 5.0
    MAX_PER_TYPE         = 100   # por tipo de comida
    MAX_PER_PROT_COMIDA  = 5     # máx recetas por proteína principal (comida)
    MAX_PER_PROT_CENA    = 3     # máx recetas por proteína principal (cena)
    MAX_PER_LAC_DESAYUNO = 4     # máx recetas por lácteo principal (desayuno)

    # ── helpers ───────────────────────────────────────────────────────────
    def _from_orm(prod: "ProductORM", grams: float) -> RecipeIngredient:
        return RecipeIngredient(
            preferred_keywords=[prod.name],
            category=prod.category,
            base_grams=grams,
        )

    def _all(category: str) -> "list[ProductORM]":
        """Todos los productos de una categoría, excluida la blacklist, por precio."""
        q = db.query(ProductORM).filter(ProductORM.category == category)
        for term in PRODUCT_BLACKLIST:
            q = q.filter(~func.lower(ProductORM.name).contains(term.lower()))
        return q.order_by(ProductORM.price_per_100g.asc()).all()

    def _kw(category: str, keyword: str) -> "list[ProductORM]":
        """Productos de una categoría cuyo nombre contiene keyword, por precio."""
        return (
            db.query(ProductORM)
            .filter(
                ProductORM.category == category,
                func.lower(ProductORM.name).contains(keyword.lower()),
            )
            .order_by(ProductORM.price_per_100g.asc())
            .all()
        )

    def _short(name: str) -> str:
        _STOP = {
            "hacendado", "brüggen", "bruggen",
            "sin", "lactosa", "calcio",
            "ultracongelado", "ultracongelada",
            "ultracongelados", "ultracongeladas",
        }
        short_words = []
        for w in name.split():
            if w.lower() in _STOP:
                break
            short_words.append(w)
            if len(short_words) == 3:
                break
        result = " ".join(short_words) if short_words else name.split()[0]
        return result[0].upper() + result[1:] if result else name

    def _cost(prods_grams: "list[tuple[ProductORM, float]]") -> float:
        return sum(p.price_per_100g / 100 * g for p, g in prods_grams)

    # ── aceite ────────────────────────────────────────────────────────────
    aceite = (
        db.query(ProductORM)
        .filter(
            ProductORM.category == "grasa",
            func.lower(ProductORM.name).contains("aceite de oliva"),
        )
        .order_by(ProductORM.price_per_100g.asc())
        .first()
    ) or (
        db.query(ProductORM)
        .filter(
            ProductORM.category == "grasa",
            func.lower(ProductORM.name).contains("aceite"),
        )
        .order_by(ProductORM.price_per_100g.asc())
        .first()
    )

    # ── todos los productos por categoría ─────────────────────────────────
    all_proteins  = _all("proteina")
    all_carbs     = _all("carbohidrato")
    all_verduras  = _all("verdura")
    all_legumbres = _all("legumbre")
    all_lacteos   = _all("lacteo")
    all_frutas    = _all("fruta")

    n_prot = len(all_proteins)
    n_carb = len(all_carbs)
    n_verd = len(all_verduras)
    n_leg  = len(all_legumbres)
    n_fru  = len(all_frutas)

    if n_prot == 0:
        return []

    # ── filtros desayuno ──────────────────────────────────────────────────
    _REAL_MILK_KWS = ("leche", "yogur", "kéfir", "bifidus", "bífidus")
    _PLANT_DRINK_KWS = (
        "bebida de soja", "bebida de avena", "bebida de arroz",
        "bebida de almendra", "bebida de avellana", "batido",
    )
    _BREAKFAST_CARB_KWS = ("avena", "cereal", "galleta", "muesli")
    _NONBREAKFAST_CARB_KWS = (
        "pan rallado", "pasta", "macarrón", "spaghetti", "hélice",
        "penne", "tallarín", "fideo", "fideos", "noodle",
    )
    # Carbos que no son aptos para comida/cena (solo desayuno)
    _BREAKFAST_ONLY_CARB = ("galleta", "muesli", "cereal", "avena")

    def _is_real_lacteo(p: "ProductORM") -> bool:
        name_l = p.name.lower()
        if any(bad in name_l for bad in _PLANT_DRINK_KWS):
            return False
        return any(kw in name_l for kw in _REAL_MILK_KWS)

    def _is_breakfast_carb(p: "ProductORM") -> bool:
        name_l = p.name.lower()
        if any(bad in name_l for bad in _NONBREAKFAST_CARB_KWS):
            return False
        return any(kw in name_l for kw in _BREAKFAST_CARB_KWS)

    def _is_meal_carb(p: "ProductORM") -> bool:
        """Apto para comida/cena (excluye galletas, cereales, avena, muesli)."""
        name_l = p.name.lower()
        return not any(kw in name_l for kw in _BREAKFAST_ONLY_CARB)

    meal_carbs = [c for c in all_carbs if _is_meal_carb(c)]
    n_mc = len(meal_carbs) or 1  # evitar división por cero

    break_carbs: list["ProductORM"] = []
    seen_ids: set[int] = set()
    for kw in ("avena", "galleta", "cereal", "pan"):
        for p in _kw("carbohidrato", kw):
            if p.id not in seen_ids and _is_breakfast_carb(p):
                break_carbs.append(p)
                seen_ids.add(p.id)
    n_bk = len(break_carbs) or 1

    proteic_lacteos: list["ProductORM"] = []
    seen_plac: set[int] = set()
    for kw in ("griego", "skyr", "queso fresco batido", "quark"):
        for p in _kw("lacteo", kw):
            if p.id not in seen_plac:
                proteic_lacteos.append(p)
                seen_plac.add(p.id)

    real_lacteos = [l for l in all_lacteos if _is_real_lacteo(l)]
    n_rl = len(real_lacteos) or 1

    # ── colectores ────────────────────────────────────────────────────────
    from app.engine.recipe_namer import generate_instructions as _gen_instructions

    existing_names: set[str] = {r.name for r in RECIPES}
    buckets: dict[str, list[tuple[float, Recipe]]] = {
        "comida": [], "cena": [], "desayuno": []
    }

    def _add(recipe: Recipe, cost: float) -> None:
        if recipe.name not in existing_names and cost <= MAX_COST_BASE:
            existing_names.add(recipe.name)
            ing_info = [(i.preferred_keywords[0], i.category) for i in recipe.ingredients]
            steps, prep = _gen_instructions(ing_info, recipe.meal_type)
            recipe.instructions = steps
            recipe.prep_time_min = prep
            buckets[recipe.meal_type].append((cost, recipe))

    # ═══════════════════════════════════════════════════════════════════════
    # COMIDAS
    # ═══════════════════════════════════════════════════════════════════════

    # Patrón 1: proteina × carb × verdura + aceite  (rotación para cubrir todo)
    # Stride primo para maximizar variedad en la rotación modular
    for i, prot in enumerate(all_proteins):
        for j in range(min(3, n_mc)):
            carb = meal_carbs[(i + j * 37) % n_mc]
            verd = all_verduras[(i + j * 41) % n_verd] if n_verd else None
            name = (
                f"{_short(prot.name)} con {_short(carb.name).lower()}"
                + (f" y {_short(verd.name).lower()}" if verd else "")
            )
            pairs = [(prot, 160.0), (carb, 120.0)]
            if verd:
                pairs.append((verd, 80.0))
            if aceite:
                pairs.append((aceite, 10.0))
            _add(Recipe(name, "comida", [_from_orm(p, g) for p, g in pairs]), _cost(pairs))

    # Cobertura de carbohidratos: cada carb aparece al menos en 1 comida
    for i, carb in enumerate(meal_carbs):
        prot = all_proteins[i % n_prot]
        name = f"{_short(prot.name)} con {_short(carb.name).lower()}"
        pairs = [(prot, 160.0), (carb, 150.0)]
        if aceite:
            pairs.append((aceite, 10.0))
        _add(Recipe(name, "comida", [_from_orm(p, g) for p, g in pairs]), _cost(pairs))

    # Patrón 2: proteina × legumbre + aceite  (mediterráneo)
    for prot in all_proteins:
        for leg in all_legumbres:
            name = f"{_short(prot.name)} con {_short(leg.name).lower()}"
            pairs = [(prot, 150.0), (leg, 100.0)]
            if aceite:
                pairs.append((aceite, 10.0))
            _add(Recipe(name, "comida", [_from_orm(p, g) for p, g in pairs]), _cost(pairs))

    # Patrón explícito — carbohidratos poco usados
    _UNDERUSED_CARB_KWS = (
        "cous", "quinoa", "fideuá", "integral", "basmati",
        "tortilla de trigo", "bulgur", "espelta",
    )
    for kw in _UNDERUSED_CARB_KWS:
        for carb in _kw("carbohidrato", kw):
            for j, prot in enumerate(all_proteins[:8]):
                verd = all_verduras[j % n_verd] if n_verd else None
                name = (
                    f"{_short(prot.name)} con {_short(carb.name).lower()}"
                    + (f" y {_short(verd.name).lower()}" if verd else "")
                )
                pairs = [(prot, 160.0), (carb, 120.0)]
                if verd:
                    pairs.append((verd, 80.0))
                if aceite:
                    pairs.append((aceite, 10.0))
                _add(Recipe(name, "comida", [_from_orm(p, g) for p, g in pairs]), _cost(pairs))

    # Patrón explícito — proteínas poco usadas en comida
    _UNDERUSED_PROT_KWS = (
        "surimi", "almeja", "pota", "boquerón", "boquerones",
        "chipirón", "chipirones", "magro", "lacón",
        "berberecho", "berberechos", "navajas", "zamburiñas",
        "salmonete", "rape", "sepia", "bacaladilla",
    )
    for kw in _UNDERUSED_PROT_KWS:
        for prot in _kw("proteina", kw):
            # 3 comidas con carbs distintos
            for j in range(min(3, n_mc)):
                carb = meal_carbs[j % n_mc]
                verd = all_verduras[j % n_verd] if n_verd else None
                name = (
                    f"{_short(prot.name)} con {_short(carb.name).lower()}"
                    + (f" y {_short(verd.name).lower()}" if verd else "")
                )
                pairs = [(prot, 160.0), (carb, 120.0)]
                if verd:
                    pairs.append((verd, 80.0))
                if aceite:
                    pairs.append((aceite, 10.0))
                _add(Recipe(name, "comida", [_from_orm(p, g) for p, g in pairs]), _cost(pairs))
            # 2 comidas con legumbre
            for leg in all_legumbres[:2]:
                name = f"{_short(prot.name)} con {_short(leg.name).lower()}"
                pairs = [(prot, 150.0), (leg, 100.0)]
                if aceite:
                    pairs.append((aceite, 10.0))
                _add(Recipe(name, "comida", [_from_orm(p, g) for p, g in pairs]), _cost(pairs))

    # ═══════════════════════════════════════════════════════════════════════
    # CENAS
    # ═══════════════════════════════════════════════════════════════════════

    # Patrón 1: proteina × verdura + aceite  (rotación para cubrir todas)
    for i, prot in enumerate(all_proteins):
        for j in range(min(3, n_verd)):
            verd = all_verduras[(i + j * 43) % n_verd]
            name = f"{_short(prot.name)} con {_short(verd.name).lower()}"
            pairs = [(prot, 150.0), (verd, 150.0)]
            if aceite:
                pairs.append((aceite, 10.0))
            _add(Recipe(name, "cena", [_from_orm(p, g) for p, g in pairs]), _cost(pairs))

    # Cobertura de verduras: cada verdura aparece al menos en 1 cena
    for i, verd in enumerate(all_verduras):
        prot = all_proteins[i % n_prot]
        name = f"{_short(prot.name)} con {_short(verd.name).lower()}"
        pairs = [(prot, 150.0), (verd, 180.0)]
        if aceite:
            pairs.append((aceite, 10.0))
        _add(Recipe(name, "cena", [_from_orm(p, g) for p, g in pairs]), _cost(pairs))

    # Patrón 2: proteina × verdura1 × verdura2 + aceite  (top proteínas)
    for i, prot in enumerate(all_proteins[:40]):
        for j in range(min(4, n_verd - 1)):
            v1 = all_verduras[(i + j * 7) % n_verd]
            v2 = all_verduras[(i + j * 7 + 3) % n_verd]
            if v1.id == v2.id:
                continue
            name = f"{_short(prot.name)} con {_short(v1.name).lower()} y {_short(v2.name).lower()}"
            pairs = [(prot, 130.0), (v1, 100.0), (v2, 80.0)]
            if aceite:
                pairs.append((aceite, 10.0))
            _add(Recipe(name, "cena", [_from_orm(p, g) for p, g in pairs]), _cost(pairs))

    # Patrón 3: legumbre × verdura + aceite
    for leg in all_legumbres:
        for verd in all_verduras:
            name = f"{_short(leg.name)} con {_short(verd.name).lower()}"
            pairs = [(leg, 120.0), (verd, 120.0)]
            if aceite:
                pairs.append((aceite, 10.0))
            _add(Recipe(name, "cena", [_from_orm(p, g) for p, g in pairs]), _cost(pairs))

    # Patrón explícito — verduras poco usadas en cena
    _UNDERUSED_VERD_KWS = (
        "edamame", "habas", "col de bruselas", "acelga",
        "espárrago", "alcachofa", "champiñ", "setas",
        "puerro", "coliflor", "brócoli", "pimiento",
    )
    for kw in _UNDERUSED_VERD_KWS:
        for verd in _kw("verdura", kw):
            for j, prot in enumerate(all_proteins[:6]):
                name = f"{_short(prot.name)} con {_short(verd.name).lower()}"
                pairs = [(prot, 150.0), (verd, 150.0)]
                if aceite:
                    pairs.append((aceite, 10.0))
                _add(Recipe(name, "cena", [_from_orm(p, g) for p, g in pairs]), _cost(pairs))

    # Patrón explícito — proteínas poco usadas en cena
    for kw in _UNDERUSED_PROT_KWS:
        for prot in _kw("proteina", kw):
            for j in range(min(4, n_verd)):
                verd = all_verduras[j % n_verd]
                name = f"{_short(prot.name)} con {_short(verd.name).lower()}"
                pairs = [(prot, 150.0), (verd, 150.0)]
                if aceite:
                    pairs.append((aceite, 10.0))
                _add(Recipe(name, "cena", [_from_orm(p, g) for p, g in pairs]), _cost(pairs))

    # ═══════════════════════════════════════════════════════════════════════
    # DESAYUNOS
    # ═══════════════════════════════════════════════════════════════════════

    # Patrón 1: lacteo × carb  (todos los lácteos reales, rotando carbs)
    for i, lac in enumerate(real_lacteos):
        for j in range(min(3, n_bk)):
            carb = break_carbs[(i + j * 7) % n_bk]
            if not _is_breakfast_carb(carb):
                continue
            name = f"{_short(lac.name)} con {_short(carb.name).lower()}"
            pairs = [(lac, 200.0), (carb, 60.0)]
            _add(Recipe(name, "desayuno", [_from_orm(p, g) for p, g in pairs]), _cost(pairs))

    # Patrón 2: lacteo × fruta  (todos los lácteos reales, rotando frutas)
    for i, lac in enumerate(real_lacteos):
        for j in range(min(2, n_fru)):
            fruta = all_frutas[(i + j * 5) % n_fru]
            name = f"{_short(lac.name)} con {_short(fruta.name).lower()}"
            pairs = [(lac, 200.0), (fruta, 120.0)]
            _add(Recipe(name, "desayuno", [_from_orm(p, g) for p, g in pairs]), _cost(pairs))

    # Cobertura de lácteos: cada lácteo real aparece al menos en 1 desayuno
    for i, lac in enumerate(real_lacteos):
        if break_carbs:
            carb = break_carbs[i % n_bk]
            name = f"{_short(lac.name)} con {_short(carb.name).lower()}"
            pairs = [(lac, 200.0), (carb, 60.0)]
            _add(Recipe(name, "desayuno", [_from_orm(p, g) for p, g in pairs]), _cost(pairs))

    # Patrón 3: carb × fruta  (avena/muesli, sin lácteo)
    avenas = [p for p in break_carbs if "avena" in p.name.lower() or "muesli" in p.name.lower()]
    for carb in (avenas + [p for p in break_carbs[:4] if _is_breakfast_carb(p)]):
        for fruta in all_frutas:
            name = f"{_short(carb.name)} con {_short(fruta.name).lower()}"
            pairs = [(carb, 70.0), (fruta, 150.0)]
            _add(Recipe(name, "desayuno", [_from_orm(p, g) for p, g in pairs]), _cost(pairs))

    # Patrón 4: solo lácteo proteico  (yogur griego, skyr, etc.)
    for lac in proteic_lacteos:
        name = _short(lac.name)
        pairs = [(lac, 300.0)]
        _add(Recipe(name, "desayuno", [_from_orm(p, g) for p, g in pairs]), _cost(pairs))

    # ═══════════════════════════════════════════════════════════════════════
    # SELECCIÓN DIVERSA
    # ─────────────────────────────────────────────────────────────────────
    # Eje de diversidad primario (maximiza cobertura de productos):
    #   comida   → clave = 2º ingrediente (carb/legumbre)  → 1 receta/carb
    #   cena     → clave = grupo proteico principal        → 5 recetas/grupo
    #   desayuno → clave = 1er ingrediente (lácteo)        → 2 recetas/lácteo
    #
    # Restricción secundaria: proteína principal (1er ingrediente) no supera
    # MAX_PER_PROT_COMIDA / MAX_PER_PROT_CENA en cada tipo de comida,
    # evitando que un solo producto monopolice el menú.
    # ═══════════════════════════════════════════════════════════════════════

    def _grouped_prot(name: str) -> str:
        """Agrupa el nombre de un producto en su categoría proteica para cena."""
        n = name.lower()
        if any(k in n for k in ("alubia", "garbanzo", "lenteja", "judía", "judia", "legumbre")):
            return "legumbre"
        if any(k in n for k in ("pechuga", "pollo", "contramuslo", "muslo")):
            return "pollo"
        if any(k in n for k in ("cerdo", "lomo", "secreto", "costilla", "panceta")):
            return "cerdo"
        if any(k in n for k in ("ternera", "vacuno", "buey", "carne picada")):
            return "ternera"
        if any(k in n for k in ("merluza", "pescado", "bacalao", "dorada", "lubina", "rape")):
            return "merluza"
        if any(k in n for k in ("salmón", "salmon")):
            return "salmon"
        if any(k in n for k in ("atún", "atun", "bonito", "caballa")):
            return "atun"
        if any(k in n for k in ("gambas", "langostino", "mejillón", "mejillon", "calamar")):
            return "marisco"
        if any(k in n for k in ("huevo", "tortilla")):
            return "huevo"
        if any(k in n for k in ("tofu", "tempeh", "soja")):
            return "vegetal"
        return "otro"

    def _coverage_key(recipe: Recipe, meal_type: str) -> str:
        """Clave que determina qué producto cubre esta receta (eje de diversidad)."""
        ings = recipe.ingredients
        if not ings:
            return "?"
        if meal_type == "comida":
            # 2º ingrediente = carb o legumbre
            return ings[1].preferred_keywords[0] if len(ings) >= 2 else ings[0].preferred_keywords[0]
        elif meal_type == "cena":
            # Primer ingrediente = proteína principal → agrupar para diversidad real
            return _grouped_prot(ings[0].preferred_keywords[0])
        else:  # desayuno
            return ings[0].preferred_keywords[0]

    def _prot_key(recipe: Recipe) -> str:
        """Clave de proteína principal (1er ingrediente) para la restricción secundaria."""
        return recipe.ingredients[0].preferred_keywords[0] if recipe.ingredients else "?"

    _coverage_cap = {"comida": 1, "cena": 5, "desayuno": 2}
    _prot_cap     = {"comida": MAX_PER_PROT_COMIDA, "cena": MAX_PER_PROT_CENA, "desayuno": 999}

    auto: list[Recipe] = []
    for meal_type in ("comida", "cena", "desayuno"):
        max_per_cov  = _coverage_cap[meal_type]
        max_per_prot = _prot_cap[meal_type]

        # Agrupar por clave de cobertura, ordenados por coste ascendente
        by_cov: dict[str, list[tuple[float, Recipe]]] = {}
        for cost, recipe in sorted(buckets[meal_type], key=lambda x: x[0]):
            ck = _coverage_key(recipe, meal_type)
            by_cov.setdefault(ck, []).append((cost, recipe))

        prot_count: dict[str, int] = {}
        cov_round:  dict[str, int] = {ck: 0 for ck in by_cov}
        selected:   list[Recipe]   = []

        for _round in range(max_per_cov):
            if len(selected) >= MAX_PER_TYPE:
                break
            made_progress = False
            for ck, entries in by_cov.items():
                if len(selected) >= MAX_PER_TYPE:
                    break
                # Avanzar hasta encontrar una receta cuya proteína no esté saturada
                while cov_round[ck] < len(entries):
                    _, recipe = entries[cov_round[ck]]
                    pk = _prot_key(recipe)
                    cov_round[ck] += 1
                    if prot_count.get(pk, 0) < max_per_prot:
                        selected.append(recipe)
                        prot_count[pk] = prot_count.get(pk, 0) + 1
                        made_progress = True
                        break
                    # proteína saturada → probar siguiente candidato del mismo carb/verdura
            if not made_progress:
                break

        auto.extend(selected)

    return auto


# ─────────────────────────────────────────────
# PREPARACIÓN DE DATOS PARA EL MIP DE RECETAS
# ─────────────────────────────────────────────

# Fracción calórica objetivo por tipo de comida
_MEAL_KCAL_FRACTION: dict[str, float] = {
    "desayuno": 0.25,
    "comida":   0.40,
    "cena":     0.35,
}

# Escala mínima y máxima permitida para no generar porciones absurdas.
# Una receta que necesite >2.5× para llegar a las kcal objetivo se sirve a ×2.5.
_SCALE_MIN = 0.7
_SCALE_MAX = 2.5


@dataclass
class ResolvedRecipeData:
    """
    Receta completamente resuelta y escalada, lista para el MIP.
    Cada ingrediente ya tiene su gramos reales post-escala.
    """
    recipe: Recipe
    # Nombre del producto resuelto por ingrediente (mismo orden que recipe.ingredients)
    product_names: list[str]
    # Gramos escalados por ingrediente
    scaled_grams: list[float]
    # Macros y coste totales de la receta a escala aplicada
    scaled_kcal: float
    scaled_cost: float
    scaled_protein: float
    scaled_fat: float
    scaled_carbs: float
    # Factor de escala aplicado (informativo)
    scale_factor: float
    # Puntuación de calidad para el objetivo MIP (proteína cara/premium = mayor score)
    quality_score: float = 1.0
    # Nombre del producto proteico principal (para rastrear variedad semanal)
    main_protein: str = ""


def build_recipe_lp_data(
    db,
    kcal_target: float,
    preferences: dict | None = None,
) -> dict[str, list[ResolvedRecipeData]]:
    """
    Resuelve todas las recetas disponibles contra la BD y las escala al
    objetivo calórico de su tipo de comida.

    Para cada receta:
      1. Resuelve los ingredientes (preferred_keywords + exclusiones).
      2. Descarta la receta si algún ingrediente no tiene producto en la BD.
      3. Calcula las kcal base de la receta con los base_grams definidos.
      4. Calcula scale_factor = kcal_objetivo / kcal_base, acotado a [0.7, 2.5].
      5. Escala todos los gramos por scale_factor.
      6. Ajusta quality_score según valoraciones previas del usuario.

    Devuelve un dict {meal_type → [ResolvedRecipeData]} con solo las recetas
    disponibles y escaladas.
    """
    from app.models.diet import DietMealORM, DietPlanORM, ProductORM
    from sqlalchemy import select

    # ── Cargar valoraciones de recetas desde el historial ─────────────
    rated_positive: set[str] = set()
    rated_negative: set[str] = set()
    try:
        stmt = (
            select(DietMealORM.recipe_name, DietPlanORM.rating)
            .join(DietPlanORM, DietMealORM.plan_id == DietPlanORM.id)
            .filter(
                DietPlanORM.rating.isnot(None),
                DietMealORM.recipe_name.isnot(None),
            )
            .distinct()
        )
        for row in db.execute(stmt).all():
            if row.rating == 1:
                rated_positive.add(row.recipe_name)
            elif row.rating == -1:
                rated_negative.add(row.recipe_name)
    except Exception:
        pass  # tabla aún no migrada o error puntual — no bloquear

    result: dict[str, list[ResolvedRecipeData]] = {
        "desayuno": [],
        "comida":   [],
        "cena":     [],
    }

    _supermarket = (preferences or {}).get("supermarket", "todos")

    # Merge manual + auto recipes (auto deduplicated by name)
    manual_names = {r.name for r in RECIPES}
    auto_recipes = [r for r in generate_auto_recipes(db) if r.name not in manual_names]
    all_recipes = list(RECIPES) + auto_recipes

    for recipe in all_recipes:
        resolved = resolve_recipe(recipe, db, _supermarket)

        # Descartar si algún ingrediente no se pudo resolver
        if any(prod is None for _, _, prod in resolved):
            continue

        # Calcular kcal base con los gramos del catálogo
        base_kcal = sum(
            prod.kcal_per_100g / 100 * ing.base_grams
            for ing, _, prod in resolved
        )
        if base_kcal < 1.0:
            continue  # receta vacía/inválida

        # Escala objetivo
        kcal_target_meal = kcal_target * _MEAL_KCAL_FRACTION[recipe.meal_type]
        raw_scale = kcal_target_meal / base_kcal
        scale = max(_SCALE_MIN, min(_SCALE_MAX, raw_scale))

        # Construir la estructura escalada
        product_names: list[str] = []
        scaled_grams:  list[float] = []
        scaled_kcal    = 0.0
        scaled_cost    = 0.0
        scaled_protein = 0.0
        scaled_fat     = 0.0
        scaled_carbs   = 0.0

        for ing, _, prod in resolved:
            grams = ing.base_grams * scale
            product_names.append(prod.name)
            scaled_grams.append(round(grams, 1))
            scaled_kcal    += prod.kcal_per_100g    / 100 * grams
            scaled_cost    += prod.price_per_100g   / 100 * grams
            scaled_protein += prod.protein_per_100g / 100 * grams
            scaled_fat     += prod.fat_per_100g     / 100 * grams
            scaled_carbs   += prod.carbs_per_100g   / 100 * grams

        # ── Calcular quality_score y main_protein ─────────────────────────
        # Producto con mayor proteína por 100g = proteína principal
        main_prot_name  = ""
        main_prot_price = 0.0
        best_prot_val   = 0.0
        for ing, _, prod in resolved:
            if prod.protein_per_100g > best_prot_val:
                best_prot_val   = prod.protein_per_100g
                main_prot_name  = prod.name
                main_prot_price = prod.price_per_100g

        quality = 1.0
        # Bonus por variedad de ingredientes (receta más completa = más interesante)
        n_ings = len(resolved)
        if n_ings >= 5:
            quality += 0.5
        elif n_ings >= 4:
            quality += 0.3
        # Bonus moderado por proteína de calidad (precio como proxy, reducido)
        if main_prot_price > 1.0:
            quality += 0.5
        # Bonus por pescado/marisco no procesado (reducido para no saturar)
        _PREMIUM = [
            "merluza", "salmón", "salmon", "atún", "atun", "sardina", "bacalao",
            "lubina", "dorada", "panga", "caballa", "gambas", "mejillones",
            "calamar", "pulpo", "langostinos", "pechuga", "solomillo",
        ]
        _PENALTY = [
            "salchicha", "frankfurt", "fuet", "chorizo", "embutido",
            "chopped", "mortadela",
        ]
        name_lower = main_prot_name.lower()
        if any(kw in name_lower for kw in _PREMIUM):
            quality += 0.3
        if any(kw in name_lower for kw in _PENALTY):
            quality -= 0.5
        # Mejora 2 — bonus para proteínas infrarrepresentadas (ternera, cerdo, caballa…)
        _DIVERSITY_BONUS_MAP: dict[str, float] = {
            "ternera":       0.45,
            "vacuno":        0.40,
            "carne picada":  0.35,
            "burger":        0.25,
            "lomo de cerdo": 0.35,
            "cerdo":         0.25,
            "caballa":       0.20,
            "sardina":       0.20,
        }
        for _kw, _bonus in _DIVERSITY_BONUS_MAP.items():
            if _kw in name_lower:
                quality += _bonus
                break
        # Ajuste por valoraciones del usuario
        if recipe.name in rated_positive:
            quality += 1.5
        if recipe.name in rated_negative:
            quality -= 2.0
        # ── Ajuste por preferencias del usuario ───────────────────────────
        if preferences:
            _proteins      = set(preferences.get("proteins", []))
            _restrictions  = set(preferences.get("restrictions", []))
            _breakfast_pref = preferences.get("breakfast", "varied")
            _prot_low = main_prot_name.lower()

            # Palabras clave por tipo de proteína
            _FISH_KWS      = ("merluza","salmón","salmon","atún","atun","sardina","bacalao",
                              "lubina","dorada","panga","caballa","gambas","mejillones",
                              "calamar","pulpo","langostino","berberecho","almeja","sepia",
                              "pota","bonito","caballa","surimi","mejillón")
            _CHICKEN_KWS   = ("pechuga","pollo","pavo","jamón cocido","jamón pavo","lomo de pavo")
            _RED_MEAT_KWS  = ("ternera","cerdo","lomo","carrillada","costilla","solomillo",
                              "buey","carne picada","hamburguesa")
            _LEGUME_KWS    = ("lenteja","garbanzo","alubia","judía","edamame","hummus")

            # Detectar tipo de proteína principal
            _is_fish      = any(kw in _prot_low for kw in _FISH_KWS)
            _is_chicken   = any(kw in _prot_low for kw in _CHICKEN_KWS)
            _is_red_meat  = any(kw in _prot_low for kw in _RED_MEAT_KWS)
            # Legumbre como proteína principal (puede ser categoría)
            _main_prod_cat = ""
            for ing, _, prod in resolved:
                if prod.name == main_prot_name:
                    _main_prod_cat = prod.category
                    break
            _is_legume = _main_prod_cat == "legumbre" or any(kw in _prot_low for kw in _LEGUME_KWS)

            # Protein type preferences
            if _is_fish:
                quality += 0.5 if "fish" in _proteins else -0.8
            if _is_chicken:
                quality += 0.5 if "chicken" in _proteins else -0.5
            if _is_red_meat:
                quality += 0.5 if "red_meat" in _proteins else -0.3
            if _is_legume and "legumes" in _proteins:
                quality += 0.5

            # Hard restrictions — keyword-based exclusion (-999 = never selected)
            _RESTRICTION_KWS: dict[str, tuple[str, ...]] = {
                "gluten_free":  ("pan", "pasta", "harina", "galleta", "cereales", "copos",
                                 "muesli", "cous", "fideos", "macarrón", "spaghetti", "hélices",
                                 "penne", "tallarín", "fideo", "tortilla de trigo", "wrap"),
                "lactose_free": ("leche", "yogur", "queso", "nata", "mantequilla",
                                 "kéfir", "bífidus", "bifidus", "lacteo"),
                "egg_free":     ("huevo", "tortilla"),
                "fish_free":    ("pescado", "merluza", "salmón", "atún", "sardina", "bacalao",
                                 "caballa", "bonito", "trucha", "dorada", "lubina", "rape",
                                 "boquerón", "anchoa", "surimi", "marisco", "gambas",
                                 "langostino", "mejillón", "calamar", "sepia", "pulpo",
                                 "almejas", "berberecho"),
                "nut_free":     ("nuez", "almendra", "avellana", "anacardo", "pistacio",
                                 "pistacho", "cacahuete", "frutos secos"),
                "pork_free":    ("cerdo", "jamón", "chorizo", "bacon", "lomo", "salchichón",
                                 "mortadela", "lacón", "morcilla", "butifarra", "sobrasada",
                                 "panceta"),
                "vegetarian":   ("pollo", "pavo", "ternera", "vacuno", "cerdo", "jamón",
                                 "chorizo", "bacon", "lomo", "carne", "pescado", "merluza",
                                 "salmón", "atún", "sardina", "bacalao", "caballa", "marisco",
                                 "gambas", "calamar"),
            }
            # Vegan expands to vegetarian + lactose_free + egg_free
            effective_restrictions = set(_restrictions)
            if "vegan" in effective_restrictions:
                effective_restrictions.update({"vegetarian", "lactose_free", "egg_free"})

            _recipe_prods_low = " ".join(n.lower() for n in product_names)
            for restr, keywords in _RESTRICTION_KWS.items():
                if restr in effective_restrictions:
                    if any(kw in _recipe_prods_low for kw in keywords):
                        quality -= 999

            # Breakfast preference (only for desayuno recipes)
            if recipe.meal_type == "desayuno":
                _recipe_prods_low = " ".join(n.lower() for n in product_names)
                _has_oats  = any(kw in _recipe_prods_low for kw in ("avena","muesli","cereal"))
                _has_toast = any(kw in _recipe_prods_low for kw in ("pan","tostada","bocadillo"))
                _has_yogurt = any(kw in _recipe_prods_low for kw in ("yogur","kéfir","bifidus"))
                if _breakfast_pref == "oats":
                    if _has_oats:   quality += 0.5
                    if _has_toast:  quality -= 0.3
                elif _breakfast_pref == "toast":
                    if _has_toast:  quality += 0.5
                    if _has_oats:   quality -= 0.3
                elif _breakfast_pref == "yogurt":
                    if _has_yogurt: quality += 0.5

        # ── Ajuste por modelo ML (si está disponible) ─────────────────────
        _bundle = _load_ml_model()
        if _bundle is not None:
            try:
                _clf          = _bundle["model"]
                _recipe_enc   = _bundle["recipe_encoder"]
                _meal_enc     = _bundle["meal_encoder"]
                if recipe.name in _recipe_enc.classes_ and recipe.meal_type in _meal_enc.classes_:
                    _recipe_idx = int(_recipe_enc.transform([recipe.name])[0])
                    _meal_idx   = int(_meal_enc.transform([recipe.meal_type])[0])
                    _feat = [[
                        kcal_target,
                        0.0,          # budget_eur desconocido aquí; se usa 0 como neutral
                        _meal_idx,
                        _recipe_idx,
                        scaled_kcal,
                        scaled_cost,
                    ]]
                    _prob_like = float(_clf.predict_proba(_feat)[0][1])
                    # Escalar prob [0,1] a score [-1.5, +1.5]
                    quality += (_prob_like - 0.5) * 3.0
            except Exception:
                pass  # cualquier error de inferencia — no bloquear

        # Aleatoriedad controlada: rompe empates y garantiza rotación natural
        quality += random.uniform(-0.8, 0.8)

        result[recipe.meal_type].append(ResolvedRecipeData(
            recipe=recipe,
            product_names=product_names,
            scaled_grams=scaled_grams,
            scaled_kcal=round(scaled_kcal, 1),
            scaled_cost=round(scaled_cost, 3),
            scaled_protein=round(scaled_protein, 1),
            scaled_fat=round(scaled_fat, 1),
            scaled_carbs=round(scaled_carbs, 1),
            scale_factor=round(scale, 3),
            quality_score=round(quality, 2),
            main_protein=main_prot_name,
        ))

    # Mejora 1 — penalizar dominancia: el mismo grupo proteíco no acapara el top
    _PROT_GROUPS_KWS: list[tuple[str, list[str]]] = [
        ("gambas",  ["gambón", "gamba", "langostino"]),
        ("pollo",   ["pechuga", "pollo"]),
        ("atun",    ["atún", "atun", "bonito"]),
        ("huevo",   ["huevo", "clara"]),
        ("lacon",   ["lacón", "lacon"]),
        ("salmón",  ["salmón", "salmon"]),
        ("merluza", ["merluza"]),
        ("jamon",   ["jamón cocido", "jamón pavo"]),
    ]

    def _prot_group(prot_name: str) -> str:
        pl = prot_name.lower()
        for grp, kws in _PROT_GROUPS_KWS:
            if any(kw in pl for kw in kws):
                return grp
        return pl[:18]

    for _mt, _rds in result.items():
        if len(_rds) < 6:
            continue
        # Recorrer de mayor a menor calidad y penalizar a partir del 4.º del mismo grupo
        _sorted_idxs = sorted(range(len(_rds)), key=lambda i: _rds[i].quality_score, reverse=True)
        _grp_seen: dict[str, int] = {}
        for _idx in _sorted_idxs:
            _rd = _rds[_idx]
            _grp = _prot_group(_rd.main_protein)
            _cnt = _grp_seen.get(_grp, 0)
            if _cnt >= 3:
                _penalty = 0.35 * (_cnt - 2)
                _rds[_idx].quality_score = round(_rd.quality_score - _penalty, 2)
            _grp_seen[_grp] = _cnt + 1

    return result


if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    sys.stdout.reconfigure(encoding="utf-8")

    from dotenv import load_dotenv
    load_dotenv()

    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        resolve_and_verify(db)
    finally:
        db.close()
