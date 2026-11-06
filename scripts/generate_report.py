"""
Genera informe de cobertura del catálogo scrapeado.
Lee de la BD (productos y pendientes) y escribe reports/coverage_report.txt.

Uso:
    python scripts/generate_report.py
    python scripts/generate_report.py --print-only   # no guarda fichero
"""

import argparse
import os
import sys
from collections import Counter
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from app.db.session import SessionLocal
from app.models.diet import ProductORM, ProductPendingORM

REPORT_PATH = os.path.join(os.path.dirname(__file__), "..", "reports", "coverage_report.txt")


def generate(print_only: bool = False) -> str:
    db = SessionLocal()
    lines = []

    try:
        ready_all   = db.query(ProductORM).filter(ProductORM.source == "mercadona").all()
        pending_all = db.query(ProductPendingORM).all()

        total_ready   = len(ready_all)
        total_pending = len(pending_all)
        total = total_ready + total_pending

        # ── Cabecera ──────────────────────────────────────────────
        lines += [
            "═" * 65,
            "  INFORME DE COBERTURA — CalorIA × Mercadona",
            f"  Generado: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            "═" * 65,
            "",
        ]

        # ── Resumen global ────────────────────────────────────────
        pct_ready   = total_ready   / total * 100 if total else 0
        pct_pending = total_pending / total * 100 if total else 0

        lines += [
            "RESUMEN GLOBAL",
            "─" * 65,
            f"  Total productos encontrados en Mercadona : {total:>5}",
            f"  Listos en ProductORM (macros completos)  : {total_ready:>5}  ({pct_ready:.1f}%)",
            f"  Pendientes en ProductPendingORM           : {total_pending:>5}  ({pct_pending:.1f}%)",
            "",
        ]

        # ── Cobertura por categoría interna ───────────────────────
        lines += [
            "COBERTURA POR CATEGORÍA INTERNA",
            "─" * 65,
            f"  {'Categoría':<14}  {'Listos':>6}  {'Pendientes':>10}  {'Total':>6}  {'Cobertura':>10}",
            f"  {'─'*14}  {'─'*6}  {'─'*10}  {'─'*6}  {'─'*10}",
        ]

        cats_internal = ["proteina", "carbohidrato", "verdura", "lacteo", "grasa"]
        for cat in cats_internal:
            r = sum(1 for p in ready_all if p.category == cat)
            p = sum(1 for x in pending_all if x.internal_category == cat)
            t = r + p
            cov = r / t * 100 if t else 0
            lines.append(f"  {cat:<14}  {r:>6}  {p:>10}  {t:>6}  {cov:>9.1f}%")

        # Pendientes sin categoría interna
        no_cat = sum(1 for x in pending_all if x.internal_category is None)
        if no_cat:
            lines.append(f"  {'(sin categoría)':<14}  {'':>6}  {no_cat:>10}  {no_cat:>6}  {'–':>10}")
        lines.append("")

        # ── Razones de pendientes ─────────────────────────────────
        reasons = Counter(x.reason for x in pending_all)
        lines += [
            "RAZONES DE PENDIENTES",
            "─" * 65,
        ]
        for reason, count in reasons.most_common():
            pct = count / total_pending * 100 if total_pending else 0
            lines.append(f"  {reason:<24}  {count:>5}  ({pct:.1f}%)")
        lines.append("")

        # ── Top 10 kcal/€ ─────────────────────────────────────────
        lines += [
            "TOP 10 PRODUCTOS POR RATIO KCAL/€",
            "─" * 65,
            f"  {'#':>2}  {'Producto':<38}  {'Cat.':<13}  {'kcal/100g':>9}  {'€/100g':>7}  {'kcal/€':>7}",
            f"  {'─'*2}  {'─'*38}  {'─'*13}  {'─'*9}  {'─'*7}  {'─'*7}",
        ]

        def kcal_eur_ratio(p: ProductORM) -> float:
            if p.price_per_100g <= 0:
                return 0.0
            return p.kcal_per_100g / p.price_per_100g

        top10 = sorted(ready_all, key=kcal_eur_ratio, reverse=True)[:10]
        for i, p in enumerate(top10, 1):
            ratio = kcal_eur_ratio(p)
            lines.append(
                f"  {i:>2}. {p.name[:37]:<37}  {p.category:<13}"
                f"  {p.kcal_per_100g:>8.0f}  {p.price_per_100g:>6.3f}€  {ratio:>6.0f}"
            )
        lines.append("")

        # ── Productos listos por categoría (detalle) ──────────────
        lines += [
            "DISTRIBUCIÓN DE PRODUCTOS LISTOS POR CATEGORÍA",
            "─" * 65,
        ]
        for cat in cats_internal:
            prods = [p for p in ready_all if p.category == cat]
            if not prods:
                lines.append(f"  {cat}: (ninguno)")
                continue
            avg_price = sum(p.price_per_100g for p in prods) / len(prods)
            avg_kcal  = sum(p.kcal_per_100g for p in prods) / len(prods)
            lines.append(
                f"  {cat:<14}  {len(prods):>3} productos"
                f"  │  precio medio: {avg_price:.3f}€/100g"
                f"  │  kcal media: {avg_kcal:.0f}"
            )
        lines.append("")

    finally:
        db.close()

    report = "\n".join(lines)

    if not print_only:
        os.makedirs(os.path.dirname(os.path.abspath(REPORT_PATH)), exist_ok=True)
        with open(REPORT_PATH, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"Informe guardado en: {os.path.abspath(REPORT_PATH)}")

    return report


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--print-only", action="store_true")
    args = parser.parse_args()
    print(generate(print_only=args.print_only))
