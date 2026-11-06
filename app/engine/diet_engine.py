"""
Motor de Recomendación de Dietas — v2.0
========================================
Optimización por Programación Lineal (PuLP).

Mejoras sobre v1.0:
  · Restricciones por categoría de alimento (mínimos y máximos diarios)
  · Distribución de ingredientes en comidas (desayuno / comida / cena)
  · Cierre del perfil macro con restricciones de carbohidratos

Formulación LP:
    Variables: x[i,m] = gramos del producto i en la comida m  (≥0, continua)
    Objetivo:  minimizar  Σ_i Σ_m price[i] · x[i,m]
    Restricciones: ver docstring de generate_diet()
"""

import copy
import random
from dataclasses import dataclass, field
from typing import Optional

import pulp

try:
    import cvxpy as cp   # type: ignore
    import numpy as np   # type: ignore
    _CVXPY_AVAILABLE = True
except ImportError:
    _CVXPY_AVAILABLE = False


# ─────────────────────────────────────────────
# 1. ESTRUCTURAS DE DATOS
# ─────────────────────────────────────────────

@dataclass
class Product:
    """Producto de supermercado. Valores nutricionales por 100g."""
    name: str
    category: str           # proteina | legumbre | carbohidrato | verdura | fruta | lacteo | grasa
    price_per_100g: float   # €/100g
    kcal_per_100g: float
    protein_per_100g: float
    fat_per_100g: float
    carbs_per_100g: float
    max_grams_per_day: float = 500.0
    min_grams_per_day: float = 0.0

    @property
    def price_per_gram(self) -> float:
        return self.price_per_100g / 100

    @property
    def kcal_per_gram(self) -> float:
        return self.kcal_per_100g / 100

    @property
    def protein_per_gram(self) -> float:
        return self.protein_per_100g / 100

    @property
    def fat_per_gram(self) -> float:
        return self.fat_per_100g / 100

    @property
    def carbs_per_gram(self) -> float:
        return self.carbs_per_100g / 100


@dataclass
class CategoryConstraint:
    """Restricción de gramos totales diarios para una categoría de alimento."""
    min_grams: float = 0.0
    max_grams: float = 9999.0


# Límites razonables por categoría para una dieta mediterránea.
# proteina y carbohidrato no tienen max_grams aquí: sus macros ya los acotan
# las restricciones min_carbs_g/max_carbs_g y min_protein_g/max_fat_g de UserProfile.
DEFAULT_CATEGORY_CONSTRAINTS: dict[str, CategoryConstraint] = {
    "proteina":     CategoryConstraint(min_grams=100.0, max_grams=9999.0),
    "legumbre":     CategoryConstraint(min_grams=0.0,   max_grams=300.0),
    "carbohidrato": CategoryConstraint(min_grams=100.0, max_grams=9999.0),
    "verdura":      CategoryConstraint(min_grams=150.0, max_grams=700.0),
    "fruta":        CategoryConstraint(min_grams=0.0,   max_grams=300.0),
    "lacteo":       CategoryConstraint(min_grams=0.0,   max_grams=500.0),
    "grasa":        CategoryConstraint(min_grams=5.0,   max_grams=50.0),
}


@dataclass
class MealConfig:
    """Proporciones calóricas y restricciones de categoría para una ingesta."""
    name: str                                      # "desayuno" | "comida" | "cena"
    kcal_fraction: float                           # fracción del total calórico diario
    kcal_tolerance: float = 0.10                   # ±% de tolerancia calórica por comida
    allowed_categories: Optional[set[str]] = None  # None → sin restricción por categoría
    category_min_grams: dict[str, float] = field(default_factory=dict)
    # Post-procesado: límites aplicados DESPUÉS del solver para legibilidad humana
    max_products: int = 6                          # máx. productos distintos en esta comida
    max_per_category: dict[str, int] = field(default_factory=dict)  # máx. por categoría (ej. {"proteina": 1})


DEFAULT_MEALS: list[MealConfig] = [
    MealConfig(
        name="desayuno",
        kcal_fraction=0.25,
        kcal_tolerance=0.15,   # más amplio: el post-procesado elimina productos y reduce kcal
        # legumbre queda fuera → no hay lentejas en el desayuno
        allowed_categories={"lacteo", "carbohidrato", "grasa", "proteina", "fruta"},
        category_min_grams={"carbohidrato": 40.0},
        max_products=3,
        max_per_category={"carbohidrato": 1, "proteina": 1, "lacteo": 1},
    ),
    MealConfig(
        name="comida",
        kcal_fraction=0.40,
        kcal_tolerance=0.12,
        # Lacteo y fruta quedan fuera de la comida principal
        allowed_categories={"proteina", "legumbre", "carbohidrato", "verdura", "grasa"},
        category_min_grams={"proteina": 80.0, "verdura": 100.0},
        max_products=4,
        max_per_category={"proteina": 1, "carbohidrato": 1, "legumbre": 1},
    ),
    MealConfig(
        name="cena",
        kcal_fraction=0.35,
        kcal_tolerance=0.15,
        # Igual que comida pero se permite lacteo (yogur, queso) y se limita carbohidrato
        allowed_categories={"proteina", "legumbre", "carbohidrato", "verdura", "grasa", "lacteo"},
        category_min_grams={"proteina": 60.0, "verdura": 80.0},
        max_products=3,
        max_per_category={"proteina": 1, "carbohidrato": 1},
    ),
]


@dataclass
class UserProfile:
    """
    Perfil nutricional del usuario.
    Las calorías objetivo se calculan externamente (ej: Harris-Benedict).
    """
    name: str
    kcal_target: float
    kcal_tolerance: float = 0.05
    min_protein_g: float = 50.0
    max_fat_g: float = 80.0
    budget_eur: float = 5.0
    min_carbs_g: float = 100.0
    max_carbs_g: float = 350.0
    max_kcal_fraction_per_product: float = 0.25  # ningún producto puede superar este % del total de kcal
    min_portion_g: float = 30.0  # gramos mínimos por producto por comida; 0 = LP puro (sin variables binarias)
    diversity_weight: float = 0.5  # λ para penalización de diversidad en QP; 0 = solo coste
    noise_factor: float = 0.0     # ±% de perturbación aleatoria sobre costes (variabilidad); 0 = determinista
    category_constraints: dict[str, CategoryConstraint] = field(
        default_factory=lambda: copy.deepcopy(DEFAULT_CATEGORY_CONSTRAINTS)
    )
    meals: list[MealConfig] = field(
        default_factory=lambda: copy.deepcopy(DEFAULT_MEALS)
    )


@dataclass
class DietResult:
    """Resultado del proceso de optimización."""
    status: str
    user: UserProfile
    quantities: dict[str, float]            # producto → gramos totales diarios
    meal_plan: dict[str, dict[str, float]]  # comida → {producto: gramos}
    total_cost: float
    total_kcal: float
    total_protein: float
    total_fat: float
    total_carbs: float
    solver_message: str = ""
    products_ref: dict[str, "Product"] = field(default_factory=dict, repr=False)
    # Nombre real de la receta seleccionada por comida (solo motor de recetas)
    recipe_names_by_meal: dict[str, str] = field(default_factory=dict, repr=False)
    # Proteína principal de cada comida (para rastrear variedad semanal)
    proteins_by_meal: dict[str, str] = field(default_factory=dict, repr=False)
    # Objeto Recipe seleccionado por comida (instrucciones, prep_time_min)
    recipes_by_meal: dict = field(default_factory=dict, repr=False)

    def summary(self) -> str:
        W = 57
        lines = [
            f"\n{'═'*W}",
            f"  DIETA GENERADA PARA: {self.user.name.upper()}",
            f"{'═'*W}",
            f"  Estado : {self.status.upper()}",
        ]

        if self.status != "optimal":
            lines += [
                f"{'─'*W}",
                f"  Sin solución factible.  {self.solver_message}",
                f"{'═'*W}\n",
            ]
            return "\n".join(lines)

        lines += [
            f"{'─'*W}",
            f"  MACROS DIARIOS",
            f"{'─'*W}",
            f"  Coste        : {self.total_cost:.2f}€  (máx {self.user.budget_eur:.2f}€)",
            f"  Calorías     : {self.total_kcal:.0f} kcal"
            f"  (obj {self.user.kcal_target:.0f} ±{self.user.kcal_tolerance*100:.0f}%)",
            f"  Proteínas    : {self.total_protein:.1f}g  (mín {self.user.min_protein_g:.0f}g)",
            f"  Grasas       : {self.total_fat:.1f}g  (máx {self.user.max_fat_g:.0f}g)",
            f"  Carbohidratos: {self.total_carbs:.1f}g"
            f"  ({self.user.min_carbs_g:.0f}–{self.user.max_carbs_g:.0f}g)",
        ]

        for meal_cfg in self.user.meals:
            items = {
                name: grams
                for name, grams in self.meal_plan.get(meal_cfg.name, {}).items()
                if grams > 0.5
            }
            if not items:
                continue

            meal_kcal = sum(
                self.products_ref[n].kcal_per_gram * g
                for n, g in items.items()
                if n in self.products_ref
            )
            meal_cost = sum(
                self.products_ref[n].price_per_gram * g
                for n, g in items.items()
                if n in self.products_ref
            )
            lines += [
                f"{'─'*W}",
                f"  {meal_cfg.name.upper()}"
                f"  ·  {meal_kcal:.0f} kcal"
                f"  ({int(meal_cfg.kcal_fraction * 100)}% obj)"
                f"  ·  {meal_cost:.2f}€",
                f"  {'PRODUCTO':<28} {'GRAMOS':>7}  {'KCAL':>5}  {'COSTE':>6}",
                f"  {'─'*44}",
            ]
            for name, grams in sorted(items.items(), key=lambda x: -x[1]):
                p = self.products_ref.get(name)
                if p is None:
                    continue
                lines.append(
                    f"  {name:<28} {grams:>6.0f}g"
                    f"  {p.kcal_per_gram * grams:>4.0f}"
                    f"  {p.price_per_gram * grams:>5.2f}€"
                )

        lines.append(f"{'═'*W}\n")
        return "\n".join(lines)


# ─────────────────────────────────────────────
# 2. DATOS DE EJEMPLO (MOCK DATA)
# ─────────────────────────────────────────────
# Precios y macros aproximados de productos reales
# en supermercados españoles (€/100g, valores por 100g)

SAMPLE_PRODUCTS: list[Product] = [
    # Proteínas
    Product(
        name="Pechuga de pollo",
        category="proteina",
        price_per_100g=0.60,
        kcal_per_100g=110,
        protein_per_100g=23.0,
        fat_per_100g=1.5,
        carbs_per_100g=0.0,
        max_grams_per_day=400,
    ),
    Product(
        name="Huevos (pieza ~50g)",
        category="proteina",
        price_per_100g=0.25,
        kcal_per_100g=155,
        protein_per_100g=13.0,
        fat_per_100g=11.0,
        carbs_per_100g=1.1,
        max_grams_per_day=300,  # ~6 huevos máx
    ),
    Product(
        name="Atún en lata (escurrido)",
        category="proteina",
        price_per_100g=0.55,
        kcal_per_100g=116,
        protein_per_100g=26.0,
        fat_per_100g=1.0,
        carbs_per_100g=0.0,
        max_grams_per_day=200,
    ),
    Product(
        name="Lentejas cocidas",
        category="proteina",
        price_per_100g=0.12,
        kcal_per_100g=116,
        protein_per_100g=9.0,
        fat_per_100g=0.4,
        carbs_per_100g=20.0,
        max_grams_per_day=400,
    ),
    # Carbohidratos
    Product(
        name="Arroz blanco cocido",
        category="carbohidrato",
        price_per_100g=0.08,
        kcal_per_100g=130,
        protein_per_100g=2.7,
        fat_per_100g=0.3,
        carbs_per_100g=28.0,
        max_grams_per_day=500,
    ),
    Product(
        name="Pan integral",
        category="carbohidrato",
        price_per_100g=0.22,
        kcal_per_100g=247,
        protein_per_100g=9.0,
        fat_per_100g=3.5,
        carbs_per_100g=41.0,
        max_grams_per_day=200,
    ),
    Product(
        name="Pasta cocida",
        category="carbohidrato",
        price_per_100g=0.09,
        kcal_per_100g=158,
        protein_per_100g=5.8,
        fat_per_100g=0.9,
        carbs_per_100g=31.0,
        max_grams_per_day=400,
    ),
    # Verduras
    Product(
        name="Espinacas frescas",
        category="verdura",
        price_per_100g=0.18,
        kcal_per_100g=23,
        protein_per_100g=2.9,
        fat_per_100g=0.4,
        carbs_per_100g=1.4,
        max_grams_per_day=300,
    ),
    Product(
        name="Tomate",
        category="verdura",
        price_per_100g=0.10,
        kcal_per_100g=18,
        protein_per_100g=0.9,
        fat_per_100g=0.2,
        carbs_per_100g=3.9,
        max_grams_per_day=400,
    ),
    # Grasas
    Product(
        name="Aceite de oliva",
        category="grasa",
        price_per_100g=0.55,
        kcal_per_100g=884,
        protein_per_100g=0.0,
        fat_per_100g=100.0,
        carbs_per_100g=0.0,
        max_grams_per_day=30,
    ),
    # Lácteos
    Product(
        name="Leche entera",
        category="lacteo",
        price_per_100g=0.07,
        kcal_per_100g=61,
        protein_per_100g=3.2,
        fat_per_100g=3.3,
        carbs_per_100g=4.8,
        max_grams_per_day=500,
    ),
]


# ─────────────────────────────────────────────
# 3. MOTOR DE OPTIMIZACIÓN
# ─────────────────────────────────────────────

def _sanitize(name: str) -> str:
    """Convierte un nombre de producto en un identificador válido para PuLP."""
    return "".join(c if c.isalnum() else "_" for c in name)


def _apply_cost_noise(products: list[Product], factor: float) -> list[Product]:
    """
    Devuelve copias con precio perturbado ±factor (distribución normal).
    Cambia qué productos elige el solver sin alterar los macros ni el catálogo.
    El factor recomendado es 0.03–0.08 (3–8 %).
    """
    noisy = []
    for p in products:
        perturbed = copy.copy(p)
        perturbed.price_per_100g = p.price_per_100g * max(0.4, 1.0 + random.gauss(0, factor))
        noisy.append(perturbed)
    return noisy


# Criterio de ordenación por categoría: qué macro priorizar al seleccionar el mejor producto.
# Si hay 2 fuentes de proteína y solo cabe 1, se queda la de mayor proteína aportada.
# Si hay 2 carbohidratos, se queda el de mayor carbohidrato aportado. Etc.
_CAT_SORT_KEY: dict[str, str] = {
    "proteina":     "protein",
    "legumbre":     "protein",
    "carbohidrato": "carbs",
    "verdura":      "kcal",     # verduras: priorizar volumen calórico (suelen ser bajas)
    "fruta":        "kcal",
    "grasa":        "kcal",
    "lacteo":       "kcal",
}


def _macro_score(p: "Product", grams: float, macro: str) -> float:
    if macro == "protein":
        return p.protein_per_gram * grams
    if macro == "carbs":
        return p.carbs_per_gram * grams
    return p.kcal_per_gram * grams   # "kcal" por defecto


def _prune_meal_plan(result: DietResult) -> DietResult:
    """
    Post-procesa el meal_plan del solver para producir comidas realistas:

      1. Elimina porciones por debajo del umbral mínimo (min_portion_g o 15 g).
      2. max_per_category: cuando hay varias fuentes de la misma categoría, conserva
         las K de mayor contribución al macro principal de esa categoría
         (proteína→proteína, carbohidrato→carbohidratos, resto→kcal).
      3. max_products global: de los que quedan, solo top-N por kcal aportada.
      4. Renormaliza: escala los gramos supervivientes para recuperar las kcal
         de la comida original que se perdieron al descartar productos.
      5. Deduplica la proteína entre comida y cena: si el mismo producto proteico
         aparece en ambas, se elimina de la que aporte menos proteína.

    Los macros post-poda se recalculan: pueden diferir ligeramente del resultado
    LP (efecto normal de simplificar la solución para legibilidad humana).
    """
    if result.status != "optimal":
        return result

    ref = result.products_ref
    MIN_G = max(result.user.min_portion_g, 15.0)

    new_meal_plan: dict[str, dict[str, float]] = {}

    for meal_cfg in result.user.meals:
        raw: dict[str, float] = result.meal_plan.get(meal_cfg.name, {})

        # 1. Umbral mínimo de gramos
        items: dict[str, float] = {n: g for n, g in raw.items() if g >= MIN_G}

        # 2. max_per_category — ordenar por el macro relevante de la categoría
        if meal_cfg.max_per_category:
            by_cat: dict[str, list[tuple[str, float]]] = {}
            for name, grams in items.items():
                p = ref.get(name)
                if p:
                    by_cat.setdefault(p.category, []).append((name, grams))

            allowed: set[str] = set()
            for cat, cat_items in by_cat.items():
                limit = meal_cfg.max_per_category.get(cat, len(cat_items))
                macro = _CAT_SORT_KEY.get(cat, "kcal")
                top = sorted(
                    cat_items,
                    key=lambda t, m=macro: _macro_score(ref[t[0]], t[1], m),
                    reverse=True,
                )
                allowed.update(name for name, _ in top[:limit])
            items = {n: g for n, g in items.items() if n in allowed}

        # 3. max_products global: top-N por kcal aportada
        if len(items) > meal_cfg.max_products:
            ranked = sorted(
                items.items(),
                key=lambda t: ref[t[0]].kcal_per_gram * t[1] if t[0] in ref else 0.0,
                reverse=True,
            )
            items = dict(ranked[: meal_cfg.max_products])

        # 4. Renormalizar: recuperar el total de kcal de la comida original (incluyendo
        #    las porciones pequeñas que fueron filtradas por el umbral mínimo).
        raw_kcal    = sum(ref[n].kcal_per_gram * g for n, g in raw.items()   if n in ref)
        pruned_kcal = sum(ref[n].kcal_per_gram * g for n, g in items.items() if n in ref)
        if pruned_kcal > 1.0 and raw_kcal > pruned_kcal * 1.05:
            scale = raw_kcal / pruned_kcal
            items = {
                n: min(g * scale, ref[n].max_grams_per_day)
                for n, g in items.items()
            }

        new_meal_plan[meal_cfg.name] = items

    # 5. Deduplicar proteína entre comida y cena
    comida_items = new_meal_plan.get("comida", {})
    cena_items   = new_meal_plan.get("cena",   {})
    shared = {
        n for n in comida_items.keys() & cena_items.keys()
        if ref.get(n) and ref[n].category == "proteina"
    }
    for name in shared:
        prot_comida = ref[name].protein_per_gram * comida_items[name]
        prot_cena   = ref[name].protein_per_gram * cena_items[name]
        if prot_comida >= prot_cena:
            cena_items.pop(name)
        else:
            comida_items.pop(name)

    # Recalcular totales
    all_q: dict[str, float] = {}
    for meal_items in new_meal_plan.values():
        for name, grams in meal_items.items():
            all_q[name] = all_q.get(name, 0.0) + grams

    return DietResult(
        status=result.status,
        user=result.user,
        quantities=all_q,
        meal_plan=new_meal_plan,
        total_cost=round(sum(ref[n].price_per_gram    * g for n, g in all_q.items() if n in ref), 3),
        total_kcal=round(sum(ref[n].kcal_per_gram     * g for n, g in all_q.items() if n in ref), 1),
        total_protein=round(sum(ref[n].protein_per_gram * g for n, g in all_q.items() if n in ref), 1),
        total_fat=round(sum(ref[n].fat_per_gram       * g for n, g in all_q.items() if n in ref), 1),
        total_carbs=round(sum(ref[n].carbs_per_gram    * g for n, g in all_q.items() if n in ref), 1),
        products_ref=ref,
        solver_message=result.solver_message + " [pruned]",
    )


def _generate_diet_qp(
    user: "UserProfile",
    products: list["Product"],
    verbose: bool = False,
) -> "DietResult | None":
    """
    QP con penalización de diversidad usando cvxpy/CLARABEL.

    Objetivo:
        minimize  Σ_i price[i]·x_daily[i]
                + λ · Σ_i (kcal[i]·x_daily[i] / kcal_target)²

    El término cuadrático penaliza que un único producto acapare una fracción
    alta del total calórico, forzando al solver a repartir más las cantidades.

    Devuelve DietResult si es óptimo, None si falla (→ fallback a PuLP MIP).
    """
    import cvxpy as cp   # noqa: F401 (ya comprobado en el import de módulo)
    import numpy as np

    n_p = len(products)
    n_m = len(user.meals)
    if n_p == 0:
        return None

    # ── Variables: x[i,j] = gramos del producto i en la comida j ─────────
    x = cp.Variable((n_p, n_m), nonneg=True)
    x_daily = cp.sum(x, axis=1)   # totales diarios por producto, shape (n_p,)

    # ── Índices por categoría ─────────────────────────────────────────────
    products_by_cat: dict[str, list[int]] = {}
    for i, p in enumerate(products):
        products_by_cat.setdefault(p.category, []).append(i)

    # ── Vectores de coeficientes nutricionales ────────────────────────────
    price_g = np.array([p.price_per_gram   for p in products])
    kcal_g  = np.array([p.kcal_per_gram    for p in products])
    prot_g  = np.array([p.protein_per_gram for p in products])
    fat_g   = np.array([p.fat_per_gram     for p in products])
    carbs_g = np.array([p.carbs_per_gram   for p in products])

    constraints: list = []

    # (J) Categorías bloqueadas por comida
    for i, p in enumerate(products):
        for j, m in enumerate(user.meals):
            if (m.allowed_categories is not None
                    and p.category not in m.allowed_categories):
                constraints.append(x[i, j] == 0)

    # (A) Bounds diarios por producto
    for i, p in enumerate(products):
        constraints.append(x_daily[i] <= p.max_grams_per_day)
        if p.min_grams_per_day > 0:
            constraints.append(x_daily[i] >= p.min_grams_per_day)

    # (B) Calorías diarias
    kcal_total = kcal_g @ x_daily
    constraints.append(kcal_total >= user.kcal_target * (1 - user.kcal_tolerance))
    constraints.append(kcal_total <= user.kcal_target * (1 + user.kcal_tolerance))

    # (C) Proteína mínima
    constraints.append(prot_g @ x_daily >= user.min_protein_g)

    # (D) Grasa máxima
    constraints.append(fat_g @ x_daily <= user.max_fat_g)

    # (E) Carbohidratos
    carbs_total = carbs_g @ x_daily
    constraints.append(carbs_total >= user.min_carbs_g)
    constraints.append(carbs_total <= user.max_carbs_g)

    # (F) Presupuesto
    constraints.append(price_g @ x_daily <= user.budget_eur)

    # (G) Restricciones diarias por categoría
    for cat, constraint in user.category_constraints.items():
        idxs = np.array(products_by_cat.get(cat, []), dtype=int)
        if len(idxs) == 0:
            continue
        cat_total = cp.sum(x_daily[idxs])
        if constraint.min_grams > 0:
            constraints.append(cat_total >= constraint.min_grams)
        if constraint.max_grams < 9999.0:
            constraints.append(cat_total <= constraint.max_grams)

    # (H) Calorías por comida  +  (I) Mínimos de categoría por comida
    for j, m in enumerate(user.meals):
        meal_kcal   = kcal_g @ x[:, j]
        meal_target = user.kcal_target * m.kcal_fraction
        constraints.append(meal_kcal >= meal_target * (1 - m.kcal_tolerance))
        constraints.append(meal_kcal <= meal_target * (1 + m.kcal_tolerance))

        for cat, min_g in m.category_min_grams.items():
            eligible = np.array(
                [
                    i for i, p in enumerate(products)
                    if p.category == cat
                    and (m.allowed_categories is None
                         or p.category in m.allowed_categories)
                ],
                dtype=int,
            )
            if len(eligible) > 0:
                constraints.append(cp.sum(x[eligible, j]) >= min_g)

    # (K) Límite calórico por producto
    if user.max_kcal_fraction_per_product < 1.0:
        kcal_cap = user.kcal_target * user.max_kcal_fraction_per_product
        for i in range(n_p):
            constraints.append(kcal_g[i] * x_daily[i] <= kcal_cap)

    # ── Objetivo: coste  +  λ · penalización de diversidad ───────────────
    # diversity_penalty = Σ_i (kcal[i]·x_daily[i] / kcal_target)²
    #   → penaliza que cualquier producto acapare muchas kcal del total.
    cost_term      = price_g @ x_daily
    kcal_frac      = kcal_g / user.kcal_target   # fracción calórica por gramo
    diversity_term = cp.sum_squares(cp.multiply(kcal_frac, x_daily))
    objective      = cp.Minimize(cost_term + user.diversity_weight * diversity_term)

    prob = cp.Problem(objective, constraints)

    try:
        prob.solve(solver=cp.CLARABEL, verbose=verbose)
    except Exception:
        try:
            prob.solve(solver=cp.SCS, verbose=verbose)
        except Exception:
            return None

    if prob.status not in ("optimal", "optimal_inaccurate"):
        return None

    x_val = x.value
    if x_val is None:
        return None

    # Extraer solución — clamp a cero valores negativos por tolerancia numérica
    products_by_name = {p.name: p for p in products}
    meal_plan: dict[str, dict[str, float]] = {
        m.name: {
            products[i].name: max(0.0, float(x_val[i, j]))
            for i in range(n_p)
        }
        for j, m in enumerate(user.meals)
    }
    quantities: dict[str, float] = {
        products[i].name: max(0.0, sum(float(x_val[i, j]) for j in range(n_m)))
        for i in range(n_p)
    }

    total_cost    = sum(p.price_per_gram   * quantities[p.name] for p in products)
    total_kcal    = sum(p.kcal_per_gram    * quantities[p.name] for p in products)
    total_protein = sum(p.protein_per_gram * quantities[p.name] for p in products)
    total_fat     = sum(p.fat_per_gram     * quantities[p.name] for p in products)
    total_carbs   = sum(p.carbs_per_gram   * quantities[p.name] for p in products)

    return DietResult(
        status="optimal",
        user=user,
        quantities=quantities,
        meal_plan=meal_plan,
        total_cost=round(total_cost, 3),
        total_kcal=round(total_kcal, 1),
        total_protein=round(total_protein, 1),
        total_fat=round(total_fat, 1),
        total_carbs=round(total_carbs, 1),
        products_ref=products_by_name,
        solver_message=f"QP/CLARABEL  λ={user.diversity_weight}",
    )


def generate_diet(
    user: UserProfile,
    products: list[Product],
    verbose: bool = False,
    excluded_products: list[str] | None = None,
) -> DietResult:
    """
    Genera una dieta óptima usando Programación Lineal.

    Variables de decisión:
        x[i, m] = gramos del producto i en la comida m  (≥0, continua)

    Función objetivo:
        minimizar  Σ_i Σ_m price[i] · x[i,m]

    Restricciones:
        (A) Bounds por producto — total diario:
                min_g[i]  ≤  Σ_m x[i,m]  ≤  max_g[i]

        (B) Calorías diarias:
                kcal_target·(1−tol)  ≤  Σ_i Σ_m kcal[i]·x[i,m]  ≤  kcal_target·(1+tol)

        (C) Proteína diaria mínima:
                Σ_i Σ_m prot[i]·x[i,m]  ≥  min_protein

        (D) Grasa diaria máxima:
                Σ_i Σ_m fat[i]·x[i,m]  ≤  max_fat

        (E) Carbohidratos diarios:
                min_carbs  ≤  Σ_i Σ_m carbs[i]·x[i,m]  ≤  max_carbs

        (F) Presupuesto:
                Σ_i Σ_m price[i]·x[i,m]  ≤  budget

        (G) Restricciones por categoría — total diario:
                cat_min[c]  ≤  Σ_{i∈c} Σ_m x[i,m]  ≤  cat_max[c]

        (H) Calorías por comida:
                frac[m]·(1−tol[m])·target  ≤  Σ_i kcal[i]·x[i,m]  ≤  frac[m]·(1+tol[m])·target

        (I) Mínimo de categoría por comida:
                Σ_{i∈c} x[i,m]  ≥  cat_min_in_meal[m,c]

        (J) Categorías bloqueadas por comida (implementado con upBound=0):
                x[i,m] = 0  si category[i] ∉ allowed_categories[m]

        (K) Límite calórico por producto:
                Σ_m kcal[i] · x[i,m]  ≤  max_kcal_fraction · kcal_target
    """
    _excluded = set(excluded_products) if excluded_products else set()
    products = [p for p in products if p.name not in _excluded]

    # Guardar originales ANTES del ruido para restaurar products_ref después del solve
    # (el ruido solo afecta qué elige el solver; los precios mostrados son los reales)
    original_by_name = {p.name: p for p in products}

    if user.noise_factor > 0:
        products = _apply_cost_noise(products, user.noise_factor)

    # ── Intentar QP con diversidad (cvxpy) ───────────────────────────────
    if _CVXPY_AVAILABLE and user.diversity_weight > 0:
        try:
            result = _generate_diet_qp(user, products, verbose)
            if result is not None:
                result.products_ref = original_by_name
                return _prune_meal_plan(result)
            if verbose:
                print("[QP] resultado no-óptimo, usando fallback PuLP MIP")
        except Exception as exc:
            if verbose:
                print(f"[QP] excepción ({exc}), usando fallback PuLP MIP")

    # ── Fallback: PuLP MIP ────────────────────────────────────────────────
    products_by_cat: dict[str, list[Product]] = {}
    for p in products:
        products_by_cat.setdefault(p.category, []).append(p)

    prob = pulp.LpProblem("diet_optimization", pulp.LpMinimize)

    # Variables x[producto, comida].
    # upBound=0 implementa restricción (J) — categoría bloqueada en esa comida.
    # upBound=None en caso contrario: el tope diario lo impone constraint (A),
    # no el bound de la variable (evita que se multiplique por n_comidas).
    qty: dict[tuple[str, str], pulp.LpVariable] = {
        (p.name, m.name): pulp.LpVariable(
            name=f"qty_{_sanitize(p.name)}_{m.name}",
            lowBound=0.0,
            upBound=(
                0.0
                if m.allowed_categories is not None
                and p.category not in m.allowed_categories
                else None
            ),
            cat="Continuous",
        )
        for p in products
        for m in user.meals
    }

    # ── Semi-continuidad: porciones mínimas ───────────────────────────
    # Variables binarias use[i,m] ∈ {0,1}: 1 si el producto i aparece en comida m.
    # Restricciones:
    #   x[i,m] >= min_portion_g * use[i,m]   → si aparece, al menos min_portion_g gramos
    #   x[i,m] <= max_g[i]     * use[i,m]    → si no aparece, forzado a cero
    # Convierte el LP en MIP. Desactivado con min_portion_g=0 para mantener LP puro.
    use: dict[tuple[str, str], pulp.LpVariable] = {}
    if user.min_portion_g > 0:
        for p in products:
            for m in user.meals:
                # Las combinaciones bloqueadas (upBound=0) ya están forzadas a cero
                if (m.allowed_categories is not None
                        and p.category not in m.allowed_categories):
                    continue
                # Si el max del producto es menor que la porción mínima, el producto
                # quedará excluido (big_m < min_portion_g → y=0 forzado). Aceptable.
                big_m = p.max_grams_per_day
                y = pulp.LpVariable(
                    name=f"use_{_sanitize(p.name)}_{m.name}",
                    cat="Binary",
                )
                use[p.name, m.name] = y
                prob += (
                    qty[p.name, m.name] >= user.min_portion_g * y,
                    f"min_port_{_sanitize(p.name)}_{m.name}",
                )
                prob += (
                    qty[p.name, m.name] <= big_m * y,
                    f"max_port_{_sanitize(p.name)}_{m.name}",
                )

    # Totales diarios por producto (expresiones LP reutilizables)
    daily: dict[str, pulp.LpAffineExpression] = {
        p.name: pulp.lpSum(qty[p.name, m.name] for m in user.meals)
        for p in products
    }

    # Objetivo: minimizar coste total
    prob += pulp.lpSum(
        p.price_per_gram * qty[p.name, m.name]
        for p in products
        for m in user.meals
    ), "coste_total"

    # (A) Bounds diarios por producto
    for p in products:
        prob += (daily[p.name] <= p.max_grams_per_day, f"prod_max_{_sanitize(p.name)}")
        if p.min_grams_per_day > 0:
            prob += (daily[p.name] >= p.min_grams_per_day, f"prod_min_{_sanitize(p.name)}")

    kcal_expr = pulp.lpSum(
        p.kcal_per_gram * qty[p.name, m.name]
        for p in products for m in user.meals
    )

    # (B) Calorías diarias
    prob += (kcal_expr >= user.kcal_target * (1 - user.kcal_tolerance), "kcal_dia_min")
    prob += (kcal_expr <= user.kcal_target * (1 + user.kcal_tolerance), "kcal_dia_max")

    # (C) Proteína diaria mínima
    prob += (
        pulp.lpSum(
            p.protein_per_gram * qty[p.name, m.name]
            for p in products for m in user.meals
        ) >= user.min_protein_g,
        "proteina_min",
    )

    # (D) Grasa diaria máxima
    prob += (
        pulp.lpSum(
            p.fat_per_gram * qty[p.name, m.name]
            for p in products for m in user.meals
        ) <= user.max_fat_g,
        "grasa_max",
    )

    # (E) Carbohidratos diarios
    carbs_expr = pulp.lpSum(
        p.carbs_per_gram * qty[p.name, m.name]
        for p in products for m in user.meals
    )
    prob += (carbs_expr >= user.min_carbs_g, "carbs_min")
    prob += (carbs_expr <= user.max_carbs_g, "carbs_max")

    # (F) Presupuesto
    prob += (
        pulp.lpSum(
            p.price_per_gram * qty[p.name, m.name]
            for p in products for m in user.meals
        ) <= user.budget_eur,
        "presupuesto",
    )

    # (G) Restricciones diarias por categoría
    for cat, constraint in user.category_constraints.items():
        cat_prods = products_by_cat.get(cat, [])
        if not cat_prods:
            continue
        cat_total = pulp.lpSum(daily[p.name] for p in cat_prods)
        if constraint.min_grams > 0:
            prob += (cat_total >= constraint.min_grams, f"cat_min_{cat}")
        if constraint.max_grams < 9999.0:
            prob += (cat_total <= constraint.max_grams, f"cat_max_{cat}")

    # (H) Calorías por comida  +  (I) Mínimos de categoría por comida
    for m in user.meals:
        meal_kcal = pulp.lpSum(
            p.kcal_per_gram * qty[p.name, m.name] for p in products
        )
        meal_target = user.kcal_target * m.kcal_fraction
        prob += (meal_kcal >= meal_target * (1 - m.kcal_tolerance), f"meal_kcal_min_{m.name}")
        prob += (meal_kcal <= meal_target * (1 + m.kcal_tolerance), f"meal_kcal_max_{m.name}")

        for cat, min_g in m.category_min_grams.items():
            eligible = [
                p for p in products_by_cat.get(cat, [])
                if m.allowed_categories is None or p.category in m.allowed_categories
            ]
            if eligible:
                prob += (
                    pulp.lpSum(qty[p.name, m.name] for p in eligible) >= min_g,
                    f"meal_cat_min_{m.name}_{cat}",
                )

    # (K) Límite calórico por producto
    if user.max_kcal_fraction_per_product < 1.0:
        kcal_cap = user.kcal_target * user.max_kcal_fraction_per_product
        for p in products:
            prob += (
                pulp.lpSum(p.kcal_per_gram * qty[p.name, m.name] for m in user.meals)
                <= kcal_cap,
                f"prod_kcal_cap_{_sanitize(p.name)}",
            )

    # Resolver — MIP cuando hay variables binarias, LP puro si min_portion_g=0
    prob.solve(pulp.PULP_CBC_CMD(msg=verbose, timeLimit=60))

    _lp_status = {
        1: "optimal",
        0: "not_solved",
        -1: "infeasible",
        -2: "unbounded",
        -3: "undefined",
    }
    status = _lp_status.get(prob.status, "error")

    if status != "optimal":
        return DietResult(
            status=status,
            user=user,
            quantities={},
            meal_plan={},
            total_cost=0.0,
            total_kcal=0.0,
            total_protein=0.0,
            total_fat=0.0,
            total_carbs=0.0,
            solver_message=pulp.LpStatus.get(prob.status, str(prob.status)),
        )

    # Extraer resultados
    meal_plan: dict[str, dict[str, float]] = {
        m.name: {
            p.name: pulp.value(qty[p.name, m.name]) or 0.0
            for p in products
        }
        for m in user.meals
    }
    quantities = {
        p.name: sum(meal_plan[m.name][p.name] for m in user.meals)
        for p in products
    }

    total_cost = sum(p.price_per_gram * quantities[p.name] for p in products)
    total_kcal = sum(p.kcal_per_gram * quantities[p.name] for p in products)
    total_protein = sum(p.protein_per_gram * quantities[p.name] for p in products)
    total_fat = sum(p.fat_per_gram * quantities[p.name] for p in products)
    total_carbs = sum(p.carbs_per_gram * quantities[p.name] for p in products)

    _pulp_result = DietResult(
        status=status,
        user=user,
        quantities=quantities,
        meal_plan=meal_plan,
        total_cost=round(total_cost, 3),
        total_kcal=round(total_kcal, 1),
        total_protein=round(total_protein, 1),
        total_fat=round(total_fat, 1),
        total_carbs=round(total_carbs, 1),
        products_ref=original_by_name,   # precios originales, sin ruido
        solver_message="MIP/CBC (fallback)",
    )
    return _prune_meal_plan(_pulp_result)


# ─────────────────────────────────────────────
# 4. MOTOR BASADO EN RECETAS PREDEFINIDAS
# ─────────────────────────────────────────────

def _attempt_recipe_mip(
    user: "UserProfile",
    all_recipes: list,
    effective_kcal: float,
    kcal_tol: float,
    fallback: dict,
    recent: set,
    db,
    verbose: bool = False,
) -> "DietResult | None":
    """
    Construye y resuelve un MIP de selección de recetas con la configuración de relajación dada.
    Devuelve DietResult si es óptimo, None si infeasible.
    """
    idx_by_meal: dict[str, list[int]] = {"desayuno": [], "comida": [], "cena": []}
    for i, rd in enumerate(all_recipes):
        idx_by_meal[rd.recipe.meal_type].append(i)

    if any(not idxs for idxs in idx_by_meal.values()):
        return None

    prob = pulp.LpProblem("recipe_selection", pulp.LpMaximize)
    sel = [pulp.LpVariable(f"sel_{i}", cat="Binary") for i in range(len(all_recipes))]

    for meal_type, idxs in idx_by_meal.items():
        prob += (pulp.lpSum(sel[i] for i in idxs) == 1, f"one_recipe_{meal_type}")

    kcal_expr    = pulp.lpSum(all_recipes[i].scaled_kcal    * sel[i] for i in range(len(all_recipes)))
    protein_expr = pulp.lpSum(all_recipes[i].scaled_protein * sel[i] for i in range(len(all_recipes)))
    fat_expr     = pulp.lpSum(all_recipes[i].scaled_fat     * sel[i] for i in range(len(all_recipes)))
    carbs_expr   = pulp.lpSum(all_recipes[i].scaled_carbs   * sel[i] for i in range(len(all_recipes)))
    cost_expr    = pulp.lpSum(all_recipes[i].scaled_cost    * sel[i] for i in range(len(all_recipes)))

    prob += (kcal_expr >= effective_kcal * (1 - kcal_tol),  "kcal_min")
    prob += (kcal_expr <= effective_kcal * (1 + kcal_tol),  "kcal_max")
    if fallback.get("min_protein_g", 0) > 0:
        prob += (protein_expr >= fallback["min_protein_g"],  "protein_min")
    if fallback.get("max_fat_g", 999) < 999:
        prob += (fat_expr     <= fallback["max_fat_g"],      "fat_max")
    if fallback.get("min_carbs_g", 0) > 0:
        prob += (carbs_expr   >= fallback["min_carbs_g"],    "carbs_min")
    prob += (carbs_expr       <= user.max_carbs_g,           "carbs_max")
    prob += (cost_expr        <= user.budget_eur,            "budget_max")
    if fallback.get("budget_min_frac", 0) > 0:
        prob += (cost_expr    >= user.budget_eur * fallback["budget_min_frac"], "budget_min")

    quality_expr = pulp.lpSum(
        (all_recipes[i].quality_score - (2.5 if all_recipes[i].recipe.name in recent else 0.0))
        * sel[i]
        for i in range(len(all_recipes))
    )
    prob += quality_expr - 0.01 * cost_expr / user.budget_eur, "quality_total"

    prob.solve(pulp.PULP_CBC_CMD(msg=verbose))

    _lp_status = {1: "optimal", 0: "not_solved", -1: "infeasible", -2: "unbounded", -3: "undefined"}
    if _lp_status.get(prob.status, "error") != "optimal":
        return None

    from app.models.diet import ProductORM
    all_orm = {p.name: p for p in db.query(ProductORM).all()}

    meal_plan:            dict[str, dict[str, float]] = {}
    quantities:           dict[str, float] = {}
    products_ref:         dict[str, Product] = {}
    recipe_names_by_meal: dict[str, str] = {}
    proteins_by_meal:     dict[str, str] = {}
    recipes_by_meal:      dict = {}
    total_cost = total_kcal = total_protein = total_fat = total_carbs = 0.0

    for i, rd in enumerate(all_recipes):
        if pulp.value(sel[i]) < 0.5:
            continue
        meal_items: dict[str, float] = {}
        for pname, grams in zip(rd.product_names, rd.scaled_grams):
            meal_items[pname] = meal_items.get(pname, 0.0) + grams
            quantities[pname] = quantities.get(pname, 0.0) + grams
            if pname in all_orm and pname not in products_ref:
                orm = all_orm[pname]
                products_ref[pname] = Product(
                    name=orm.name, category=orm.category,
                    price_per_100g=orm.price_per_100g, kcal_per_100g=orm.kcal_per_100g,
                    protein_per_100g=orm.protein_per_100g, fat_per_100g=orm.fat_per_100g,
                    carbs_per_100g=orm.carbs_per_100g,
                    max_grams_per_day=orm.max_grams_per_day, min_grams_per_day=orm.min_grams_per_day,
                )
        meal_plan[rd.recipe.meal_type]            = meal_items
        recipe_names_by_meal[rd.recipe.meal_type] = rd.recipe.name
        proteins_by_meal[rd.recipe.meal_type]     = rd.main_protein
        recipes_by_meal[rd.recipe.meal_type]      = rd.recipe
        total_cost    += rd.scaled_cost
        total_kcal    += rd.scaled_kcal
        total_protein += rd.scaled_protein
        total_fat     += rd.scaled_fat
        total_carbs   += rd.scaled_carbs

    return DietResult(
        status="optimal", user=user,
        quantities=quantities, meal_plan=meal_plan,
        total_cost=round(total_cost, 3), total_kcal=round(total_kcal, 1),
        total_protein=round(total_protein, 1), total_fat=round(total_fat, 1),
        total_carbs=round(total_carbs, 1),
        products_ref=products_ref, solver_message="MIP/recipes",
        recipe_names_by_meal=recipe_names_by_meal, proteins_by_meal=proteins_by_meal,
        recipes_by_meal=recipes_by_meal,
    )


def generate_diet_from_recipes(
    user: UserProfile,
    db,
    excluded_recipe_names: list[str] | None = None,
    recent_recipe_names: list[str] | None = None,
    preferences: dict | None = None,
    verbose: bool = False,
) -> DietResult:
    """
    Genera una dieta seleccionando exactamente 1 receta por comida (desayuno/
    comida/cena) mediante un MIP pequeño con variables binarias.

    Con fallback progresivo de 4 intentos cuando el solver devuelve infeasible:
      1. Restricciones completas
      2. Sin mínimo de proteína
      3. Sin mínimos de proteína ni carbohidratos
      4. Sin mínimos de proteína/carbos y sin límite de grasa

    Para presupuestos < 3.5€ se amplía automáticamente la tolerancia calórica
    a ±20% y se elimina la restricción de gasto mínimo.
    Para presupuestos < 3€ las recetas se escalan a un objetivo calórico
    proporcional al presupuesto (≈550 kcal/€) para garantizar recetas asequibles.
    """
    from app.engine.recipes import build_recipe_lp_data, ResolvedRecipeData

    excluded = set(excluded_recipe_names or [])

    # Mejora 4: escalar objetivo calórico al presupuesto cuando es bajo
    effective_kcal = (
        min(user.kcal_target, user.budget_eur * 550)
        if user.budget_eur < 3.0
        else user.kcal_target
    )

    recipe_data = build_recipe_lp_data(db, effective_kcal, preferences=preferences)

    all_recipes_full: list[ResolvedRecipeData] = [
        rd
        for meal_type in ("desayuno", "comida", "cena")
        for rd in recipe_data[meal_type]
        if rd.recipe.name not in excluded
    ]

    if not all_recipes_full:
        return DietResult(
            status="infeasible", user=user, quantities={}, meal_plan={},
            total_cost=0.0, total_kcal=0.0, total_protein=0.0, total_fat=0.0, total_carbs=0.0,
            solver_message="Sin recetas disponibles en la BD",
        )

    for meal_type in ("desayuno", "comida", "cena"):
        if not any(rd.recipe.meal_type == meal_type for rd in all_recipes_full):
            return DietResult(
                status="infeasible", user=user, quantities={}, meal_plan={},
                total_cost=0.0, total_kcal=0.0, total_protein=0.0, total_fat=0.0, total_carbs=0.0,
                solver_message=f"Sin recetas disponibles para '{meal_type}'",
            )

    # Mejora 2: filtrar recetas que superen el presupuesto diario completo
    all_recipes = [rd for rd in all_recipes_full if rd.scaled_cost <= user.budget_eur * 1.1]
    for mt in ("desayuno", "comida", "cena"):
        if not any(rd.recipe.meal_type == mt for rd in all_recipes):
            all_recipes = all_recipes_full  # restaurar si el filtro dejó algún tipo vacío
            break

    # Mejora 1: tolerancia calórica ampliada para presupuestos ajustados
    kcal_tol = 0.20 if user.budget_eur < 3.5 else user.kcal_tolerance * 2

    # Mejora 3: fallback progresivo (4 intentos con restricciones cada vez más relajadas)
    fallback_configs = [
        dict(min_protein_g=user.min_protein_g, min_carbs_g=user.min_carbs_g,
             max_fat_g=user.max_fat_g,
             budget_min_frac=0.0 if user.budget_eur < 3.5 else 0.6),
        dict(min_protein_g=0, min_carbs_g=user.min_carbs_g,
             max_fat_g=user.max_fat_g, budget_min_frac=0.0),
        dict(min_protein_g=0, min_carbs_g=0,
             max_fat_g=user.max_fat_g, budget_min_frac=0.0),
        dict(min_protein_g=0, min_carbs_g=0,
             max_fat_g=999, budget_min_frac=0.0),
    ]

    _recent = set(recent_recipe_names) if recent_recipe_names else set()

    for attempt, fb in enumerate(fallback_configs):
        result = _attempt_recipe_mip(
            user=user, all_recipes=all_recipes, effective_kcal=effective_kcal,
            kcal_tol=kcal_tol, fallback=fb, recent=_recent, db=db, verbose=verbose,
        )
        if result is not None:
            if attempt > 0:
                result.solver_message += f" [fallback={attempt}]"
            return result

    return DietResult(
        status="infeasible", user=user, quantities={}, meal_plan={},
        total_cost=0.0, total_kcal=0.0, total_protein=0.0, total_fat=0.0, total_carbs=0.0,
        solver_message="Sin solución tras 4 intentos de relajación",
    )


# ─────────────────────────────────────────────
# 5. EJEMPLOS DE USO
# ─────────────────────────────────────────────

def run_examples():
    profiles = [
        UserProfile(
            name="Carlos — Perder peso",
            kcal_target=1800,
            min_protein_g=140,
            max_fat_g=60,
            min_carbs_g=120,
            max_carbs_g=220,
            budget_eur=4.50,
        ),
        UserProfile(
            name="Laura — Mantener peso",
            kcal_target=2000,
            min_protein_g=80,
            max_fat_g=75,
            min_carbs_g=200,
            max_carbs_g=280,
            budget_eur=5.00,
        ),
        UserProfile(
            name="Miguel — Ganar músculo",
            kcal_target=2800,
            min_protein_g=180,
            max_fat_g=90,
            min_carbs_g=300,
            max_carbs_g=400,
            budget_eur=7.00,
        ),
    ]

    for profile in profiles:
        result = generate_diet(profile, SAMPLE_PRODUCTS)
        print(result.summary())
        print(f"  Solver: {result.solver_message}\n")

def run_recipe_examples():
    import os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    sys.stdout.reconfigure(encoding="utf-8")

    from dotenv import load_dotenv
    load_dotenv()

    from app.db.session import SessionLocal
    db = SessionLocal()

    profiles = [
        UserProfile(
            name="Carlos — Perder peso",
            kcal_target=1800,
            min_protein_g=140,
            max_fat_g=60,
            min_carbs_g=120,
            max_carbs_g=220,
            budget_eur=4.50,
        ),
        UserProfile(
            name="Laura — Mantener peso",
            kcal_target=2000,
            min_protein_g=80,
            max_fat_g=75,
            min_carbs_g=200,
            max_carbs_g=280,
            budget_eur=5.00,
        ),
        UserProfile(
            name="Miguel — Ganar músculo",
            kcal_target=2800,
            min_protein_g=180,
            max_fat_g=90,
            min_carbs_g=300,
            max_carbs_g=400,
            budget_eur=7.00,
        ),
        # ── Prueba de presupuesto ajustado ────────────────────────────────
        UserProfile(
            name="Carlos — 3€/día",
            kcal_target=1800,
            min_protein_g=80,
            max_fat_g=70,
            min_carbs_g=120,
            max_carbs_g=280,
            budget_eur=3.00,
        ),
        UserProfile(
            name="Laura — 3€/día",
            kcal_target=2000,
            min_protein_g=80,
            max_fat_g=75,
            min_carbs_g=200,
            max_carbs_g=280,
            budget_eur=3.00,
        ),
        UserProfile(
            name="Miguel — 3€/día",
            kcal_target=2800,
            min_protein_g=140,
            max_fat_g=100,
            min_carbs_g=300,
            max_carbs_g=420,
            budget_eur=3.00,
        ),
    ]

    try:
        for profile in profiles:
            result = generate_diet_from_recipes(profile, db)
            print(result.summary())
            print(f"  Solver: {result.solver_message}\n")
    finally:
        db.close()


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    run_recipe_examples()
