"""
Actualiza package_size_g y package_price_eur en ProductORM
consultando la API de Mercadona por mercadona_id.

Estrategia:
  - Cruza EANs de ProductORM con mercadona_id de ProductPendingORM.
  - Para cada producto con cruce encontrado, llama a /api/products/{id}/.
  - Extrae unit_size y unit_price de price_instructions.
  - Convierte unit_size a gramos según size_format (kg/l → ×1000; g/ml → ×1).
  - Productos con size_format=ud (precio por unidad sin peso fijo) quedan sin package_size_g.

Uso:
    python scripts/update_package_info.py            # ejecuta
    python scripts/update_package_info.py --dry-run  # solo muestra, no modifica BD
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv()

import httpx

from app.db.session import SessionLocal
from app.models.diet import ProductORM, ProductPendingORM

MERCADONA_BASE = "https://tienda.mercadona.es/api"
DELAY = 0.5   # segundos entre requests
REPORT_EVERY = 50

_HEADERS = {
    "Accept-Language": "es",
    "User-Agent": "CalorIA/0.1 (educational project, contact: dev@caloria.local)",
}

# Factores de conversión a gramos según size_format de la API
_TO_GRAMS = {
    "kg": 1000.0,
    "l":  1000.0,   # litros → mililitros ≈ gramos para alimentos acuosos
    "g":  1.0,
    "ml": 1.0,
    "cl": 10.0,
}
# Formatos sin conversión posible a gramos (precio por unidad sin peso)
_SKIP_FORMATS = {"ud", "dz", ""}


def _size_to_grams(unit_size, size_format: str) -> float | None:
    """Convierte unit_size al formato dado en gramos. None si no es convertible."""
    if unit_size is None or size_format is None:
        return None
    fmt = str(size_format).lower().strip()
    if fmt in _SKIP_FORMATS:
        return None
    factor = _TO_GRAMS.get(fmt)
    if factor is None:
        return None
    try:
        return round(float(unit_size) * factor, 1)
    except (ValueError, TypeError):
        return None


def main(dry_run: bool) -> None:
    db = SessionLocal()
    client = httpx.Client(headers=_HEADERS, timeout=15)

    try:
        # ── Construir mapa EAN → mercadona_id desde ProductPendingORM ──
        pending = db.query(ProductPendingORM).filter(
            ProductPendingORM.mercadona_id != None,
            ProductPendingORM.ean != None,
        ).all()
        ean_to_mid: dict[str, str] = {p.ean: p.mercadona_id for p in pending}
        print(f"EAN→mercadona_id disponibles en ProductPendingORM: {len(ean_to_mid)}")

        # ── Productos a actualizar ──
        products = db.query(ProductORM).filter(
            ProductORM.ean != None,
        ).all()

        to_update = [(p, ean_to_mid[p.ean]) for p in products if p.ean in ean_to_mid]
        print(f"ProductORM con EAN en Mercadona:  {len(products)}")
        print(f"Productos con mercadona_id cruzado: {len(to_update)}")
        print()

        stats = {"ok": 0, "no_size": 0, "error": 0, "already": 0}
        examples = []

        for idx, (prod, mid) in enumerate(to_update, 1):
            # Saltar si ya tiene datos (a menos que estemos actualizando todo)
            if prod.package_size_g is not None and prod.package_price_eur is not None:
                stats["already"] += 1
                continue

            if idx % REPORT_EVERY == 0:
                print(f"  [{idx}/{len(to_update)}] procesados…  ok={stats['ok']}  sin_tamaño={stats['no_size']}  error={stats['error']}")

            time.sleep(DELAY)
            try:
                r = client.get(f"{MERCADONA_BASE}/products/{mid}/")
                if r.status_code != 200:
                    stats["error"] += 1
                    continue
                pi = r.json().get("price_instructions", {})
            except Exception:
                stats["error"] += 1
                continue

            unit_size   = pi.get("unit_size")
            unit_price  = pi.get("unit_price")
            size_format = (pi.get("size_format") or "").lower()

            pkg_g = _size_to_grams(unit_size, size_format)
            try:
                pkg_eur = round(float(unit_price), 2) if unit_price is not None else None
            except (ValueError, TypeError):
                pkg_eur = None

            if pkg_g is None:
                stats["no_size"] += 1
                continue

            stats["ok"] += 1
            if len(examples) < 8:
                examples.append((prod.name, pkg_g, pkg_eur, size_format))

            if not dry_run:
                prod.package_size_g    = pkg_g
                prod.package_price_eur = pkg_eur

        if not dry_run:
            db.commit()

        prefix = "[DRY-RUN] " if dry_run else ""
        print()
        print(f"{prefix}═══ Resultados ═══")
        print(f"  Actualizados (pkg_g + pkg_eur):  {stats['ok']}")
        print(f"  Sin tamaño convertible (ud/dz):  {stats['no_size']}")
        print(f"  Ya tenían datos (skip):          {stats['already']}")
        print(f"  Errores HTTP:                    {stats['error']}")
        print()
        print("Ejemplos de envases:")
        print(f"  {'Producto':<50}  {'Envase':>8}  {'Precio':>7}")
        print("  " + "─" * 68)
        for name, g, eur, fmt in examples:
            eur_s = f"{eur:.2f}€" if eur is not None else "?"
            print(f"  {name[:50]:<50}  {g:>6.0f}g  {eur_s:>7}")

    finally:
        db.close()
        client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
