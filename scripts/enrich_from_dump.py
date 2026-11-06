"""
Enriquece ProductPendingORM usando el dump CSV de OpenFoodFacts (sin API).

Flujo:
  1. Carga los EANs de ProductPendingORM accionables en memoria (set pequeño).
  2. Descarga el dump CSV de OpenFoodFacts en streaming (gzip line-by-line).
     · Intenta primero el dump filtrado para España (~300MB comprimido).
     · Si no existe, usa el dump mundial (~9GB) filtrando por countries_tags.
  3. Para cada fila del dump cuyo EAN coincide, extrae macros.
  4. Valida rangos nutricionales (misma lógica que el scraper).
  5. Mueve los productos válidos a ProductORM; actualiza reason en los inválidos.
  6. Imprime estadísticas de cobertura antes/después.

Uso:
    python scripts/enrich_from_dump.py            # ejecuta
    python scripts/enrich_from_dump.py --dry-run  # solo muestra qué haría
    python scripts/enrich_from_dump.py --dump-path data/spain.csv.gz  # archivo local
"""

import argparse
import csv
import gzip
import io
import os
import sys
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Iterator

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv()

from app.db.session import SessionLocal
from app.models.diet import ProductORM, ProductPendingORM
from app.scraper.mercadona import _validate_macros

# ─────────────────────────────────────────────
# Configuración
# ─────────────────────────────────────────────

# Intentamos primero el dump filtrado por España (mucho más pequeño).
# Dump por España: no existe en OFF (verificado 2026-04-11).
# El dump mundial CSV comprimido son ~1.16 GB (descomprimido ~9 GB).
DUMP_URL_SPAIN  = "https://static.openfoodfacts.org/data/exports/products_by_country/en:spain.csv.gz"
DUMP_URL_WORLD  = "https://static.openfoodfacts.org/data/en.openfoodfacts.org.products.csv.gz"

# Razones que NO vale la pena reintentar (sin EAN o precio incompatible)
_SKIP_REASONS = {"no_ean", "price_not_per_kg"}

# Columnas mínimas que necesitamos del dump de OFF (nombres exactos del CSV)
_NEEDED_COLS = {
    "code",
    "energy-kcal_100g",
    "proteins_100g",
    "fat_100g",
    "carbohydrates_100g",
    "countries_tags",
}

# max_grams_per_day por categoría (igual que normalizer.py / fix_max_grams.py)
_MAX_GRAMS: dict[str, float] = {
    "proteina":     300.0,
    "legumbre":     200.0,
    "carbohidrato": 250.0,
    "verdura":      400.0,
    "fruta":        300.0,
    "lacteo":       400.0,
    "grasa":         40.0,
}


# ─────────────────────────────────────────────
# Verificación del dump de España
# ─────────────────────────────────────────────

def _spain_dump_exists() -> bool:
    """HEAD request para verificar si el dump de España existe."""
    try:
        req = urllib.request.Request(DUMP_URL_SPAIN, method="HEAD")
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status == 200
    except Exception:
        return False


# ─────────────────────────────────────────────
# Streaming del dump CSV (gzip)
# ─────────────────────────────────────────────

def _open_gzip_stream(source: str) -> gzip.GzipFile:
    """
    Abre una fuente (URL o ruta local) como stream gzip.
    Devuelve un objeto file-like de bytes descomprimidos.
    """
    if os.path.isfile(source):
        return gzip.open(source, "rb")
    print(f"  Descargando {source} ...")
    response = urllib.request.urlopen(source, timeout=60)
    return gzip.GzipFile(fileobj=response)


def _iter_off_rows(
    source: str,
    target_eans: set[str],
) -> Iterator[dict]:
    """
    Itera el dump CSV de OFF en streaming y devuelve solo las filas
    cuyo `code` está en target_eans.

    No filtramos por país: los EANs de Mercadona (prefijo 84) no siempre
    tienen el tag en:spain en OFF. El cruce exacto por EAN es suficiente.

    El CSV de OFF usa tabulador como separador.
    """
    gz = _open_gzip_stream(source)
    csv.field_size_limit(10_000_000)  # algunos campos OFF son muy grandes
    reader = csv.DictReader(
        io.TextIOWrapper(gz, encoding="utf-8", errors="replace"),
        delimiter="\t",
    )

    rows_scanned = 0
    found = 0
    report_every = 250_000

    for row in reader:
        rows_scanned += 1
        if rows_scanned % report_every == 0:
            print(f"    … {rows_scanned:,} filas escaneadas, {found} coincidencias hasta ahora")

        ean = (row.get("code") or "").strip()
        if not ean or ean not in target_eans:
            continue

        # No filtramos por país: los EANs de Mercadona (84xxxxxxxx) no siempre
        # tienen el tag en:spain en OFF. El cruce por EAN es suficiente.
        found += 1
        yield row

    print(f"    Escaneo completo: {rows_scanned:,} filas totales, {found} EANs coincidentes.")
    gz.close()


# ─────────────────────────────────────────────
# Extracción de macros de una fila del dump
# ─────────────────────────────────────────────

def _extract_macros(row: dict) -> dict | None:
    """
    Extrae macros de una fila del dump. Devuelve None si faltan campos.
    """
    def _f(key: str) -> float | None:
        v = (row.get(key) or "").strip()
        if not v:
            return None
        try:
            return float(v)
        except ValueError:
            return None

    kcal  = _f("energy-kcal_100g")
    prot  = _f("proteins_100g")
    fat   = _f("fat_100g")
    carbs = _f("carbohydrates_100g")

    if any(v is None for v in (kcal, prot, fat, carbs)):
        return None

    return {
        "kcal_per_100g":    kcal,
        "protein_per_100g": prot,
        "fat_per_100g":     fat,
        "carbs_per_100g":   carbs,
    }


# ─────────────────────────────────────────────
# Estadísticas de cobertura
# ─────────────────────────────────────────────

def _print_coverage(db) -> None:
    ready   = db.query(ProductORM).count()
    pending = db.query(ProductPendingORM).count()
    print(f"  ProductORM (listos):   {ready}")
    print(f"  ProductPendingORM:     {pending}")

    by_cat = Counter(
        p.category for p in db.query(ProductORM).all()
    )
    print("  Distribución por categoría (ProductORM):")
    for cat, n in sorted(by_cat.items(), key=lambda x: -x[1]):
        print(f"    {cat:<15} {n:>4}")


# ─────────────────────────────────────────────
# Script principal
# ─────────────────────────────────────────────

def main(dry_run: bool, dump_path: str | None) -> None:
    db = SessionLocal()

    try:
        # ── 1. Cargar productos pendientes accionables ──────────────────
        pending_all = db.query(ProductPendingORM).all()
        actionable  = [
            p for p in pending_all
            if p.reason not in _SKIP_REASONS and p.ean
        ]

        print(f"Estado inicial:")
        _print_coverage(db)
        print()

        by_reason_before = Counter(p.reason for p in actionable)
        print(f"Pendientes accionables (con EAN, reason != no_ean/price_not_per_kg): {len(actionable)}")
        for r, n in sorted(by_reason_before.items(), key=lambda x: -x[1]):
            print(f"  {r:<22} {n}")
        print()

        if not actionable:
            print("Nada que enriquecer.")
            return

        # EAN → lista de productos pendientes (puede haber varios con el mismo EAN)
        ean_to_pending: dict[str, list[ProductPendingORM]] = defaultdict(list)
        for p in actionable:
            ean_to_pending[p.ean].append(p)
        target_eans: set[str] = set(ean_to_pending.keys())
        print(f"EANs únicos a buscar: {len(target_eans)}")

        # Nombres ya en ProductORM para evitar duplicados
        existing_names: set[str] = {
            row.name for row in db.query(ProductORM).all()
        }

        # ── 2. Elegir fuente del dump ────────────────────────────────────
        if dump_path:
            source = dump_path
            print(f"Usando dump local: {dump_path}")
        else:
            print("Verificando si existe el dump filtrado para España...")
            if _spain_dump_exists():
                source = DUMP_URL_SPAIN
                print(f"  → Usando dump de España: {DUMP_URL_SPAIN}")
            else:
                source = DUMP_URL_WORLD
                print(f"  → Dump de España no encontrado. Usando dump mundial (~1.16 GB comprimido).")
        print()

        # ── 3. Escanear dump y recoger macros ───────────────────────────
        print("Escaneando dump CSV de OpenFoodFacts (cruce por EAN, sin filtro de país)...")
        # ean → mejor fila de macros encontrada (tomamos la primera que tenga todo)
        ean_macros: dict[str, dict] = {}

        for row in _iter_off_rows(source, target_eans):
            ean = row.get("code", "").strip()
            if ean in ean_macros:
                continue  # ya tenemos macros para este EAN
            macros = _extract_macros(row)
            if macros is not None:
                ean_macros[ean] = macros

        print(f"\nEANs con macros completos en el dump: {len(ean_macros)} / {len(target_eans)}")
        print()

        # ── 4. Procesar matches ─────────────────────────────────────────
        stats = Counter()

        for ean, macros in ean_macros.items():
            for pending in ean_to_pending[ean]:
                cat = pending.internal_category
                if cat is None:
                    stats["skip_no_category"] += 1
                    continue

                if not _validate_macros(cat, macros):
                    stats["invalid_macros"] += 1
                    if not dry_run:
                        pending.reason = "invalid_macros"
                    continue

                if pending.price_per_100g is None:
                    stats["skip_no_price"] += 1
                    continue

                # Evitar duplicados por nombre
                if pending.name in existing_names:
                    stats["skip_duplicate_name"] += 1
                    continue

                stats["promoted"] += 1
                print(
                    f"  ✓ [{pending.reason}→OK]  {pending.name[:50]:<50}"
                    f"  {cat:<12}  kcal={macros['kcal_per_100g']:.0f}"
                )

                if not dry_run:
                    max_g = _MAX_GRAMS.get(cat, 300.0)
                    db.add(ProductORM(
                        name=pending.name,
                        category=cat,
                        price_per_100g=pending.price_per_100g,
                        kcal_per_100g=macros["kcal_per_100g"],
                        protein_per_100g=macros["protein_per_100g"],
                        fat_per_100g=macros["fat_per_100g"],
                        carbs_per_100g=macros["carbs_per_100g"],
                        max_grams_per_day=max_g,
                        ean=ean,
                        source="off_dump",
                        scraped_at=datetime.now(timezone.utc),
                    ))
                    existing_names.add(pending.name)
                    db.delete(pending)

        # EANs buscados pero no encontrados en el dump
        not_found_in_dump = target_eans - set(ean_macros.keys())
        stats["not_in_dump"] = len(not_found_in_dump)

        if not dry_run:
            db.commit()

        # ── 5. Resumen ───────────────────────────────────────────────────
        prefix = "[DRY-RUN] " if dry_run else ""
        print()
        print(f"{prefix}═══ Resultados ═══")
        print(f"  Promovidos a ProductORM:  {stats['promoted']}")
        print(f"  Macros inválidos:         {stats['invalid_macros']}")
        print(f"  Sin precio (skip):        {stats['skip_no_price']}")
        print(f"  Sin categoría (skip):     {stats['skip_no_category']}")
        print(f"  Nombre duplicado (skip):  {stats['skip_duplicate_name']}")
        print(f"  EAN no encontrado dump:   {stats['not_in_dump']}")
        print()

        if not dry_run:
            print(f"Estado final:")
            _print_coverage(db)

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enriquecer ProductPendingORM desde dump OFF")
    parser.add_argument("--dry-run", action="store_true", help="Solo muestra qué haría, sin modificar BD")
    parser.add_argument(
        "--dump-path",
        default=None,
        help="Ruta a un archivo .csv.gz local (evita la descarga). Ej: data/spain.csv.gz",
    )
    args = parser.parse_args()
    main(dry_run=args.dry_run, dump_path=args.dump_path)
