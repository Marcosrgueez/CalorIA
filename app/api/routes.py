from typing import Optional
import math

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.api.auth import FREE_DAILY_LIMIT, _today_str, get_optional_user
from app.db.session import get_db
from app.engine.diet_engine import DietResult, Product, UserProfile, generate_diet, generate_diet_from_recipes
from app.engine.recipe_namer import name_meal
from app.engine.recipes import RECIPES_BY_NAME
from app.models.diet import DietMealORM, DietPlanORM, ProductORM, UserORM
from app.utils.recipe_images import get_recipe_image

from app.schemas.diet import (
    DayDietResponse,
    DietResponse,
    DietSummaryResponse,
    FridgeRequest,
    HealthResponse,
    MacrosResponse,
    MealItemResponse,
    MLTrainingRecord,
    MealResponse,
    RatingResponse,
    ShoppingListItem,
    ShoppingListResponse,
    UserProfileRequest,
    WeekPlanResponse,
)

router = APIRouter()

FREEMIUM_ENABLED = False  # Cambiar a True cuando se lance


def _parse_supermarkets(supermarket: str) -> list[str]:
    """Convierte el string de supermercado a lista. 'todos' → todos los conocidos."""
    if supermarket == "todos":
        return ["mercadona", "carrefour", "gadis", "consum"]
    if supermarket.startswith("multi:"):
        return supermarket[6:].split(",")
    return [supermarket]


def _get_products_from_db(db: Session, supermarket: str = "mercadona") -> list:
    """Carga productos filtrando por supermercado. 'todos' devuelve todos."""
    query = db.query(ProductORM)
    if supermarket != "todos":
        query = query.filter(ProductORM.supermarket.in_(_parse_supermarkets(supermarket)))
    return query.all()


def check_freemium_limits(
    db: Session,
    user: Optional[UserORM],
    *,
    premium_only: bool = False,
) -> None:
    """
    Raises 403 if a premium-only endpoint is called by a free/anonymous user.
    Raises 429 if a free user has hit the daily diet generation limit.
    """
    if not FREEMIUM_ENABLED:
        return
    plan = user.plan if user else "free"

    if premium_only and plan != "premium":
        raise HTTPException(
            status_code=403,
            detail={
                "code": "premium_required",
                "message": "Esta función requiere el plan Premium.",
            },
        )

    if plan != "premium" and user is not None:
        today = _today_str()
        if user.last_diet_date != today:
            user.diets_today = 0
            user.last_diet_date = today
        if user.diets_today >= FREE_DAILY_LIMIT:
            raise HTTPException(
                status_code=429,
                detail={
                    "code": "daily_limit",
                    "message": f"Has alcanzado el límite de {FREE_DAILY_LIMIT} dietas diarias del plan gratuito.",
                },
            )


def _increment_diets_today(db: Session, user: Optional[UserORM]) -> None:
    if user is None or user.plan == "premium":
        return
    today = _today_str()
    if user.last_diet_date != today:
        user.diets_today = 1
        user.last_diet_date = today
    else:
        user.diets_today += 1
    db.commit()


# Orden y fracciones calóricas fijas de las comidas por defecto.
# Cuando meal config sea configurable por usuario, esto pasará al modelo de BD.
_MEAL_ORDER = ["desayuno", "comida", "cena"]
_MEAL_FRACTIONS: dict[str, float] = {"desayuno": 0.25, "comida": 0.40, "cena": 0.35}


# ─────────────────────────────────────────────
# Conversores internos
# ─────────────────────────────────────────────

def _orm_to_engine_product(p: ProductORM) -> Product:
    return Product(
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


def _engine_result_to_response(result: DietResult, plan: DietPlanORM) -> DietResponse:
    """Construye DietResponse a partir del resultado del optimizador + la fila recién guardada."""
    meals = []
    for meal_cfg in result.user.meals:
        items = []
        for name, grams in result.meal_plan.get(meal_cfg.name, {}).items():
            if grams <= 0.5:
                continue
            p = result.products_ref[name]
            items.append(
                MealItemResponse(
                    product=name,
                    category=p.category,
                    grams=round(grams, 1),
                    kcal=round(p.kcal_per_gram * grams, 1),
                    cost_eur=round(p.price_per_gram * grams, 3),
                )
            )
        items.sort(key=lambda x: -x.grams)
        canonical = result.recipe_names_by_meal.get(meal_cfg.name, "")
        recipe_obj = (
            result.recipes_by_meal.get(meal_cfg.name)
            or RECIPES_BY_NAME.get(canonical)
        )
        meals.append(
            MealResponse(
                name=meal_cfg.name,
                recipe_name=canonical or name_meal(items),
                kcal_target_pct=meal_cfg.kcal_fraction,
                kcal_actual=round(sum(i.kcal for i in items), 1),
                cost_eur=round(sum(i.cost_eur for i in items), 3),
                items=items,
                instructions=recipe_obj.instructions if recipe_obj else [],
                prep_time_min=recipe_obj.prep_time_min if recipe_obj else 15,
                image_url=get_recipe_image(canonical) if canonical else "",
            )
        )

    return DietResponse(
        diet_id=plan.id,
        created_at=plan.created_at,
        status=result.status,
        user_name=result.user.name,
        macros=MacrosResponse(
            kcal=result.total_kcal,
            protein_g=result.total_protein,
            fat_g=result.total_fat,
            carbs_g=result.total_carbs,
            cost_eur=result.total_cost,
        ),
        meals=meals,
        rating=plan.rating,
    )


def _plan_orm_to_response(plan: DietPlanORM) -> DietResponse:
    """Reconstruye DietResponse desde un DietPlanORM cargado con sus meals."""
    meals_by_name: dict[str, list[DietMealORM]] = {}
    for item in plan.meals:
        meals_by_name.setdefault(item.meal_name, []).append(item)

    meals = []
    for meal_name in _MEAL_ORDER:
        if meal_name not in meals_by_name:
            continue
        sorted_items = sorted(meals_by_name[meal_name], key=lambda x: -x.grams)
        meal_items = [
            MealItemResponse(
                product=i.product_name,
                category=i.category,
                grams=i.grams,
                kcal=i.kcal,
                cost_eur=i.cost_eur,
            )
            for i in sorted_items
        ]
        canonical = next((i.recipe_name for i in sorted_items if i.recipe_name), "")
        recipe_obj = RECIPES_BY_NAME.get(canonical)
        meals.append(
            MealResponse(
                name=meal_name,
                recipe_name=canonical or name_meal(meal_items),
                kcal_target_pct=_MEAL_FRACTIONS.get(meal_name, 0.0),
                kcal_actual=round(sum(i.kcal for i in meal_items), 1),
                cost_eur=round(sum(i.cost_eur for i in meal_items), 3),
                items=meal_items,
                instructions=recipe_obj.instructions if recipe_obj else [],
                prep_time_min=recipe_obj.prep_time_min if recipe_obj else 15,
                image_url=get_recipe_image(canonical) if canonical else "",
            )
        )

    return DietResponse(
        diet_id=plan.id,
        created_at=plan.created_at,
        status=plan.status,
        user_name=plan.user_name,
        macros=MacrosResponse(
            kcal=plan.total_kcal,
            protein_g=plan.total_protein_g,
            fat_g=plan.total_fat_g,
            carbs_g=plan.total_carbs_g,
            cost_eur=plan.total_cost_eur,
        ),
        meals=meals,
        rating=plan.rating,
    )


# ─────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────

@router.post("/diet", response_model=DietResponse, status_code=201, summary="Genera una dieta óptima")
def create_diet(
    request: UserProfileRequest,
    db: Session = Depends(get_db),
    user: Optional[UserORM] = Depends(get_optional_user),
) -> DietResponse:
    """
    Recibe el perfil nutricional del usuario, optimiza la dieta y la persiste.

    Devuelve **422** si las restricciones no tienen solución factible
    (presupuesto demasiado bajo o metas nutricionales incompatibles).
    """
    check_freemium_limits(db, user)
    products = [_orm_to_engine_product(p) for p in _get_products_from_db(db, request.supermarket)]

    user_profile = UserProfile(
        name=request.name,
        kcal_target=request.kcal_target,
        kcal_tolerance=request.kcal_tolerance,
        min_protein_g=request.min_protein_g,
        max_fat_g=request.max_fat_g,
        budget_eur=request.budget_eur,
        min_carbs_g=request.min_carbs_g,
        max_carbs_g=request.max_carbs_g,
        min_portion_g=request.min_portion_g,
        diversity_weight=request.diversity_weight,
    )
    result = generate_diet(user_profile, products)

    if result.status != "optimal":
        raise HTTPException(status_code=422, detail=_diagnose_infeasibility(user_profile))

    # Persistir plan
    plan = DietPlanORM(
        user_name=user_profile.name,
        status=result.status,
        kcal_target=user_profile.kcal_target,
        budget_eur=user_profile.budget_eur,
        total_kcal=result.total_kcal,
        total_protein_g=result.total_protein,
        total_fat_g=result.total_fat,
        total_carbs_g=result.total_carbs,
        total_cost_eur=result.total_cost,
    )
    db.add(plan)
    db.flush()

    for meal_name, items in result.meal_plan.items():
        recipe_name = result.recipe_names_by_meal.get(meal_name)
        for product_name, grams in items.items():
            if grams <= 0.5:
                continue
            p = result.products_ref[product_name]
            db.add(
                DietMealORM(
                    plan_id=plan.id,
                    meal_name=meal_name,
                    recipe_name=recipe_name,
                    product_name=product_name,
                    category=p.category,
                    grams=round(grams, 1),
                    kcal=round(p.kcal_per_gram * grams, 1),
                    cost_eur=round(p.price_per_gram * grams, 3),
                )
            )

    db.commit()
    db.refresh(plan)
    _increment_diets_today(db, user)

    return _engine_result_to_response(result, plan)


_DAYS_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
# Productos a excluir por categoría tras cada día
_TOP_PROTEIN_EXCLUDE = 2   # dominantes de proteina+legumbre por gramos
_TOP_CARB_EXCLUDE    = 2   # dominantes de carbohidrato por gramos
# Ventana de exclusión: los excluidos el día N solo se bloquean en el día N+1.
# En el día N+2 vuelven a estar disponibles.


def _dominant_products(result: DietResult, category_filter: set[str], top_n: int) -> list[str]:
    """Devuelve los top_n productos de las categorías indicadas, ordenados por gramos totales."""
    grams_total: dict[str, float] = {}
    for meal_items in result.meal_plan.values():
        for pname, g in meal_items.items():
            if g <= 0.5:
                continue
            p = result.products_ref[pname]
            if p.category in category_filter:
                grams_total[pname] = grams_total.get(pname, 0.0) + g
    return [name for name, _ in sorted(grams_total.items(), key=lambda x: -x[1])[:top_n]]


def _persist_plan(db: Session, user: UserProfile, result: DietResult) -> DietPlanORM:
    """Persiste un DietResult en BD y devuelve el ORM con id y created_at cargados."""
    plan = DietPlanORM(
        user_name=user.name,
        status=result.status,
        kcal_target=user.kcal_target,
        budget_eur=user.budget_eur,
        total_kcal=result.total_kcal,
        total_protein_g=result.total_protein,
        total_fat_g=result.total_fat,
        total_carbs_g=result.total_carbs,
        total_cost_eur=result.total_cost,
    )
    db.add(plan)
    db.flush()

    for meal_name, items in result.meal_plan.items():
        recipe_name = result.recipe_names_by_meal.get(meal_name)
        for product_name, grams in items.items():
            if grams <= 0.5:
                continue
            p = result.products_ref[product_name]
            db.add(
                DietMealORM(
                    plan_id=plan.id,
                    meal_name=meal_name,
                    recipe_name=recipe_name,
                    product_name=product_name,
                    category=p.category,
                    grams=round(grams, 1),
                    kcal=round(p.kcal_per_gram * grams, 1),
                    cost_eur=round(p.price_per_gram * grams, 3),
                )
            )

    db.commit()
    db.refresh(plan)
    return plan


@router.post(
    "/diet/week",
    response_model=WeekPlanResponse,
    status_code=201,
    summary="Genera un plan semanal de dietas con variedad",
)
def create_week_plan(
    request: UserProfileRequest,
    db: Session = Depends(get_db),
    user: Optional[UserORM] = Depends(get_optional_user),
) -> WeekPlanResponse:
    """
    Genera 7 dietas diarias consecutivas con variedad garantizada.

    Mecanismo de exclusión con ventana de 1 día:
    - Tras el día N se identifican los 2 productos dominantes de proteina/legumbre
      y los 2 dominantes de carbohidrato (por gramos totales).
    - Esos 4 productos se excluyen del día N+1 pasándolos a generate_diet()
      como excluded_products.
    - En el día N+2 vuelven a estar disponibles (ventana = 1 día).
    """
    check_freemium_limits(db, user, premium_only=True)
    all_products_orm = _get_products_from_db(db, request.supermarket)
    base_products = [_orm_to_engine_product(p) for p in all_products_orm]

    days: list[DayDietResponse] = []
    # excluded_window[i] = set de nombres excluidos el día i (solo aplica al día i+1)
    excluded_today: list[str] = []

    for day_idx in range(7):
        user_profile = UserProfile(
            name=request.name,
            kcal_target=request.kcal_target,
            kcal_tolerance=request.kcal_tolerance,
            min_protein_g=request.min_protein_g,
            max_fat_g=request.max_fat_g,
            budget_eur=request.budget_eur,
            min_carbs_g=request.min_carbs_g,
            max_carbs_g=request.max_carbs_g,
            min_portion_g=request.min_portion_g,
            diversity_weight=request.diversity_weight,
        )
        result = generate_diet(user_profile, base_products, excluded_products=excluded_today)

        if result.status != "optimal":
            diag = _diagnose_infeasibility(user_profile)
            diag["message"] = f"{_DAYS_ES[day_idx]}: {diag['message']}"
            raise HTTPException(status_code=422, detail=diag)

        plan = _persist_plan(db, user_profile, result)
        diet_response = _engine_result_to_response(result, plan)
        days.append(DayDietResponse(day=_DAYS_ES[day_idx], day_index=day_idx, diet=diet_response))

        # Calcular exclusiones para el día siguiente (ventana = 1 día)
        top_proteins = _dominant_products(result, {"proteina", "legumbre"}, _TOP_PROTEIN_EXCLUDE)
        top_carbs    = _dominant_products(result, {"carbohidrato"},          _TOP_CARB_EXCLUDE)
        excluded_today = top_proteins + top_carbs  # se limpian automáticamente el día N+2

    return WeekPlanResponse(user_name=request.name, days=days)


@router.get("/diets", response_model=list[DietSummaryResponse], summary="Historial de dietas")
def list_diets(limit: int = 20, db: Session = Depends(get_db)) -> list[DietSummaryResponse]:
    """Devuelve las últimas `limit` dietas guardadas, ordenadas por fecha descendente."""
    plans = (
        db.query(DietPlanORM)
        .order_by(DietPlanORM.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        DietSummaryResponse(
            diet_id=p.id,
            created_at=p.created_at,
            user_name=p.user_name,
            kcal_target=p.kcal_target,
            total_kcal=p.total_kcal,
            total_protein=p.total_protein_g,
            total_cost=p.total_cost_eur,
            status=p.status,
            rating=p.rating,
        )
        for p in plans
    ]


@router.get("/diets/{diet_id}", response_model=DietResponse, summary="Recupera una dieta guardada")
def get_diet(diet_id: int, db: Session = Depends(get_db)) -> DietResponse:
    """Devuelve una dieta previamente generada por su ID."""
    plan = (
        db.query(DietPlanORM)
        .options(joinedload(DietPlanORM.meals))
        .filter(DietPlanORM.id == diet_id)
        .first()
    )
    if plan is None:
        raise HTTPException(status_code=404, detail=f"Dieta {diet_id} no encontrada.")
    return _plan_orm_to_response(plan)


@router.post("/diets/{diet_id}/rate", response_model=RatingResponse, summary="Valora una dieta")
def rate_diet(diet_id: int, rating: int, db: Session = Depends(get_db)) -> RatingResponse:
    """
    Guarda una valoración (1 = positivo, -1 = negativo) para una dieta.
    El motor de recetas usa estas valoraciones para ajustar el quality_score.
    """
    if rating not in (1, -1):
        raise HTTPException(status_code=422, detail="rating debe ser 1 (positivo) o -1 (negativo).")
    plan = db.query(DietPlanORM).filter(DietPlanORM.id == diet_id).first()
    if plan is None:
        raise HTTPException(status_code=404, detail=f"Dieta {diet_id} no encontrada.")
    plan.rating = rating
    db.commit()
    return RatingResponse(diet_id=diet_id, rating=rating)


def _diagnose_infeasibility(user: UserProfile, db=None) -> dict:
    """
    Devuelve {message, suggestions} con la causa probable del fallo.
    Usa heurísticas derivadas del análisis de factibilidad.
    """
    prot   = user.min_protein_g
    budget = user.budget_eur
    kcal   = user.kcal_target

    # Límite fisiológico: >40% de kcal como proteína
    max_prot_fisio = kcal * 0.40 / 4
    if prot > max_prot_fisio:
        return {
            "message": (
                f"{prot:.0f}g de proteína representa más del 40% de {kcal:.0f} kcal "
                f"(máximo razonable: {max_prot_fisio:.0f}g). "
                "No existe ninguna combinación de alimentos que lo cumpla."
            ),
            "suggestions": [
                f"Reduce la proteína a menos de {max_prot_fisio:.0f}g",
                f"Aumenta las calorías objetivo por encima de {int(prot * 4 / 0.40)} kcal",
            ],
        }

    # Proteína alta con presupuesto insuficiente
    if prot > 180 and budget < 6.0:
        return {
            "message": (
                f"Con {prot:.0f}g de proteína se necesita un presupuesto de al menos 6 €/día "
                f"(presupuesto actual: {budget:.2f} €). "
                "Las fuentes de proteína disponibles no son suficientemente baratas para este objetivo."
            ),
            "suggestions": [
                "Sube el presupuesto a 6 €/día o más",
                f"Reduce la proteína a 140-160g (factible desde 4 €/día con {kcal:.0f} kcal)",
            ],
        }

    if prot > 140 and budget < 4.0:
        return {
            "message": (
                f"Con {prot:.0f}g de proteína se necesita un presupuesto de al menos 4 €/día "
                f"(presupuesto actual: {budget:.2f} €)."
            ),
            "suggestions": [
                "Sube el presupuesto a 4 €/día o más",
                "Reduce la proteína a 100-120g (alcanzable con 3 €/día)",
            ],
        }

    # Caso genérico — restricciones combinadas
    return {
        "message": (
            "No se encontró ninguna combinación de recetas que cumpla simultáneamente "
            "las restricciones de calorías, proteína, grasa, carbohidratos y presupuesto."
        ),
        "suggestions": [
            "Aumenta el presupuesto diario",
            "Reduce el objetivo de proteína",
            "Amplía el rango de carbohidratos",
            "Aumenta la grasa máxima permitida",
        ],
    }


def _user_from_request(request: UserProfileRequest) -> UserProfile:
    return UserProfile(
        name=request.name,
        kcal_target=request.kcal_target,
        kcal_tolerance=request.kcal_tolerance,
        min_protein_g=request.min_protein_g,
        max_fat_g=request.max_fat_g,
        budget_eur=request.budget_eur,
        min_carbs_g=request.min_carbs_g,
        max_carbs_g=request.max_carbs_g,
        min_portion_g=request.min_portion_g,
        diversity_weight=request.diversity_weight,
    )


@router.post(
    "/diet/recipe",
    response_model=DietResponse,
    status_code=201,
    summary="Genera una dieta seleccionando recetas predefinidas",
)
def create_diet_recipe(
    request: UserProfileRequest,
    db: Session = Depends(get_db),
    user: Optional[UserORM] = Depends(get_optional_user),
) -> DietResponse:
    """
    Selecciona exactamente 1 receta para desayuno, comida y cena mediante MIP.
    Las recetas se escalan al objetivo calórico del usuario.
    """
    check_freemium_limits(db, user)
    user_profile = _user_from_request(request)
    prefs = request.preferences.model_dump() if request.preferences else {}
    prefs["supermarket"] = request.supermarket
    result = generate_diet_from_recipes(user_profile, db, preferences=prefs)

    if result.status != "optimal":
        raise HTTPException(status_code=422, detail=_diagnose_infeasibility(user_profile, db))

    plan = _persist_plan(db, user_profile, result)
    _increment_diets_today(db, user)
    return _engine_result_to_response(result, plan)


def _filter_recipes_by_fridge(ingredients: list[str]) -> list[str]:
    """
    Devuelve nombres de recetas que se pueden hacer con los ingredientes dados.

    Reglas de matching por categoría:
    - grasa (aceite): siempre disponible, nunca bloquea.
    - proteina / lacteo / legumbre: OBLIGATORIO — el usuario debe tenerlo.
    - carbohidrato / verdura / fruta: condicional:
        · Si el usuario tiene ese ingrediente concreto → ok.
        · Si no lo tiene pero SÍ tiene otro de la misma categoría → bloquea.
        · Si el usuario no tiene NINGUNO de esa categoría → no bloquea.

    Normalización: se eliminan tildes antes de comparar para que "atun" matchee
    con "atún" y "brocoli" con "brócoli".
    """
    import unicodedata
    from app.engine.recipes import RECIPES

    ALWAYS_AVAILABLE = {"grasa"}
    SOFT_CATEGORIES  = {"carbohidrato", "verdura", "fruta"}

    # Términos genéricos → keywords específicas de recetas
    ALIASES: dict[str, list[str]] = {
        "pescado":   ["atun", "merluza", "salmon", "sardina", "bacalao", "gamba",
                      "gambones", "caballa", "surimi", "panga", "calamar", "sepia",
                      "pota", "berberecho", "almeja", "bonito"],
        "legumbres": ["lenteja", "garbanzo", "alubia", "judias"],
    }

    def _norm(s: str) -> str:
        return unicodedata.normalize("NFKD", s.lower()).encode("ascii", "ignore").decode("ascii")

    user_ings_raw = [_norm(i) for i in ingredients if i.strip()]
    user_ings: list[str] = []
    for u in user_ings_raw:
        user_ings.append(u)
        for alias in ALIASES.get(u, []):
            user_ings.append(_norm(alias))

    def _matches(kws: list[str], u: str) -> bool:
        return any(_norm(kw) in u or u in _norm(kw) for kw in kws)

    def _user_has_category(cat: str) -> bool:
        return any(
            _matches(i2.preferred_keywords, u)
            for r2 in RECIPES
            for i2 in r2.ingredients
            if i2.category == cat
            for u in user_ings
        )

    valid: list[str] = []
    for recipe in RECIPES:
        # Desayuno: los básicos de desayuno (leche, pan, avena, yogur) se asumen
        # siempre disponibles — el filtro de nevera aplica solo a comida y cena.
        if recipe.meal_type == "desayuno":
            valid.append(recipe.name)
            continue

        can_make = True
        for ing in recipe.ingredients:
            if ing.category in ALWAYS_AVAILABLE:
                continue

            found = any(_matches(ing.preferred_keywords, u) for u in user_ings)

            if ing.category in SOFT_CATEGORIES:
                if not found and _user_has_category(ing.category):
                    can_make = False
                    break
                continue

            # proteina / lacteo / legumbre — obligatorio en comida y cena
            if not found:
                can_make = False
                break

        if can_make:
            valid.append(recipe.name)
    return valid


@router.post(
    "/diet/fridge",
    response_model=DietResponse,
    status_code=201,
    summary="Genera una dieta con los ingredientes disponibles en casa",
)
def create_fridge_diet(
    request: FridgeRequest,
    db: Session = Depends(get_db),
    user: Optional[UserORM] = Depends(get_optional_user),
) -> DietResponse:
    """
    Filtra el catálogo de recetas para incluir solo las que pueden prepararse
    con los ingredientes indicados, luego genera la dieta con ese subconjunto.
    """
    from app.engine.recipes import RECIPES

    check_freemium_limits(db, user)

    valid_names = _filter_recipes_by_fridge(request.ingredients)

    if len(valid_names) < 3:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "No se encontraron suficientes recetas con esos ingredientes.",
                "suggestions": [
                    "Añade proteínas: pollo, carne, huevo o pescado",
                    "Añade carbohidratos: arroz, pasta o pan",
                    "Añade lácteos: leche o yogur para el desayuno",
                ],
            },
        )

    # Comprobar que hay al menos una receta por tipo de comida
    by_type: dict[str, list[str]] = {}
    for recipe in RECIPES:
        if recipe.name in valid_names:
            by_type.setdefault(recipe.meal_type, []).append(recipe.name)

    missing = [mt for mt in ("desayuno", "comida", "cena") if mt not in by_type]
    if missing:
        labels = {"desayuno": "desayuno", "comida": "comida principal", "cena": "cena"}
        names_str = " y ".join(labels[m] for m in missing)
        raise HTTPException(
            status_code=422,
            detail={
                "message": f"No hay recetas para {names_str} con esos ingredientes.",
                "suggestions": [
                    "Añade leche, yogur o avena para el desayuno",
                    "Añade una proteína principal (pollo, carne, pescado, legumbres) para comida y cena",
                ],
            },
        )

    # Excluir del motor todas las recetas que NO están disponibles
    all_names = {r.name for r in RECIPES}
    excluded = list(all_names - set(valid_names))

    user_profile = UserProfile(
        name=request.name,
        kcal_target=request.kcal_target,
        kcal_tolerance=0.15,
        min_protein_g=50.0,
        max_fat_g=100.0,
        budget_eur=request.budget_eur,
        min_carbs_g=80.0,
        max_carbs_g=400.0,
        min_portion_g=30.0,
        diversity_weight=0.3,
    )

    prefs = request.preferences.model_dump() if request.preferences else {}
    result = generate_diet_from_recipes(
        user_profile, db, excluded_recipe_names=excluded, preferences=prefs
    )

    if result.status != "optimal":
        raise HTTPException(
            status_code=422,
            detail={
                "message": f"No se pudo generar una dieta completa con {len(valid_names)} receta(s) disponible(s).",
                "suggestions": [
                    "Añade más ingredientes para ampliar las opciones",
                    "Prueba con ingredientes de base: arroz, aceite, verduras",
                ],
            },
        )

    plan = _persist_plan(db, user_profile, result)
    _increment_diets_today(db, user)
    return _engine_result_to_response(result, plan)


@router.post(
    "/diet/week/recipe",
    response_model=WeekPlanResponse,
    status_code=201,
    summary="Genera un plan semanal con recetas predefinidas sin repetición inmediata",
)
def create_week_recipe(
    request: UserProfileRequest,
    db: Session = Depends(get_db),
    user: Optional[UserORM] = Depends(get_optional_user),
) -> WeekPlanResponse:
    """
    Genera 7 días seleccionando recetas con ventana de exclusión diferenciada:

    - Desayuno: ventana de semana completa (excluye todos los desayunos ya usados
      esta semana) → los 7 desayunos son únicos siempre que haya ≥7 opciones.
    - Comida/Cena: ventana de 2 días (N-1 y N-2).

    Auto-relax por tipo: si tras aplicar la ventana ideal un tipo de comida se
    queda sin opciones, su ventana se reduce a 1 día, luego a 0.
    """
    check_freemium_limits(db, user, premium_only=True)
    from app.engine.recipes import build_recipe_lp_data

    days: list[DayDietResponse] = []

    # Historial completo por tipo (desayuno: toda la semana; comida/cena: últimos 2)
    history: dict[str, list[str]] = {"desayuno": [], "comida": [], "cena": []}
    # Historial de grupo proteíco para comida/cena (últimas 3 apariciones)
    # Se guarda el GRUPO (e.g. "gambas", "pollo") no el producto exacto
    protein_history: dict[str, list[str]] = {"comida": [], "cena": []}
    # Conteo semanal de grupos proteícos usados (Mejora 3)
    protein_week_count: dict[str, int] = {}

    # Ventana ideal por tipo: desayuno = semana entera, comida/cena = 2 días
    _WINDOW: dict[str, int] = {"desayuno": 7, "comida": 2, "cena": 2}
    _PROTEIN_WINDOW = 3  # días de exclusión de proteína repetida

    _prefs = request.preferences.model_dump() if request.preferences else {}
    _prefs["supermarket"] = request.supermarket

    # Mejora 3 — mapeo de grupos proteícos (coincide con recipes.py)
    _WEEK_PROT_GROUPS: list[tuple[str, list[str]]] = [
        ("gambas",  ["gambón", "gamba", "langostino"]),
        ("pollo",   ["pechuga", "pollo"]),
        ("atun",    ["atún", "atun", "bonito"]),
        ("huevo",   ["huevo", "clara"]),
        ("lacon",   ["lacón", "lacon"]),
        ("salmón",  ["salmón", "salmon"]),
        ("merluza", ["merluza"]),
        ("jamon",   ["jamón cocido", "jamón pavo"]),
        ("ternera", ["ternera", "vacuno", "carne picada", "burger"]),
        ("cerdo",   ["lomo de cerdo", "cerdo", "carrillada", "costilla"]),
        ("sardina", ["sardina", "caballa"]),
        ("bacalao", ["bacalao"]),
    ]

    def _prot_group_key(prot_name: str) -> str:
        pl = prot_name.lower()
        for grp, kws in _WEEK_PROT_GROUPS:
            if any(kw in pl for kw in kws):
                return grp
        return pl[:18]

    # Cache de recipe_data para no recalcular en cada iteración
    _recipe_data_cache: dict | None = None

    def _get_recipe_data():
        nonlocal _recipe_data_cache
        if _recipe_data_cache is None:
            _recipe_data_cache = build_recipe_lp_data(db, request.kcal_target, preferences=_prefs)
        return _recipe_data_cache

    def _build_exclusion(windows: dict[str, int]) -> set[str]:
        excl: set[str] = set()
        for mt, w in windows.items():
            excl.update(history[mt][-w:] if w > 0 else [])
        # Excluir recetas cuyo GRUPO proteíco apareció en los últimos N días
        recent_prot_groups: set[str] = set()
        for mt in ("comida", "cena"):
            recent_prot_groups.update(
                g for g in protein_history[mt][-_PROTEIN_WINDOW:] if g
            )
        # Mejora 3 — excluir también grupos que ya se usaron ≥3 veces esta semana
        overused_groups = {g for g, cnt in protein_week_count.items() if cnt >= 3}
        all_blocked_groups = recent_prot_groups | overused_groups
        if all_blocked_groups:
            for mt, rds in _get_recipe_data().items():
                if mt == "desayuno":
                    continue
                for rd in rds:
                    if _prot_group_key(rd.main_protein) in all_blocked_groups:
                        excl.add(rd.recipe.name)
        return excl

    def _counts(excluded: set[str]) -> dict[str, int]:
        return {
            mt: sum(1 for rd in rds if rd.recipe.name not in excluded)
            for mt, rds in _get_recipe_data().items()
        }

    for day_idx in range(7):
        # Determinar ventana efectiva por tipo con auto-relax
        effective_windows = dict(_WINDOW)
        excl = _build_exclusion(effective_windows)
        c = _counts(excl)

        for mt in ("desayuno", "comida", "cena"):
            if c[mt] >= 1:
                continue
            # Relajar este tipo de comida paso a paso
            for fallback_w in (2, 1, 0):
                if fallback_w < effective_windows[mt]:
                    effective_windows[mt] = fallback_w
                    excl = _build_exclusion(effective_windows)
                    c = _counts(excl)
                    if c[mt] >= 1:
                        break

        user_profile = _user_from_request(request)
        recent = [r for recipes in history.values() for r in recipes]
        result = generate_diet_from_recipes(user_profile, db, excluded_recipe_names=list(excl), recent_recipe_names=recent, preferences=_prefs)

        if result.status != "optimal":
            diag = _diagnose_infeasibility(user_profile, db)
            diag["message"] = f"{_DAYS_ES[day_idx]}: {diag['message']}"
            raise HTTPException(status_code=422, detail=diag)

        plan = _persist_plan(db, user_profile, result)
        diet_response = _engine_result_to_response(result, plan)
        days.append(DayDietResponse(day=_DAYS_ES[day_idx], day_index=day_idx, diet=diet_response))

        # Actualizar historial de recetas (desayuno: ilimitado; comida/cena: últimas 2)
        for meal_type, recipe_name in result.recipe_names_by_meal.items():
            history[meal_type].append(recipe_name)
            if meal_type != "desayuno" and len(history[meal_type]) > 2:
                history[meal_type].pop(0)
        # Actualizar historial de proteínas por grupo (comida/cena: últimas 3)
        for meal_type in ("comida", "cena"):
            prot = result.proteins_by_meal.get(meal_type, "")
            if prot:
                grp = _prot_group_key(prot)
                protein_history[meal_type].append(grp)
                if len(protein_history[meal_type]) > _PROTEIN_WINDOW:
                    protein_history[meal_type].pop(0)
                # Mejora 3 — acumular conteo semanal por grupo
                protein_week_count[grp] = protein_week_count.get(grp, 0) + 1

    return WeekPlanResponse(user_name=request.name, days=days)


@router.post(
    "/diet/week/shopping-list",
    response_model=ShoppingListResponse,
    summary="Lista de la compra para un plan semanal",
)
async def shopping_list(week: WeekPlanResponse, db: Session = Depends(get_db)) -> ShoppingListResponse:
    """
    Recibe un WeekPlanResponse y calcula la lista de la compra semanal.

    Incluye TODOS los productos usados en la semana:
    - Con datos de envase: coste = ceil(gramos / package_size_g) × package_price_eur
    - Sin datos de envase: coste estimado = price_per_100g × total_grams / 100
                           (cost_is_estimated=True)
    """
    # ── Sumar gramos totales por producto ─────────────────────────────
    grams_total: dict[str, float] = {}
    category_of: dict[str, str] = {}
    for day in week.days:
        for meal in day.diet.meals:
            for item in meal.items:
                grams_total[item.product] = grams_total.get(item.product, 0.0) + item.grams
                category_of[item.product] = item.category

    # ── Cargar ProductORM por nombre ──────────────────────────────────
    product_names = list(grams_total.keys())
    db_products: dict[str, ProductORM] = {
        p.name: p
        for p in db.query(ProductORM).filter(ProductORM.name.in_(product_names)).all()
    }

    # ── Punto 5 opcional: intentar rellenar package_size_g faltante ───
    # Busca en ProductPendingORM productos con mismo EAN que algún ProductORM sin envase,
    # y si encuentra mercadona_id cruza con la tabla para rellenar en caliente.
    # No persiste cambios — solo enriquece la respuesta de esta llamada.
    missing_pkg = [
        p for p in db_products.values()
        if p.package_size_g is None and p.ean
    ]
    if missing_pkg:
        missing_eans = {p.ean for p in missing_pkg}
        from app.models.diet import ProductPendingORM
        pending_by_ean = {
            row.ean: row
            for row in db.query(ProductPendingORM)
            .filter(ProductPendingORM.ean.in_(missing_eans))
            .all()
            if row.ean
        }
        # Intentar obtener datos de envase desde Mercadona en tiempo real
        # Solo si hay pocos productos (evitar latencia excesiva en la respuesta)
        if pending_by_ean and len(pending_by_ean) <= 20:
            import asyncio as _asyncio
            import httpx as _httpx
            _TO_GRAMS = {"kg": 1000.0, "l": 1000.0, "g": 1.0, "ml": 1.0, "cl": 10.0}
            async with _httpx.AsyncClient(
                headers={"Accept-Language": "es", "User-Agent": "CalorIA/0.1"},
                timeout=5,
            ) as _client:
                for ean, pending_row in pending_by_ean.items():
                    mid = pending_row.mercadona_id
                    if not mid:
                        continue
                    try:
                        r = await _client.get(f"https://tienda.mercadona.es/api/products/{mid}/")
                        if r.status_code != 200:
                            continue
                        pi = r.json().get("price_instructions", {})
                        fmt = (pi.get("size_format") or "").lower()
                        factor = _TO_GRAMS.get(fmt)
                        if factor and pi.get("unit_size") and pi.get("unit_price"):
                            pkg_g = round(float(pi["unit_size"]) * factor, 1)
                            pkg_eur = round(float(pi["unit_price"]), 2)
                            for p in missing_pkg:
                                if p.ean == ean:
                                    p.package_size_g = pkg_g
                                    p.package_price_eur = pkg_eur
                        await _asyncio.sleep(0.3)
                    except Exception:
                        continue

    # ── Construir items de la lista ───────────────────────────────────
    items_by_category: dict[str, list[ShoppingListItem]] = {}
    total_cost = 0.0
    estimated_count = 0

    for name, grams in sorted(grams_total.items()):
        p = db_products.get(name)
        cat = category_of.get(name, p.category if p else "otros")

        sm = p.supermarket if p else "mercadona"
        if p and p.package_size_g and p.package_price_eur:
            # Coste real por envases
            packages = math.ceil(grams / p.package_size_g)
            cost = round(packages * p.package_price_eur, 2)
            item = ShoppingListItem(
                product_name=name,
                category=cat,
                supermarket=sm,
                total_grams_needed=round(grams, 0),
                package_size_g=p.package_size_g,
                packages_to_buy=packages,
                package_price_eur=p.package_price_eur,
                total_cost_eur=cost,
                cost_is_estimated=False,
            )
        else:
            # Coste estimado por price_per_100g
            price_100g = p.price_per_100g if p else 0.0
            cost = round(price_100g * grams / 100, 2)
            estimated_count += 1
            item = ShoppingListItem(
                product_name=name,
                category=cat,
                supermarket=sm,
                total_grams_needed=round(grams, 0),
                package_size_g=None,
                packages_to_buy=None,
                package_price_eur=None,
                total_cost_eur=cost,
                cost_is_estimated=True,
            )

        total_cost += cost
        items_by_category.setdefault(cat, []).append(item)

    # Ordenar cada categoría: primero reales (coste desc), luego estimados
    for cat in items_by_category:
        items_by_category[cat].sort(key=lambda x: (x.cost_is_estimated, -x.total_cost_eur))

    return ShoppingListResponse(
        total_cost_eur=round(total_cost, 2),
        estimated_items_count=estimated_count,
        items_by_category=items_by_category,
    )


@router.get("/ml/training-data", response_model=list[MLTrainingRecord], summary="Datos de entrenamiento ML")
def ml_training_data(db: Session = Depends(get_db)) -> list[MLTrainingRecord]:
    """
    Devuelve registros de dietas valoradas (rating IS NOT NULL) con contexto
    por comida para entrenar un modelo de recomendación de recetas.

    Cada fila representa una comida dentro de una dieta valorada.
    Solo se incluyen comidas con recipe_name guardado (recetas mode).
    """
    from sqlalchemy import func as sqlfunc

    # Aggregate meal-level stats from DietMealORM rows
    stmt = (
        db.query(
            DietMealORM.plan_id,
            DietMealORM.meal_name,
            DietMealORM.recipe_name,
            sqlfunc.sum(DietMealORM.kcal).label("meal_kcal"),
            sqlfunc.sum(DietMealORM.cost_eur).label("meal_cost_eur"),
        )
        .filter(DietMealORM.recipe_name.isnot(None))
        .group_by(DietMealORM.plan_id, DietMealORM.meal_name, DietMealORM.recipe_name)
        .subquery()
    )

    rows = (
        db.query(
            DietPlanORM.id.label("diet_id"),
            DietPlanORM.rating,
            DietPlanORM.kcal_target,
            DietPlanORM.budget_eur,
            stmt.c.meal_name,
            stmt.c.recipe_name,
            stmt.c.meal_kcal,
            stmt.c.meal_cost_eur,
        )
        .join(stmt, stmt.c.plan_id == DietPlanORM.id)
        .filter(DietPlanORM.rating.isnot(None))
        .order_by(DietPlanORM.id)
        .all()
    )

    return [
        MLTrainingRecord(
            diet_id=r.diet_id,
            rating=r.rating,
            kcal_target=r.kcal_target,
            budget_eur=r.budget_eur,
            meal_type=r.meal_name,
            recipe_name=r.recipe_name,
            meal_kcal=round(r.meal_kcal, 1),
            meal_cost_eur=round(r.meal_cost_eur, 3),
        )
        for r in rows
    ]


@router.post(
    "/diet/{diet_id}/meal/{meal_name}/swap",
    response_model=MealResponse,
    summary="Regenera una comida específica de una dieta",
)
def swap_meal(
    diet_id: int,
    meal_name: str,
    request: UserProfileRequest,
    db: Session = Depends(get_db),
    user: Optional[UserORM] = Depends(get_optional_user),
) -> MealResponse:
    """
    Regenera una sola comida (desayuno / comida / cena) de una dieta existente,
    excluyendo la receta actual para garantizar variedad.
    """
    check_freemium_limits(db, user)

    current = db.query(DietMealORM).filter(
        DietMealORM.plan_id == diet_id,
        DietMealORM.meal_name == meal_name,
    ).first()
    excluded = [current.recipe_name] if current and current.recipe_name else []

    user_profile = _user_from_request(request)
    prefs = request.preferences.model_dump() if request.preferences else {}
    prefs["supermarket"] = request.supermarket

    result = generate_diet_from_recipes(
        user_profile, db, excluded_recipe_names=excluded, preferences=prefs,
    )

    if result.status != "optimal" or meal_name not in result.meal_plan:
        raise HTTPException(
            status_code=422,
            detail={"message": f"No se pudo generar una nueva receta para '{meal_name}'"},
        )

    # Reemplazar filas del meal en BD
    db.query(DietMealORM).filter(
        DietMealORM.plan_id == diet_id,
        DietMealORM.meal_name == meal_name,
    ).delete()

    new_recipe = result.recipe_names_by_meal.get(meal_name, "")
    new_items  = result.meal_plan[meal_name]
    for pname, grams in new_items.items():
        if grams <= 0.5:
            continue
        p = result.products_ref.get(pname)
        if not p:
            continue
        db.add(DietMealORM(
            plan_id=diet_id, meal_name=meal_name, recipe_name=new_recipe,
            product_name=pname, category=p.category,
            grams=round(grams, 1),
            kcal=round(p.kcal_per_gram * grams, 1),
            cost_eur=round(p.price_per_gram * grams, 3),
        ))
    db.commit()

    items = [
        MealItemResponse(
            product=pname, category=result.products_ref[pname].category,
            grams=round(grams, 1),
            kcal=round(result.products_ref[pname].kcal_per_gram * grams, 1),
            cost_eur=round(result.products_ref[pname].price_per_gram * grams, 3),
        )
        for pname, grams in sorted(new_items.items(), key=lambda x: -x[1])
        if grams > 0.5 and pname in result.products_ref
    ]
    recipe_obj = (
        result.recipes_by_meal.get(meal_name)
        or RECIPES_BY_NAME.get(new_recipe)
    )
    meal_cfg   = next((m for m in result.user.meals if m.name == meal_name), None)

    return MealResponse(
        name=meal_name,
        recipe_name=new_recipe or name_meal(items),
        kcal_target_pct=meal_cfg.kcal_fraction if meal_cfg else _MEAL_FRACTIONS.get(meal_name, 0.0),
        kcal_actual=round(sum(i.kcal for i in items), 1),
        cost_eur=round(sum(i.cost_eur for i in items), 3),
        items=items,
        instructions=recipe_obj.instructions if recipe_obj else [],
        prep_time_min=recipe_obj.prep_time_min if recipe_obj else 15,
        image_url=get_recipe_image(new_recipe) if new_recipe else "",
    )


@router.get("/health", response_model=HealthResponse, summary="Healthcheck")
def health_check() -> HealthResponse:
    return HealthResponse(status="ok")

