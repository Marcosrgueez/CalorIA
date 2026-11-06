"""
Mapeo de categorías de Mercadona → categorías internas de CalorIA.

Categorías internas: proteina | carbohidrato | verdura | lacteo | grasa

Fuente de IDs: GET https://tienda.mercadona.es/api/categories/
Nivel 0 = sección grande, Nivel 1 = subcategoría navegable (la que usamos).

Solo se incluyen las secciones de alimentación relevantes para el motor LP.
Las secciones excluidas (limpieza, bebé, mascotas, maquillaje, etc.) no se scrapeean.
"""

from dataclasses import dataclass


@dataclass
class CategoryMapping:
    internal: str          # proteina | legumbre | carbohidrato | verdura | fruta | lacteo | grasa
    max_grams_per_day: float


# Mapa: mercadona_subcategory_id → CategoryMapping
# IDs verificados contra GET /categories/ el 2026-04-10
CATEGORY_MAP: dict[int, CategoryMapping] = {
    # ── Fruta y verdura (1) ────────────────────────────────
    27: CategoryMapping("fruta",   400.0),   # Fruta fresca
    28: CategoryMapping("verdura", 400.0),   # Lechuga y ensalada preparada
    29: CategoryMapping("verdura", 500.0),   # Verdura

    # ── Marisco y pescado (2) ──────────────────────────────
    32: CategoryMapping("proteina", 300.0),  # Marisco
    31: CategoryMapping("proteina", 300.0),  # Pescado fresco
    34: CategoryMapping("proteina", 300.0),  # Pescado congelado
    36: CategoryMapping("proteina", 100.0),  # Salazones y ahumados

    # ── Carne (3) ─────────────────────────────────────────
    38: CategoryMapping("proteina", 300.0),  # Aves y pollo
    37: CategoryMapping("proteina", 300.0),  # Cerdo
    40: CategoryMapping("proteina", 300.0),  # Vacuno
    42: CategoryMapping("proteina", 300.0),  # Conejo y cordero
    43: CategoryMapping("proteina", 150.0),  # Embutido
    44: CategoryMapping("proteina", 250.0),  # Hamburguesas y picadas
    45: CategoryMapping("proteina", 250.0),  # Empanados y elaborados
    46: CategoryMapping("proteina", 250.0),  # Arreglos
    47: CategoryMapping("proteina", 300.0),  # Carne congelada

    # ── Charcutería y quesos (4) ──────────────────────────
    48: CategoryMapping("proteina", 150.0),  # Aves y jamón cocido
    49: CategoryMapping("proteina", 100.0),  # Chopped y mortadela
    50: CategoryMapping("proteina", 80.0),   # Jamón serrano
    51: CategoryMapping("proteina", 100.0),  # Embutido curado
    52: CategoryMapping("proteina", 100.0),  # Bacón y salchichas
    53: CategoryMapping("lacteo",   200.0),  # Queso untable, fresco
    54: CategoryMapping("lacteo",   150.0),  # Queso curado, semicurado
    56: CategoryMapping("lacteo",   100.0),  # Queso lonchas y rallado
    58: CategoryMapping("grasa",    40.0),   # Paté y sobrasada

    # ── Panadería y pastelería (5) ────────────────────────
    59: CategoryMapping("carbohidrato", 200.0),  # Pan de horno
    60: CategoryMapping("carbohidrato", 200.0),  # Pan de molde
    62: CategoryMapping("carbohidrato", 100.0),  # Pan tostado y rallado
    64: CategoryMapping("carbohidrato", 80.0),   # Picos y rosquilletas
    65: CategoryMapping("carbohidrato", 100.0),  # Bollería de horno
    66: CategoryMapping("carbohidrato", 80.0),   # Bollería envasada

    # ── Huevos, leche y mantequilla (6) ───────────────────
    72: CategoryMapping("lacteo",   400.0),  # Leche y bebidas vegetales
    75: CategoryMapping("grasa",    30.0),   # Mantequilla y margarina
    77: CategoryMapping("proteina", 300.0),  # Huevos

    # ── Cereales y galletas (7) ───────────────────────────
    78: CategoryMapping("carbohidrato", 150.0),  # Cereales
    79: CategoryMapping("carbohidrato", 80.0),   # Tortitas
    80: CategoryMapping("carbohidrato", 80.0),   # Galletas

    # ── Aceite, especias y salsas (12) ────────────────────
    112: CategoryMapping("grasa", 30.0),   # Aceite, vinagre y sal

    # ── Arroz, legumbres y pasta (13) ─────────────────────
    118: CategoryMapping("carbohidrato", 250.0),  # Arroz
    120: CategoryMapping("carbohidrato", 250.0),  # Pasta y fideos
    121: CategoryMapping("legumbre",     200.0),  # Legumbres

    # ── Conservas (14) ────────────────────────────────────
    122: CategoryMapping("proteina", 200.0),  # Atún y conservas de pescado
    123: CategoryMapping("proteina", 150.0),  # Berberechos y mejillones
    126: CategoryMapping("verdura",  200.0),  # Tomate (conserva)
    127: CategoryMapping("verdura",  200.0),  # Conservas de verdura y frutas

    # ── Aperitivos (15) ───────────────────────────────────
    133: CategoryMapping("grasa",   40.0),   # Frutos secos

    # ── Congelados (17) ───────────────────────────────────
    147: CategoryMapping("carbohidrato", 250.0),  # Arroz y pasta congelados
    148: CategoryMapping("proteina",     300.0),  # Carne congelada
    149: CategoryMapping("proteina",     300.0),  # Pescado congelado
    150: CategoryMapping("proteina",     300.0),  # Marisco congelado
    145: CategoryMapping("verdura",      400.0),  # Verdura congelada

    # ── Postres y yogures (11) ────────────────────────────
    103: CategoryMapping("lacteo", 300.0),  # Yogures desnatados
    104: CategoryMapping("lacteo", 300.0),  # Yogures naturales y sabores
    105: CategoryMapping("lacteo", 300.0),  # Bífidus
    107: CategoryMapping("lacteo", 200.0),  # Yogures infantiles
    108: CategoryMapping("lacteo", 300.0),  # Yogures líquidos
    109: CategoryMapping("lacteo", 200.0),  # Yogures griegos
}

# Secciones de nivel 0 que se scrapeean (todas las alimentarias)
SCRAPE_TOP_LEVEL_IDS: set[int] = {1, 2, 3, 4, 5, 6, 7, 11, 12, 13, 14, 15, 17}


def get_mapping(subcategory_id: int) -> CategoryMapping | None:
    """Devuelve el mapping interno para una subcategoría de Mercadona, o None si no está mapeada."""
    return CATEGORY_MAP.get(subcategory_id)
