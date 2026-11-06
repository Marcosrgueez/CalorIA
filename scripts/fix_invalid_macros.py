"""
Recorre ProductORM y mueve a ProductPendingORM los productos con macros
fuera de rango, usando la misma lógica de _validate_macros del scraper.

Uso:
    python scripts/fix_invalid_macros.py           # mueve los inválidos
    python scripts/fix_invalid_macros.py --dry-run # solo lista, no modifica
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from app.db.session import SessionLocal
from app.models.diet import ProductORM, ProductPendingORM
from app.scraper.mercadona import _validate_macros


def main(dry_run: bool) -> None:
    db = SessionLocal()
    moved = 0
    kept  = 0
    worst: list[tuple[str, str, float]] = []  # (name, category, kcal)

    try:
        products = db.query(ProductORM).filter(ProductORM.source == "mercadona").all()
        print(f"Productos Mercadona en BD: {len(products)}")

        for p in products:
            macros = {
                "kcal_per_100g":    p.kcal_per_100g,
                "protein_per_100g": p.protein_per_100g,
                "fat_per_100g":     p.fat_per_100g,
                "carbs_per_100g":   p.carbs_per_100g,
            }
            if _validate_macros(p.category, macros):
                kept += 1
                continue

            worst.append((p.name, p.category, p.kcal_per_100g))
            moved += 1

            if not dry_run:
                # Insertar en pendientes si no existe ya
                exists = db.query(ProductPendingORM).filter_by(
                    mercadona_id=p.ean or f"ean_missing_{p.id}"
                ).first()
                if not exists:
                    db.add(ProductPendingORM(
                        mercadona_id=p.ean or f"ean_missing_{p.id}",
                        name=p.name,
                        ean=p.ean,
                        mercadona_category=p.category,
                        internal_category=p.category,
                        price_per_100g=p.price_per_100g,
                        reason="invalid_macros",
                    ))
                db.delete(p)

        if not dry_run:
            db.commit()

        prefix = "[DRY-RUN] " if dry_run else ""
        print(f"\n{prefix}Resultado:")
        print(f"  Válidos (se quedan):  {kept}")
        print(f"  Inválidos (movidos):  {moved}")
        print()

        if worst:
            print(f"{'Producto':<50}  {'Cat.':<13}  {'kcal/100g':>9}")
            print("─" * 80)
            for name, cat, kcal in sorted(worst, key=lambda x: x[2]):
                print(f"  {name:<48}  {cat:<13}  {kcal:>8.1f}")

    finally:
        db.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
