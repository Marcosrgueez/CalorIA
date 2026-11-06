"""
Generador de nombres cosméticos para comidas.

Recibe la lista de MealItemResponse de una comida y devuelve un nombre
legible basándose en los ingredientes dominantes por kcal:

  - Ingrediente principal de proteina/legumbre → protagonista
  - Ingrediente principal de carbohidrato → acompañamiento
  - Si no hay carbohidrato, usa verdura como acompañamiento

Ejemplos:
  Pollo + tallarines + guisantes → "Pollo con tallarines"
  Lentejas + pan + guisantes     → "Lentejas con pan"
  Atún + arroz + brócoli         → "Atún con arroz"
  Yogur + cereales               → "Yogur con cereales"
"""

from __future__ import annotations

import re


# Categorías que pueden actuar como protagonista (por orden de prioridad)
_PROTAGONIST_CATS = ("proteina", "legumbre", "lacteo")
# Categorías que pueden actuar como acompañamiento
_SIDEKICK_CATS = ("carbohidrato", "verdura", "fruta", "grasa")


def _short_name(full_name: str) -> str:
    """
    Acorta el nombre del producto para que suene natural en una frase.
    Elimina sufijos entre paréntesis, marcas, y recorta a ≤3 palabras.
    """
    # Quitar contenido entre paréntesis: "Pechuga de pollo (fresca)" → "Pechuga de pollo"
    name = re.sub(r"\s*\([^)]*\)", "", full_name).strip()
    # Quitar porcentajes: "Leche entera 3,5%" → "Leche entera"
    name = re.sub(r"\s*\d[\d,.]*\s*%", "", name).strip()
    # Tomar primeras 3 palabras
    words = name.split()
    name = " ".join(words[:3])
    return name.capitalize()


def name_meal(items: list) -> str:
    """
    Genera un nombre para la comida a partir de sus items.

    items: lista de objetos con atributos .category, .kcal, .product
    (compatible con MealItemResponse y cualquier objeto similar).
    """
    if not items:
        return "Comida"

    # Agrupar kcal por categoría y elegir el ingrediente dominante de cada una
    best: dict[str, tuple[float, str]] = {}  # cat → (kcal, product_name)
    for item in items:
        cat = item.category
        kcal = item.kcal
        if cat not in best or kcal > best[cat][0]:
            best[cat] = (kcal, item.product)

    # Elegir protagonista
    protagonist: str | None = None
    for cat in _PROTAGONIST_CATS:
        if cat in best:
            protagonist = _short_name(best[cat][1])
            break

    # Elegir acompañamiento (excluir la categoría del protagonista)
    protagonist_cat = next(
        (c for c in _PROTAGONIST_CATS if c in best and _short_name(best[c][1]) == protagonist),
        None,
    )
    sidekick: str | None = None
    for cat in _SIDEKICK_CATS:
        if cat in best and cat != protagonist_cat:
            sidekick = _short_name(best[cat][1])
            break

    if protagonist and sidekick:
        return f"{protagonist} con {sidekick.lower()}"
    if protagonist:
        return protagonist
    # Fallback: ingrediente con más kcal
    top = max(items, key=lambda i: i.kcal)
    return _short_name(top.product)


# ─────────────────────────────────────────────────────────────────────────────
# GENERADOR AUTOMÁTICO DE INSTRUCCIONES
# ─────────────────────────────────────────────────────────────────────────────

def _has(names: list[str], *keywords: str) -> bool:
    return any(kw in n for n in names for kw in keywords)


def generate_instructions(
    ingredients: list[tuple[str, str]],   # [(product_name, category), ...]
    meal_type: str,
) -> tuple[list[str], int]:
    """
    Genera pasos de preparación y tiempo estimado para una receta auto-generada.

    ingredients: lista de (nombre_producto, categoría)
    meal_type:   "desayuno" | "comida" | "cena"
    Returns: (pasos: list[str], prep_time_min: int)
    """
    names = [n.lower() for n, _ in ingredients]
    cats  = {c for _, c in ingredients}

    has_protein  = "proteina"     in cats
    has_legume   = "legumbre"     in cats
    has_carb     = "carbohidrato" in cats
    has_veg      = "verdura"      in cats
    has_dairy    = "lacteo"       in cats
    has_fruit    = "fruta"        in cats
    has_fat      = "grasa"        in cats

    is_canned    = _has(names, "lata", "escurrido", "bonito", "caballa", "mejillón", "mejillon")
    is_egg       = _has(names, "huevo", "clara de huevo")
    is_shrimp    = _has(names, "gamba", "langostino")
    is_salmon    = _has(names, "salmón", "salmon")
    is_fish      = _has(names, "merluza", "bacalao", "dorada", "lubina", "rape") and not is_salmon
    is_poultry   = _has(names, "pollo", "pechuga", "contramuslo", "muslo", "pavo")
    is_pork      = _has(names, "cerdo", "lomo", "solomillo", "secreto", "costilla", "panceta")
    is_beef      = _has(names, "ternera", "vacuno", "buey", "carne picada", "filete de ternera")

    # ── DESAYUNOS ─────────────────────────────────────────────────────────
    if meal_type == "desayuno":
        is_yogurt = _has(names, "yogur", "skyr", "requesón", "requeson", "queso fresco")
        is_milk   = _has(names, "leche")
        is_oats   = _has(names, "avena", "muesli", "cereal", "copos")

        if has_dairy and has_carb:
            if is_yogurt:
                return ([
                    "Vierte el yogur en un bol.",
                    "Añade la avena o cereales por encima.",
                    "Mezcla ligeramente y sirve frío.",
                ], 3)
            elif is_milk and is_oats:
                return ([
                    "Calienta la leche en el microondas o un cazo (1-2 min).",
                    "Vierte sobre los copos de avena en un bol.",
                    "Mezcla bien y deja reposar 2 min antes de servir.",
                ], 5)
            else:
                return ([
                    "Prepara el acompañamiento (tuesta el pan o sirve los cereales en un bol).",
                    "Añade el lácteo y sirve.",
                ], 5)
        if has_dairy and has_fruit:
            fruit_name = next((n for n in names if any(k in n for k in ("plátano","platano","manzana","naranja","fresa","pera","kiwi","mandarina","arándano","arandano"))), "fruta")
            if is_milk:
                return ([
                    f"Pela y trocea el {fruit_name.split()[0]}.",
                    "Pon la leche y la fruta en un vaso o batidora.",
                    "Bate 20 segundos y sirve frío.",
                ], 5)
            else:
                return ([
                    f"Lava y trocea la fruta.",
                    "Vierte el yogur en un bol.",
                    "Incorpora la fruta y sirve frío.",
                ], 3)
        if has_carb and has_fruit:
            return ([
                "Lava y trocea la fruta.",
                "Sirve la avena o cereales en un bol.",
                "Añade la fruta encima y sirve.",
            ], 5)
        if has_carb and has_protein:
            return ([
                "Tuesta el pan en tostadora o sartén hasta que esté dorado.",
                "Coloca el ingrediente proteico encima (fiambre, huevo, etc.).",
                "Sirve inmediatamente.",
            ], 5)
        if has_dairy:
            return (["Sirve el lácteo en un vaso o bol y consume frío o templado."], 2)
        return (["Prepara los ingredientes en un bol y sirve."], 5)

    # ── COMIDAS Y CENAS ───────────────────────────────────────────────────
    steps: list[str] = []
    prep_time = 15

    # — Preparación carb (si hay) —
    if has_carb:
        if _has(names, "arroz"):
            steps.append("Cuece el arroz según el paquete o caliéntalo si es precocido.")
        elif _has(names, "pasta"):
            steps.append("Cuece la pasta en agua hirviendo con sal hasta que esté al dente, o caliéntala si es precocida.")
        elif _has(names, "patata"):
            steps.append("Cuece la patata en agua con sal 20 min, o caliéntala si está precocida.")
        elif _has(names, "boniato"):
            steps.append("Cuece el boniato en agua con sal 15-20 min, o caliéntalo si está precocido.")
        elif _has(names, "quinoa"):
            steps.append("Cuece la quinoa en el doble de agua con sal a fuego bajo 15 min.")
        elif _has(names, "pan"):
            steps.append("Tuesta el pan ligeramente en sartén o tostadora.")

    # — Preparación verduras —
    if has_veg:
        steps.append("Lava y corta las verduras en trozos medianos.")

    # — Preparación y cocinado proteína —
    if is_canned:
        steps.append("Abre y escurre bien el líquido de la lata.")
        if has_veg:
            steps.append("Saltea las verduras en sartén con un chorrito de aceite a fuego medio, 4-5 min removiendo.")
            steps.append("Incorpora el contenido de la lata, mezcla y calienta 1-2 min más.")
        elif has_carb:
            steps.append("Mezcla el contenido de la lata con el acompañamiento ya cocido.")
        prep_time = 10

    elif is_egg:
        steps.append("Bate los huevos en un bol con una pizca de sal.")
        if has_veg:
            steps.append("Saltea las verduras en sartén con aceite a fuego medio, 3-4 min.")
            steps.append("Vierte los huevos sobre las verduras y remueve suavemente hasta cuajar (2-3 min).")
        else:
            steps.append("Cuaja los huevos en sartén con un chorrito de aceite a fuego medio-bajo, removiendo para hacer revuelto.")
        prep_time = 10

    elif is_shrimp:
        steps.append("Seca las gambas con papel de cocina.")
        steps.append("Calienta aceite en sartén a fuego alto. Cocina las gambas 2 min por cada lado hasta que estén rosadas.")
        if has_veg:
            steps.append("En la misma sartén, saltea las verduras 4-5 min a fuego medio.")
        prep_time = 15

    elif is_salmon:
        steps.append("Seca el salmón con papel de cocina. Salpimienta generosamente.")
        steps.append("Calienta aceite en sartén antiadherente. Cocina el salmón 4 min por el lado de la piel y 3 min por el otro lado.")
        if has_veg:
            steps.append("Mientras se hace el salmón, saltea las verduras en otra sartén con aceite 4-5 min.")
        prep_time = 20

    elif is_fish:
        steps.append("Seca el pescado con papel de cocina. Salpimienta por ambos lados.")
        steps.append("Calienta aceite en sartén a fuego medio-alto. Cocina el pescado 3-4 min por cada lado hasta que esté hecho.")
        if has_veg:
            steps.append("En la misma sartén, saltea las verduras 4-5 min a fuego medio.")
        prep_time = 20

    elif is_poultry:
        steps.append("Corta el pollo o pavo en trozos o filetes. Salpimienta al gusto.")
        steps.append("Calienta aceite en sartén a fuego medio-alto. Cocina 5-6 min por cada lado hasta que esté dorado y hecho por dentro.")
        if has_veg:
            steps.append("En la misma sartén, saltea las verduras 4-5 min a fuego medio.")
        prep_time = 25

    elif is_pork:
        steps.append("Salpimienta el cerdo por ambos lados.")
        steps.append("Calienta sartén a fuego alto con un chorrito de aceite. Sella el cerdo 4-5 min por cada lado hasta dorar.")
        if has_veg:
            steps.append("Retira el cerdo y, en la misma sartén, saltea las verduras 4-5 min.")
        prep_time = 20

    elif is_beef:
        if _has(names, "picada"):
            steps.append("Salpimienta la carne picada.")
            steps.append("Calienta sartén a fuego alto con un chorrito de aceite. Sofríe la carne removiendo 6-7 min hasta que pierda el color rosado.")
        else:
            steps.append("Salpimienta el filete de ternera.")
            steps.append("Calienta sartén a fuego muy alto. Sella la ternera 3-4 min por cada lado para término medio, o más tiempo si la prefieres bien hecha.")
        if has_veg:
            steps.append("Retira la carne y saltea las verduras en la misma sartén 4-5 min.")
        prep_time = 20

    elif has_legume and not has_protein:
        leg = next((n for n in names if _has([n], "lenteja", "garbanzo", "alubia", "judía", "guisante", "edamame")), "legumbre")
        leg_pretty = leg.split()[0].capitalize() + "s"
        steps.append(f"Escurre y enjuaga bien las {leg_pretty} del bote.")
        if has_veg:
            steps.append("Calienta aceite en sartén a fuego medio. Sofríe las verduras 4-5 min.")
            steps.append(f"Añade las {leg_pretty}, salpimienta y calienta 2-3 min removiendo.")
        elif has_carb:
            steps.append(f"Mezcla las {leg_pretty} con el acompañamiento ya cocido.")
            steps.append("Calienta todo junto en sartén con un chorrito de aceite 2-3 min.")
        else:
            steps.append("Calienta en sartén con aceite 3-4 min, salpimenta y sirve.")
        prep_time = 15

    # — Paso final —
    steps.append("Sirve en el plato, ajusta de sal al gusto y consume caliente.")

    return steps, prep_time
