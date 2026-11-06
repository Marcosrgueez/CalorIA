"""
Esquemas Pydantic para la API de CalorIA.

Separados intencionalmente de las dataclasses del motor:
- El motor (diet_engine) es agnóstico de FastAPI y testeable de forma aislada.
- Estos schemas viven en la frontera HTTP: validan entrada y serializan salida.
"""

from datetime import datetime

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────
# REQUEST
# ─────────────────────────────────────────────

class UserPreferences(BaseModel):
    proteins:     list[str] = Field(default_factory=list, description="Proteínas preferidas: fish, chicken, red_meat, legumes")
    restrictions: list[str] = Field(default_factory=list, description="Restricciones: none|gluten_free|lactose_free|egg_free|fish_free|nut_free|pork_free|vegetarian|vegan")
    breakfast:    str       = Field("varied", description="Desayuno preferido: oats, toast, yogur, varied")


class FridgeRequest(BaseModel):
    name: str = "Usuario"
    ingredients: list[str]          # ["pollo", "arroz", "tomate", "huevo"]
    kcal_target: float = 2000
    budget_eur: float = 10.0
    preferences: UserPreferences | None = None


class UserProfileRequest(BaseModel):
    name: str = Field(..., min_length=1, examples=["Carlos"])
    kcal_target: float = Field(..., gt=0, description="Calorías objetivo por día", examples=[1800])
    kcal_tolerance: float = Field(0.05, ge=0.0, le=0.20, description="Tolerancia calórica ±%")
    min_protein_g: float = Field(50.0, ge=0.0, description="Proteína mínima diaria en gramos")
    max_fat_g: float = Field(80.0, ge=0.0, description="Grasa máxima diaria en gramos")
    budget_eur: float = Field(5.0, gt=0.0, description="Presupuesto diario en euros")
    min_carbs_g: float = Field(100.0, ge=0.0, description="Carbohidratos mínimos diarios en gramos")
    max_carbs_g: float = Field(350.0, ge=0.0, description="Carbohidratos máximos diarios en gramos")
    min_portion_g: float = Field(30.0, ge=0.0, description="Gramos mínimos por producto por comida (0 = LP puro)")
    diversity_weight: float = Field(0.5, ge=0.0, le=5.0, description="λ penalización de diversidad (0 = solo coste, QP desactivado)")
    preferences: UserPreferences | None = Field(None, description="Preferencias alimentarias del usuario")
    supermarket: str = Field("mercadona", description="Supermercado origen: mercadona | carrefour | todos")


# ─────────────────────────────────────────────
# RESPONSE — bloques anidados
# ─────────────────────────────────────────────

class MealItemResponse(BaseModel):
    product: str
    category: str
    grams: float
    kcal: float
    cost_eur: float


class MealResponse(BaseModel):
    name: str
    recipe_name: str = ""    # nombre cosmético generado automáticamente
    kcal_target_pct: float   # fracción del total, ej: 0.25
    kcal_actual: float
    cost_eur: float
    items: list[MealItemResponse]
    instructions: list[str] = []
    prep_time_min: int = 15
    image_url: str = ""


class MacrosResponse(BaseModel):
    kcal: float
    protein_g: float
    fat_g: float
    carbs_g: float
    cost_eur: float


class DietResponse(BaseModel):
    diet_id: int
    created_at: datetime
    status: str
    user_name: str
    macros: MacrosResponse
    meals: list[MealResponse]
    rating: int | None = None


# ─────────────────────────────────────────────
# RESPONSE — plan semanal
# ─────────────────────────────────────────────

class DayDietResponse(BaseModel):
    day: str               # "Lunes", "Martes", …
    day_index: int         # 0-6
    diet: DietResponse


class WeekPlanResponse(BaseModel):
    user_name: str
    days: list[DayDietResponse]


# ─────────────────────────────────────────────
# RESPONSE — lista de la compra semanal
# ─────────────────────────────────────────────

class ShoppingListItem(BaseModel):
    product_name: str
    category: str
    supermarket: str                    # "mercadona", "carrefour", etc.
    total_grams_needed: float
    package_size_g: float | None        # None si no hay datos de envase
    packages_to_buy: int | None         # None si no hay datos de envase
    package_price_eur: float | None     # None si no hay datos de envase
    total_cost_eur: float               # real o estimado (price_per_100g × gramos)
    cost_is_estimated: bool             # True cuando no hay datos de envase


class ShoppingListResponse(BaseModel):
    total_cost_eur: float
    estimated_items_count: int          # nº de productos con coste estimado
    items_by_category: dict[str, list[ShoppingListItem]]


# ─────────────────────────────────────────────
# RESPONSE — catálogo de productos
# ─────────────────────────────────────────────

class ProductResponse(BaseModel):
    name: str
    category: str
    price_per_100g: float
    kcal_per_100g: float
    protein_per_100g: float
    fat_per_100g: float
    carbs_per_100g: float
    max_grams_per_day: float


# ─────────────────────────────────────────────
# RESPONSE — listado de historial
# ─────────────────────────────────────────────

class DietSummaryResponse(BaseModel):
    diet_id: int
    created_at: datetime
    user_name: str
    kcal_target: float
    total_kcal: float
    total_protein: float
    total_cost: float
    status: str
    rating: int | None = None


class RatingResponse(BaseModel):
    diet_id: int
    rating: int


# ─────────────────────────────────────────────
# RESPONSE — healthcheck
# ─────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str


# ─────────────────────────────────────────────
# RESPONSE — ML training data
# ─────────────────────────────────────────────

class MLTrainingRecord(BaseModel):
    diet_id: int
    rating: int              # 1 = positivo, -1 = negativo
    kcal_target: float
    budget_eur: float
    meal_type: str           # desayuno | comida | cena
    recipe_name: str
    meal_kcal: float
    meal_cost_eur: float
