"""
Mueve legumbres de 'proteina' a 'legumbre' en ProductORM, y actualiza
max_grams_per_day según la categoría destino (200g para legumbre).

Productos afectados: lentejas, garbanzos, alubias, guisantes secos,
habas, soja, etc. que estaban en la subcategoría ID 121 "Legumbres".

Como ProductORM no guarda el ID de subcategoría, identificamos por nombre.

Uso:
    python scripts/fix_legume_category.py           # ejecuta
    python scripts/fix_legume_category.py --dry-run # solo lista
"""

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from app.db.session import SessionLocal
from app.models.diet import ProductORM

_LEGUME_KEYWORDS = {
    "lenteja", "lentejas",
    "garbanzo", "garbanzos",
    "alubia", "alubias",
    "judía", "judías", "judia", "judias",
    "habas", "haba",
    "guisante", "guisantes",       # seco/conserva — los congelados quedan en verdura
    "soja",
    "edamame",
    "frijol", "frijoles",
}


def _is_legume(name: str) -> bool:
    words = set(re.split(r"[^a-záéíóúüñ]+", name.lower()))
    return bool(words & _LEGUME_KEYWORDS)


def main(dry_run: bool) -> None:
    db = SessionLocal()
    moved = 0

    try:
        # Legumbres en proteina o legumbre (para idempotencia)
        candidates = (
            db.query(ProductORM)
            .filter(ProductORM.category.in_(["proteina", "legumbre"]))
            .all()
        )

        to_move = [p for p in candidates if _is_legume(p.name) and p.category != "legumbre"]
        already = [p for p in candidates if _is_legume(p.name) and p.category == "legumbre"]

        print(f"Candidatos en 'proteina': {len(candidates)}")
        print(f"Ya en 'legumbre':          {len(already)}")
        print(f"A mover:                   {len(to_move)}")
        print()

        if to_move:
            print(f"{'Producto':<55}  {'kcal/100g':>9}  {'prot':>5}")
            print("-" * 75)
            for p in sorted(to_move, key=lambda x: x.name):
                print(f"  {p.name:<53}  {p.kcal_per_100g:>8.0f}  {p.protein_per_100g:>4.1f}g")
            print()

        if not dry_run:
            for p in to_move:
                p.category = "legumbre"
                p.max_grams_per_day = 200.0
                moved += 1
            db.commit()
            print(f"BD actualizada: {moved} productos → 'legumbre'.")
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
