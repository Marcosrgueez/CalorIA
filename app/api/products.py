"""Products endpoints — catalog, price comparison, stats."""
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.diet import DietPlanORM, ProductORM
from app.schemas.diet import ProductResponse

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[ProductResponse], summary="Catálogo de productos")
def list_products(db: Session = Depends(get_db)) -> list[ProductResponse]:
    """Devuelve todos los productos disponibles con su información nutricional y precio."""
    products = db.query(ProductORM).order_by(ProductORM.category, ProductORM.name).all()
    return [
        ProductResponse(
            name=p.name, category=p.category,
            price_per_100g=p.price_per_100g, kcal_per_100g=p.kcal_per_100g,
            protein_per_100g=p.protein_per_100g, fat_per_100g=p.fat_per_100g,
            carbs_per_100g=p.carbs_per_100g, max_grams_per_day=p.max_grams_per_day,
        )
        for p in products
    ]


@router.get("/stats", summary="Estadísticas del catálogo")
def get_catalog_stats(db: Session = Depends(get_db)):
    """Cuenta productos indexados y dietas generadas para las métricas de la home."""
    products_count = db.query(func.count(ProductORM.id)).scalar() or 0
    diets_count    = db.query(func.count(DietPlanORM.id)).scalar() or 0
    return {"products_count": products_count, "diets_generated": diets_count}


@router.get("/compare", summary="Comparar precios de un producto entre supermercados")
def compare_product_prices(keyword: str, db: Session = Depends(get_db)):
    result = {}
    for sm in ["mercadona", "carrefour", "gadis", "consum"]:
        product = (
            db.query(ProductORM)
            .filter(
                ProductORM.supermarket == sm,
                ProductORM.name.ilike(f"%{keyword}%"),
                ProductORM.price_per_100g.isnot(None),
            )
            .order_by(ProductORM.price_per_100g)
            .first()
        )
        if product:
            result[sm] = {
                "name": product.name[:40],
                "price_per_100g": round(product.price_per_100g, 3),
                "package_price": product.package_price_eur,
            }
    return result


@router.post("/compare-batch", summary="Comparar precios de varios productos entre supermercados")
def compare_prices_batch(keywords: list[str], db: Session = Depends(get_db)):
    comparison = {}
    for keyword in keywords[:20]:
        comparison[keyword] = {}
        for sm in ["mercadona", "carrefour", "gadis", "consum"]:
            product = (
                db.query(ProductORM)
                .filter(
                    ProductORM.supermarket == sm,
                    ProductORM.name.ilike(f"%{keyword}%"),
                    ProductORM.price_per_100g.isnot(None),
                )
                .order_by(ProductORM.price_per_100g)
                .first()
            )
            if product:
                comparison[keyword][sm] = {
                    "name": product.name[:40],
                    "price_per_100g": round(product.price_per_100g, 3),
                    "package_price": product.package_price_eur,
                }
    return comparison
