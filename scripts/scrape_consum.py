"""
Script de scraping de Consum España.

Uso:
    # Scraping completo
    python scripts/scrape_consum.py

    # Prueba rápida: solo los primeros N términos de búsqueda
    python scripts/scrape_consum.py --max-terms 5

    # Modo dry-run: no escribe en BD
    python scripts/scrape_consum.py --dry-run --max-terms 3
"""

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from app.db.session import SessionLocal, engine
from app.models.diet import Base, ProductORM, ProductPendingORM
from app.scraper.mercadona import PendingProduct, ScrapedProduct
from app.scraper.consum import scrape

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("scrape_consum")


def _upsert_products(
    ready: list[ScrapedProduct],
    pending: list[PendingProduct],
    dry_run: bool,
) -> None:
    if dry_run:
        log.info("[DRY-RUN] %d listos / %d pendientes en este batch.", len(ready), len(pending))
        for p in ready[:5]:
            log.info("  [ready]   %s | %.3f€/100g | %.0fkcal | %s",
                     p.name, p.price_per_100g, p.kcal_per_100g, p.category)
        for p in pending[:3]:
            log.info("  [pending] %s | %s | %s", p.name, p.internal_category, p.reason)
        return

    db = SessionLocal()
    inserted = updated = pending_inserted = 0
    try:
        for p in ready:
            existing = db.query(ProductORM).filter_by(
                name=p.name, supermarket="consum"
            ).first()
            kwargs = dict(
                category=p.category,
                price_per_100g=p.price_per_100g,
                kcal_per_100g=p.kcal_per_100g,
                protein_per_100g=p.protein_per_100g,
                fat_per_100g=p.fat_per_100g,
                carbs_per_100g=p.carbs_per_100g,
                max_grams_per_day=p.max_grams_per_day,
                ean=p.ean,
                source=p.source,
                scraped_at=p.scraped_at,
                package_size_g=p.__dict__.get("_package_size_g"),
                package_price_eur=p.__dict__.get("_package_price_eur"),
            )
            if existing:
                for k, v in kwargs.items():
                    setattr(existing, k, v)
                updated += 1
            else:
                db.add(ProductORM(
                    name=p.name,
                    supermarket="consum",
                    min_grams_per_day=0.0,
                    **kwargs,
                ))
                inserted += 1

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
        log.info("BD: +%d insertados, %d actualizados, %d pendientes nuevos.",
                 inserted, updated, pending_inserted)
    except Exception:
        db.rollback()
        log.exception("Error al escribir en BD, rollback aplicado.")
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Scraper de Consum para CalorIA")
    parser.add_argument("--max-terms", type=int, default=None,
                        help="Limitar número de términos de búsqueda (útil para pruebas)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Ejecutar sin escribir en la base de datos")
    args = parser.parse_args()

    log.info("Iniciando scraping Consum (max_terms=%s, dry_run=%s)",
             args.max_terms, args.dry_run)

    if not args.dry_run:
        Base.metadata.create_all(bind=engine)

    total_ready = total_pending = terms_done = 0

    for batch_ready, batch_pending in scrape(max_terms=args.max_terms):
        _upsert_products(batch_ready, batch_pending, dry_run=args.dry_run)
        total_ready   += len(batch_ready)
        total_pending += len(batch_pending)
        terms_done    += 1
        log.info("── [%d términos] acumulado: %d listos │ %d pendientes ──",
                 terms_done, total_ready, total_pending)

    log.info("Scraping completo: %d términos │ %d listos │ %d pendientes.",
             terms_done, total_ready, total_pending)


if __name__ == "__main__":
    main()
