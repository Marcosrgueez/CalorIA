"""
Mueve productos mal categorizados como 'verdura' a 'fruta' en ProductORM.

Los productos frutales llegaron a la categoría 'verdura' porque Mercadona
agrupa frutas y verduras en la misma sección (ID 27 "Fruta", antes mapeado
a 'verdura'). El normalizer ya está corregido para futuros scrapings.

Criterio: nombre contiene palabras clave de fruta, o es un producto de
conserva/congelado de fruta.

Uso:
    python scripts/fix_fruit_category.py           # ejecuta el fix
    python scripts/fix_fruit_category.py --dry-run # solo lista, no modifica
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from app.db.session import SessionLocal
from app.models.diet import ProductORM

# Palabras clave por palabra completa que indican fruta.
# Se usa coincidencia de palabras enteras (split en espacios y signos no alfa).
_FRUIT_KEYWORDS = {
    "naranja", "naranjas",
    "mandarina", "mandarinas",
    "limón", "limones", "limon",
    "fresa", "fresas",
    "frambuesa", "frambuesas",
    "arándano", "arándanos", "arandano", "arandanos",
    "cereza", "cerezas",
    "melocotón", "melocotones", "melocoton",
    "nectarina", "nectarinas",
    "albaricoque", "albaricoques",
    "manzana", "manzanas",
    "plátano", "plátanos", "platano", "platanos",
    "piña", "piñas",            # con tilde — evita "espinaca" → "pina"
    "mango", "mangos",
    "kiwi", "kiwis",
    "uva", "uvas",
    "sandía", "sandias", "sandia",
    "melón", "melones", "melon",
    "ciruela", "ciruelas",
    "membrillo",
    "frutas",                   # "mix frutas", "dúo frutas", "macedonia … frutas"
    "frutos",                   # "frutos rojos", "frutos del bosque"
    "tropical",                 # "mix frutas tropical"
}

# Producto es fruta si alguna de estas frases aparece como subcadena
_FRUIT_PHRASES = {
    "postre de manzana",
    "mix fruta",
    "mezcla de fruta",
}

# Si el nombre contiene estas palabras, NO es fruta (evita falsos positivos)
_NOT_FRUIT_WORDS = {"verduras", "verdura", "vegetal", "vegetales", "espinaca", "espinacas"}


def _is_fruit(name: str) -> bool:
    import re
    name_lower = name.lower()

    # Exclusión explícita
    if any(w in name_lower for w in _NOT_FRUIT_WORDS):
        return False

    # Frases exactas
    if any(phrase in name_lower for phrase in _FRUIT_PHRASES):
        return True

    # Palabras completas (separadas por espacios o signos no alfa)
    words = set(re.split(r"[^a-záéíóúüñ]+", name_lower))
    return bool(words & _FRUIT_KEYWORDS)


def main(dry_run: bool) -> None:
    db = SessionLocal()
    moved = 0
    kept  = 0

    try:
        verduras = db.query(ProductORM).filter(ProductORM.category == "verdura").all()
        print(f"Productos con categoria='verdura': {len(verduras)}")
        print()

        to_move = [p for p in verduras if _is_fruit(p.name)]
        to_keep = [p for p in verduras if not _is_fruit(p.name)]

        print(f"Se moverán a 'fruta':  {len(to_move)}")
        print(f"Se quedan en 'verdura': {len(to_keep)}")
        print()

        if to_move:
            print(f"{'Producto':<58}  {'kcal/100g':>9}")
            print("-" * 70)
            for p in sorted(to_move, key=lambda x: x.name):
                print(f"  {p.name:<56}  {p.kcal_per_100g:>8.0f}")
            print()

        if not dry_run:
            for p in to_move:
                p.category = "fruta"
                moved += 1
            db.commit()
            print(f"BD actualizada: {moved} productos movidos a 'fruta'.")
        else:
            print("[DRY-RUN] No se ha modificado nada.")

    finally:
        db.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
