"""
Actualiza max_grams_per_day en ProductORM según categoría.
Los valores del ORM son 500g genéricos del scraping original.

Uso:
    python scripts/fix_max_grams.py           # ejecuta
    python scripts/fix_max_grams.py --dry-run # solo muestra conteos
"""

import argparse
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from app.db.session import SessionLocal
from app.models.diet import ProductORM

# max_grams_per_day por categoría (igual que en normalizer.py)
MAX_GRAMS: dict[str, float] = {
    "proteina":     300.0,
    "legumbre":     200.0,
    "carbohidrato": 250.0,
    "verdura":      400.0,
    "fruta":        300.0,
    "lacteo":       400.0,
    "grasa":         40.0,
}


def main(dry_run: bool) -> None:
    db = SessionLocal()

    try:
        products = db.query(ProductORM).all()
        counter: Counter = Counter()

        for p in products:
            new_max = MAX_GRAMS.get(p.category)
            if new_max is None:
                print(f"  WARN: categoría desconocida '{p.category}' en '{p.name}'")
                continue
            if p.max_grams_per_day != new_max:
                counter[p.category] += 1
                if not dry_run:
                    p.max_grams_per_day = new_max

        if not dry_run:
            db.commit()

        prefix = "[DRY-RUN] " if dry_run else ""
        print(f"{prefix}Productos actualizados por categoría:")
        for cat, n in sorted(counter.items()):
            print(f"  {cat:<15}  {n:>4} productos → {MAX_GRAMS[cat]:.0f}g máx")
        total = sum(counter.values())
        print(f"  {'TOTAL':<15}  {total:>4}")

    finally:
        db.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
