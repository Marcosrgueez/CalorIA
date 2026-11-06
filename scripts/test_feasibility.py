"""
scripts/test_feasibility.py

Diagnóstico de infeasibilidad del motor de recetas.
Prueba una matriz de (kcal_target × budget × protein) y reporta
qué combinaciones fallan y por qué.
"""

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from app.db.session import SessionLocal
from app.engine.diet_engine import UserProfile, generate_diet_from_recipes
from app.engine.recipes import build_recipe_lp_data

# ─────────────────────────────────────────────
# Parámetros de la matriz
# ─────────────────────────────────────────────
KCAL_TARGETS   = [1600, 1800, 2000, 2200, 2500, 2800]
BUDGETS        = [3.0, 4.0, 5.0, 7.0]
PROTEIN_TARGETS = [60, 100, 140, 180]

# Resto de restricciones fijas (razonables, no ultrarrestrictivas)
MAX_FAT_G    = 100.0
MIN_CARBS_G  = 100.0
MAX_CARBS_G  = 500.0

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _cheapest_feasible_cost(db, kcal_target: float) -> dict[str, float]:
    """
    Devuelve el coste mínimo alcanzable por tipo de comida
    (receta más barata disponible de cada tipo).
    """
    recipe_data = build_recipe_lp_data(db, kcal_target)
    result = {}
    for mt, rds in recipe_data.items():
        if rds:
            result[mt] = min(rd.scaled_cost for rd in rds)
        else:
            result[mt] = float("inf")
    return result


def _max_protein_achievable(db, kcal_target: float) -> dict[str, float]:
    """
    Devuelve la proteína máxima alcanzable por tipo de comida
    (receta con más proteína de cada tipo).
    """
    recipe_data = build_recipe_lp_data(db, kcal_target)
    result = {}
    for mt, rds in recipe_data.items():
        if rds:
            result[mt] = max(rd.scaled_protein for rd in rds)
        else:
            result[mt] = 0.0
    return result


def _diagnose_infeasibility(
    budget: float,
    protein: float,
    kcal_target: float,
    min_costs: dict[str, float],
    max_proteins: dict[str, float],
) -> list[str]:
    """
    Heurística para identificar por qué falla una combinación.
    Devuelve lista de razones legibles.
    """
    reasons = []
    min_total_cost = sum(min_costs.values())
    if min_total_cost > budget:
        reasons.append(
            f"presupuesto insuficiente: mín={min_total_cost:.2f}€ > {budget:.2f}€"
        )
    max_total_protein = sum(max_proteins.values())
    if max_total_protein < protein:
        reasons.append(
            f"proteína inalcanzable: máx={max_total_protein:.0f}g < {protein:.0f}g"
        )
    return reasons if reasons else ["restricciones combinadas (kcal/fat/carbs)"]


# ─────────────────────────────────────────────
# Ejecución
# ─────────────────────────────────────────────

db = SessionLocal()
try:
    # Pre-calcular costes mínimos y proteínas máximas por kcal_target
    # (evita recalcular en cada iteración del mismo kcal_target)
    cached_costs: dict[float, dict[str, float]] = {}
    cached_proteins: dict[float, dict[str, float]] = {}
    for kcal in KCAL_TARGETS:
        cached_costs[kcal]   = _cheapest_feasible_cost(db, kcal)
        cached_proteins[kcal] = _max_protein_achievable(db, kcal)

    # Mostrar límites por kcal_target (informativo)
    W = 80
    print(f"\n{'═'*W}")
    print(f"  LÍMITES POR OBJETIVO CALÓRICO")
    print(f"{'═'*W}")
    print(f"  {'kcal':>6}  {'coste_min':>10}  {'prot_max_D':>10}  {'prot_max_C':>10}  {'prot_max_N':>10}  {'prot_total':>10}")
    print(f"  {'─'*72}")
    for kcal in KCAL_TARGETS:
        c = cached_costs[kcal]
        p = cached_proteins[kcal]
        total_p = sum(p.values())
        total_c = sum(c.values())
        print(
            f"  {kcal:>6}  {total_c:>10.2f}€"
            f"  {p.get('desayuno',0):>10.1f}g"
            f"  {p.get('comida',0):>10.1f}g"
            f"  {p.get('cena',0):>10.1f}g"
            f"  {total_p:>10.1f}g"
        )

    # Ejecutar la matriz completa
    results = []
    total = len(KCAL_TARGETS) * len(BUDGETS) * len(PROTEIN_TARGETS)
    done = 0

    print(f"\n{'═'*W}")
    print(f"  MATRIZ DE FACTIBILIDAD  ({total} combinaciones)")
    print(f"{'═'*W}")

    for kcal in KCAL_TARGETS:
        for budget in BUDGETS:
            for protein in PROTEIN_TARGETS:
                user = UserProfile(
                    name=f"test_{kcal}_{budget}_{protein}",
                    kcal_target=kcal,
                    min_protein_g=protein,
                    max_fat_g=MAX_FAT_G,
                    min_carbs_g=MIN_CARBS_G,
                    max_carbs_g=MAX_CARBS_G,
                    budget_eur=budget,
                )
                result = generate_diet_from_recipes(user, db)
                feasible = result.status == "optimal"
                reasons = []
                if not feasible:
                    reasons = _diagnose_infeasibility(
                        budget, protein, kcal,
                        cached_costs[kcal],
                        cached_proteins[kcal],
                    )
                results.append({
                    "kcal": kcal,
                    "budget": budget,
                    "protein": protein,
                    "feasible": feasible,
                    "reasons": reasons,
                    "actual_cost": result.total_cost,
                    "actual_protein": result.total_protein,
                })
                done += 1
                mark = "✓" if feasible else "✗"
                print(f"  [{done:>3}/{total}] {mark}  {kcal} kcal  {budget:.1f}€  {protein}g prot", end="")
                if not feasible:
                    print(f"  ← {'; '.join(reasons)}", end="")
                print()

    # ── Resumen ───────────────────────────────────────────────────────────
    infeasible = [r for r in results if not r["feasible"]]
    feasible_ok = [r for r in results if r["feasible"]]

    print(f"\n{'═'*W}")
    print(f"  RESUMEN")
    print(f"{'═'*W}")
    print(f"  Total:      {total}")
    print(f"  Feasibles:  {len(feasible_ok)}")
    print(f"  Infeasibles:{len(infeasible)}")

    if infeasible:
        print(f"\n  COMBINACIONES INFEASIBLES:")
        print(f"  {'kcal':>6}  {'budget':>7}  {'protein':>8}  RAZÓN")
        print(f"  {'─'*68}")
        for r in infeasible:
            print(
                f"  {r['kcal']:>6}  {r['budget']:>7.1f}€  {r['protein']:>7}g  "
                f"{'; '.join(r['reasons'])}"
            )

        # Agrupar por razón principal
        budget_failures  = [r for r in infeasible if any("presupuesto" in x for x in r["reasons"])]
        protein_failures = [r for r in infeasible if any("proteína"    in x for x in r["reasons"])]
        other_failures   = [r for r in infeasible if not any(
            "presupuesto" in x or "proteína" in x for x in r["reasons"]
        )]
        print(f"\n  Por causa:")
        print(f"    Presupuesto insuficiente : {len(budget_failures)}")
        print(f"    Proteína inalcanzable    : {len(protein_failures)}")
        print(f"    Otras restricciones      : {len(other_failures)}")

        # Umbrales mínimos de budget por kcal_target
        print(f"\n  PRESUPUESTO MÍNIMO VIABLE POR OBJETIVO CALÓRICO:")
        for kcal in KCAL_TARGETS:
            min_cost = sum(cached_costs[kcal].values())
            print(f"    {kcal} kcal → mín {min_cost:.2f}€/día")

        # Proteína máxima alcanzable por kcal_target
        print(f"\n  PROTEÍNA MÁXIMA ALCANZABLE POR OBJETIVO CALÓRICO:")
        for kcal in KCAL_TARGETS:
            max_p = sum(cached_proteins[kcal].values())
            print(f"    {kcal} kcal → máx {max_p:.0f}g proteína/día")

    print(f"\n{'═'*W}\n")

finally:
    db.close()
