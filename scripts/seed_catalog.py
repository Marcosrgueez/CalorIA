"""
Pobla la BD con un catálogo amplio de productos de Mercadona.
Solo inserta productos que no existan ya (idempotente por nombre).

Uso:
    python scripts/seed_catalog.py
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from app.db.session import SessionLocal
from app.models.diet import ProductORM

# (nombre, categoria, price_per_100g, kcal, prot, fat, carbs, max_g)
PRODUCTS = [
    # ── PROTEÍNAS ─────────────────────────────────────────────────────────
    ("Pechuga de pollo",          "proteina",    0.60, 110, 23.0,  1.5,  0.0, 400),
    ("Contramuslo de pollo",      "proteina",    0.45, 175, 18.0, 11.0,  0.0, 400),
    ("Muslo de pollo",            "proteina",    0.40, 190, 17.0, 13.0,  0.0, 350),
    ("Pechuga de pavo",           "proteina",    0.65, 107, 24.0,  1.0,  0.0, 400),
    ("Lomo de cerdo",             "proteina",    0.55, 143, 22.0,  6.0,  0.0, 350),
    ("Solomillo de cerdo",        "proteina",    0.80, 133, 22.0,  5.0,  0.0, 300),
    ("Ternera picada",            "proteina",    0.85, 175, 20.0, 10.0,  0.0, 350),
    ("Filete de ternera",         "proteina",    1.20, 165, 22.0,  8.0,  0.0, 300),
    ("Merluza (filete congelado)","proteina",    0.70,  82, 17.5,  1.2,  0.0, 350),
    ("Bacalao desalado",          "proteina",    0.90,  84, 19.0,  0.7,  0.0, 300),
    ("Dorada (filete)",           "proteina",    1.10, 128, 19.0,  5.5,  0.0, 300),
    ("Lubina (filete)",           "proteina",    1.20, 124, 18.5,  5.5,  0.0, 300),
    ("Salmón fresco",             "proteina",    1.40, 208, 20.0, 14.0,  0.0, 300),
    ("Atún en lata (escurrido)",  "proteina",    0.55, 116, 26.0,  1.0,  0.0, 200),
    ("Bonito en lata (escurrido)","proteina",    0.60, 130, 24.0,  4.0,  0.0, 200),
    ("Caballa en lata",           "proteina",    0.45, 190, 19.0, 12.0,  0.0, 200),
    ("Gambas peladas (congelado)","proteina",    1.30,  85, 18.0,  1.0,  0.5, 250),
    ("Mejillones en lata",        "proteina",    0.50, 110, 17.0,  3.5,  2.5, 200),
    ("Huevos (pieza ~50g)",       "proteina",    0.25, 155, 13.0, 11.0,  1.1, 300),
    ("Clara de huevo",            "proteina",    0.30,  52, 11.0,  0.2,  0.7, 300),
    # ── LEGUMBRES ─────────────────────────────────────────────────────────
    ("Lentejas cocidas",          "legumbre",    0.12, 116,  9.0,  0.4, 20.0, 400),
    ("Garbanzos cocidos",         "legumbre",    0.14, 164,  8.9,  2.6, 27.4, 400),
    ("Alubias blancas cocidas",   "legumbre",    0.13, 130,  9.0,  0.5, 23.0, 400),
    ("Alubias negras cocidas",    "legumbre",    0.14, 132,  8.9,  0.5, 23.7, 400),
    ("Alubias pintas cocidas",    "legumbre",    0.13, 128,  8.7,  0.5, 23.0, 400),
    ("Guisantes cocidos",         "legumbre",    0.18,  81,  5.4,  0.4, 14.5, 300),
    ("Edamame (vaina)",           "legumbre",    0.40, 122, 11.0,  5.2,  8.9, 200),
    # ── CARBOHIDRATOS ─────────────────────────────────────────────────────
    ("Arroz blanco cocido",       "carbohidrato",0.08, 130,  2.7,  0.3, 28.0, 500),
    ("Arroz integral cocido",     "carbohidrato",0.10, 111,  2.6,  0.9, 23.0, 500),
    ("Pasta cocida",              "carbohidrato",0.09, 158,  5.8,  0.9, 31.0, 400),
    ("Pasta integral cocida",     "carbohidrato",0.12, 149,  5.9,  1.1, 28.0, 400),
    ("Patata cocida",             "carbohidrato",0.08,  77,  2.0,  0.1, 17.0, 400),
    ("Boniato cocido",            "carbohidrato",0.12,  86,  1.6,  0.1, 20.0, 350),
    ("Pan integral",              "carbohidrato",0.22, 247,  9.0,  3.5, 41.0, 150),
    ("Pan de molde integral",     "carbohidrato",0.28, 255,  8.5,  4.0, 43.0, 120),
    ("Avena en copos",            "carbohidrato",0.15, 389, 17.0,  7.0, 66.0, 100),
    ("Muesli sin azúcar",         "carbohidrato",0.35, 370, 11.0,  7.5, 64.0,  80),
    ("Quinoa cocida",             "carbohidrato",0.25, 120,  4.4,  1.9, 21.3, 300),
    ("Copos de avena finos",      "carbohidrato",0.14, 370, 13.0,  7.0, 62.0, 100),
    # ── VERDURAS ──────────────────────────────────────────────────────────
    ("Espinacas frescas",         "verdura",     0.18,  23,  2.9,  0.4,  1.4, 300),
    ("Tomate",                    "verdura",     0.10,  18,  0.9,  0.2,  3.9, 400),
    ("Brócoli",                   "verdura",     0.20,  34,  2.8,  0.4,  7.0, 300),
    ("Zanahoria",                 "verdura",     0.09,  41,  0.9,  0.2,  9.6, 300),
    ("Pimiento rojo",             "verdura",     0.15,  31,  1.0,  0.3,  6.0, 300),
    ("Pimiento verde",            "verdura",     0.12,  20,  0.9,  0.2,  4.6, 300),
    ("Calabacín",                 "verdura",     0.14,  17,  1.2,  0.3,  3.1, 350),
    ("Berenjena",                 "verdura",     0.12,  25,  1.0,  0.2,  5.9, 300),
    ("Champiñones",               "verdura",     0.20,  22,  3.1,  0.3,  3.3, 250),
    ("Cebolla",                   "verdura",     0.08,  40,  1.1,  0.1,  9.3, 200),
    ("Lechuga romana",            "verdura",     0.15,  17,  1.2,  0.3,  2.4, 200),
    ("Pepino",                    "verdura",     0.10,  15,  0.6,  0.1,  3.6, 300),
    ("Coliflor",                  "verdura",     0.18,  25,  1.9,  0.3,  5.0, 300),
    ("Acelgas",                   "verdura",     0.15,  19,  1.8,  0.2,  3.7, 300),
    ("Puerro",                    "verdura",     0.20,  61,  1.5,  0.3, 14.0, 200),
    ("Espárragos",                "verdura",     0.35,  20,  2.2,  0.1,  3.9, 200),
    ("Judías verdes",             "verdura",     0.18,  31,  1.8,  0.1,  7.1, 250),
    ("Col de bruselas",           "verdura",     0.22,  43,  3.4,  0.5,  9.0, 250),
    # ── LÁCTEOS ───────────────────────────────────────────────────────────
    ("Leche entera",              "lacteo",      0.07,  61,  3.2,  3.3,  4.8, 500),
    ("Leche semidesnatada",       "lacteo",      0.07,  46,  3.2,  1.5,  4.8, 500),
    ("Yogur natural",             "lacteo",      0.10,  59,  3.5,  3.0,  4.0, 400),
    ("Yogur griego",              "lacteo",      0.18, 133,  4.5, 10.0,  3.5, 300),
    ("Skyr natural",              "lacteo",      0.25,  67, 11.0,  0.3,  4.0, 250),
    ("Queso fresco",              "lacteo",      0.30,  99,  8.5,  6.5,  2.5, 200),
    ("Requesón",                  "lacteo",      0.25,  74,  9.0,  3.0,  3.6, 250),
    # ── FRUTAS ────────────────────────────────────────────────────────────
    ("Manzana",                   "fruta",       0.15,  52,  0.3,  0.2, 14.0, 300),
    ("Plátano",                   "fruta",       0.12,  89,  1.1,  0.3, 23.0, 200),
    ("Naranja",                   "fruta",       0.12,  47,  0.9,  0.1, 12.0, 300),
    ("Fresa",                     "fruta",       0.28,  32,  0.7,  0.3,  7.7, 300),
    ("Pera",                      "fruta",       0.15,  57,  0.4,  0.1, 15.0, 300),
    ("Kiwi",                      "fruta",       0.22,  61,  1.1,  0.5, 15.0, 200),
    ("Mandarina",                 "fruta",       0.13,  53,  0.8,  0.3, 13.0, 300),
    ("Arándanos",                 "fruta",       0.50,  57,  0.7,  0.3, 14.0, 200),
    # ── GRASAS ────────────────────────────────────────────────────────────
    ("Aceite de oliva",           "grasa",       0.55, 884,  0.0,100.0,  0.0,  30),
    ("Aguacate",                  "grasa",       0.35, 160,  2.0, 15.0,  9.0, 150),
]


def main() -> None:
    db = SessionLocal()
    existing = {p.name for p in db.query(ProductORM.name).all()}  # type: ignore[attr-defined]

    added = 0
    for name, cat, price, kcal, prot, fat, carbs, max_g in PRODUCTS:
        if name in existing:
            continue
        db.add(ProductORM(
            name=name,
            category=cat,
            price_per_100g=price,
            kcal_per_100g=kcal,
            protein_per_100g=prot,
            fat_per_100g=fat,
            carbs_per_100g=carbs,
            max_grams_per_day=float(max_g),
            supermarket="mercadona",
            source="manual",
        ))
        added += 1

    db.commit()
    db.close()

    total = len(PRODUCTS)
    print(f"Productos añadidos: {added} / {total}  (ya existían: {total - added})")


if __name__ == "__main__":
    main()
