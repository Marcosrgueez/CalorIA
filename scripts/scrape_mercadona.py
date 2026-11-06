"""
Script de scraping manual de Mercadona.

Uso:
    # Scraping completo (puede tardar 30-60 min por delays y volumen)
    python scripts/scrape_mercadona.py

    # Prueba rápida: solo las primeras N subcategorías
    python scripts/scrape_mercadona.py --max-categories 3

    # Modo dry-run: no escribe en BD
    python scripts/scrape_mercadona.py --dry-run --max-categories 2
"""

import argparse
import logging
import os
import sys

# Añadir raíz del proyecto al path para importar `app`
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from app.db.session import SessionLocal, engine
from app.models.diet import Base, ProductORM, ProductPendingORM
from app.scraper.mercadona import PendingProduct, ScrapedProduct, scrape

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("scrape_mercadona")


def _upsert_products(
    ready: list[ScrapedProduct],
    pending: list[PendingProduct],
    dry_run: bool,
) -> None:
    """Inserta/actualiza productos en BD. Usa name como clave de upsert."""
    if dry_run:
        log.info("[DRY-RUN] Se insertarían %d productos y %d pendientes.", len(ready), len(pending))
        for p in ready[:5]:
            log.info("  [ready]   %s | %.2f€/100g | %.0fkcal | %s", p.name, p.price_per_100g, p.kcal_per_100g, p.category)
        for p in pending[:5]:
            log.info("  [pending] %s | %s | %s", p.name, p.mercadona_category, p.reason)
        return

    db = SessionLocal()

    inserted = updated = pending_inserted = 0
    try:
        for p in ready:
            existing = db.query(ProductORM).filter_by(name=p.name).first()
            if existing:
                existing.category         = p.category
                existing.price_per_100g   = p.price_per_100g
                existing.kcal_per_100g    = p.kcal_per_100g
                existing.protein_per_100g = p.protein_per_100g
                existing.fat_per_100g     = p.fat_per_100g
                existing.carbs_per_100g   = p.carbs_per_100g
                existing.max_grams_per_day = p.max_grams_per_day
                existing.ean              = p.ean
                existing.source           = p.source
                existing.scraped_at       = p.scraped_at
                updated += 1
            else:
                db.add(ProductORM(
                    name=p.name,
                    category=p.category,
                    price_per_100g=p.price_per_100g,
                    kcal_per_100g=p.kcal_per_100g,
                    protein_per_100g=p.protein_per_100g,
                    fat_per_100g=p.fat_per_100g,
                    carbs_per_100g=p.carbs_per_100g,
                    max_grams_per_day=p.max_grams_per_day,
                    min_grams_per_day=0.0,
                    ean=p.ean,
                    source=p.source,
                    supermarket=p.supermarket,
                    scraped_at=p.scraped_at,
                ))
                db.flush()  # visible to subsequent filter_by queries in same session
                inserted += 1

        # Productos pendientes: insertar solo si no existe ya (por mercadona_id)
        for pp in pending:
            exists = db.query(ProductPendingORM).filter_by(
                mercadona_id=pp.mercadona_id
            ).first()
            if not exists:
                db.add(ProductPendingORM(
                    mercadona_id=pp.mercadona_id,
                    name=pp.name,
                    ean=pp.ean,
                    mercadona_category=pp.mercadona_category,
                    internal_category=pp.internal_category,
                    price_per_100g=pp.price_per_100g,
                    reason=pp.reason,
                ))
                pending_inserted += 1

        db.commit()
        log.info(
            "BD actualizada: %d insertados, %d actualizados, %d pendientes nuevos.",
            inserted, updated, pending_inserted,
        )
    except Exception:
        db.rollback()
        log.exception("Error al escribir en BD, rollback aplicado.")
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Scraper de catálogo Mercadona para CalorIA")
    parser.add_argument(
        "--max-categories", type=int, default=None,
        help="Limitar número de subcategorías procesadas (útil para pruebas)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Ejecutar scraping sin escribir en la base de datos",
    )
    args = parser.parse_args()

    log.info(
        "Iniciando scraping (max_categories=%s, dry_run=%s)",
        args.max_categories, args.dry_run,
    )

    # Crear tablas ANTES de scraping, para que estén disponibles desde el inicio
    if not args.dry_run:
        Base.metadata.create_all(bind=engine)
        log.info("Tablas verificadas/creadas en BD.")

    total_ready = total_pending = cats_done = 0

    for batch_ready, batch_pending in scrape(max_categories=args.max_categories):
        _upsert_products(batch_ready, batch_pending, dry_run=args.dry_run)
        total_ready   += len(batch_ready)
        total_pending += len(batch_pending)
        cats_done     += 1
        log.info(
            "── [%d subcats] acumulado: %d listos │ %d pendientes ──",
            cats_done, total_ready, total_pending,
        )

    log.info(
        "Scraping completo: %d subcategorías │ %d listos │ %d pendientes.",
        cats_done, total_ready, total_pending,
    )


if __name__ == "__main__":
    main()
