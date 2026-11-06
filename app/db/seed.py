from sqlalchemy.orm import Session

from app.engine.diet_engine import SAMPLE_PRODUCTS
from app.models.diet import ProductORM


def seed_products(db: Session) -> None:
    """
    Inserta SAMPLE_PRODUCTS en la tabla products si está vacía.
    Idempotente: no hace nada si ya hay productos.
    """
    if db.query(ProductORM).count() > 0:
        return

    db.add_all(
        [
            ProductORM(
                name=p.name,
                category=p.category,
                price_per_100g=p.price_per_100g,
                kcal_per_100g=p.kcal_per_100g,
                protein_per_100g=p.protein_per_100g,
                fat_per_100g=p.fat_per_100g,
                carbs_per_100g=p.carbs_per_100g,
                max_grams_per_day=p.max_grams_per_day,
                min_grams_per_day=p.min_grams_per_day,
            )
            for p in SAMPLE_PRODUCTS
        ]
    )
    db.commit()
