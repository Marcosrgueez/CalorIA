from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class UserORM(Base):
    __tablename__ = "users"

    id:             Mapped[int]           = mapped_column(Integer, primary_key=True)
    email:          Mapped[str]           = mapped_column(String, unique=True, nullable=False, index=True)
    username:       Mapped[str]           = mapped_column(String, unique=True, nullable=False, index=True)
    password_hash:  Mapped[str]           = mapped_column(String, nullable=False)
    plan:           Mapped[str]           = mapped_column(String, nullable=False, default="free")
    created_at:     Mapped[datetime]      = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    diets_today:    Mapped[int]           = mapped_column(Integer, nullable=False, default=0)
    last_diet_date: Mapped[str | None]    = mapped_column(String, nullable=True)


class ProductORM(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    category: Mapped[str] = mapped_column(String, nullable=False)
    price_per_100g: Mapped[float] = mapped_column(Float, nullable=False)
    kcal_per_100g: Mapped[float] = mapped_column(Float, nullable=False)
    protein_per_100g: Mapped[float] = mapped_column(Float, nullable=False)
    fat_per_100g: Mapped[float] = mapped_column(Float, nullable=False)
    carbs_per_100g: Mapped[float] = mapped_column(Float, nullable=False)
    max_grams_per_day: Mapped[float] = mapped_column(Float, nullable=False, default=500.0)
    min_grams_per_day: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    # Información de envase (para calcular coste real de compra)
    package_size_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    package_price_eur: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Trazabilidad del origen del dato
    ean: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    source: Mapped[str] = mapped_column(String, nullable=False, default="manual")
    supermarket: Mapped[str] = mapped_column(String, nullable=False, default="mercadona")
    scraped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ProductPendingORM(Base):
    """
    Productos de Mercadona que no pudieron enriquecerse con macros.
    Fuentes de enriquecimiento posterior: OpenFoodFacts manual, edición admin.

    Motivos típicos (campo `reason`):
      - "off_not_found"      : EAN no encontrado en OpenFoodFacts
      - "off_incomplete"     : OpenFoodFacts no tiene todos los macros
      - "price_not_per_kg"   : referencia de precio no es kg/l (ej: ud, dz)
    """
    __tablename__ = "products_pending"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mercadona_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    ean: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    mercadona_category: Mapped[str] = mapped_column(String, nullable=False)
    internal_category: Mapped[str | None] = mapped_column(String, nullable=True)
    price_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    reason: Mapped[str] = mapped_column(String, nullable=False)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class DietPlanORM(Base):
    __tablename__ = "diet_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    status: Mapped[str] = mapped_column(String, nullable=False)
    kcal_target: Mapped[float] = mapped_column(Float, nullable=False)
    budget_eur: Mapped[float] = mapped_column(Float, nullable=False)
    total_kcal: Mapped[float] = mapped_column(Float, nullable=False)
    total_protein_g: Mapped[float] = mapped_column(Float, nullable=False)
    total_fat_g: Mapped[float] = mapped_column(Float, nullable=False)
    total_carbs_g: Mapped[float] = mapped_column(Float, nullable=False)
    total_cost_eur: Mapped[float] = mapped_column(Float, nullable=False)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1=positivo, -1=negativo

    meals: Mapped[list["DietMealORM"]] = relationship(
        "DietMealORM", back_populates="plan", cascade="all, delete-orphan"
    )


class DietMealORM(Base):
    __tablename__ = "diet_meals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("diet_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    meal_name: Mapped[str] = mapped_column(String, nullable=False)
    recipe_name: Mapped[str | None] = mapped_column(String, nullable=True)  # nombre canónico de receta
    product_name: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    grams: Mapped[float] = mapped_column(Float, nullable=False)
    kcal: Mapped[float] = mapped_column(Float, nullable=False)
    cost_eur: Mapped[float] = mapped_column(Float, nullable=False)

    plan: Mapped["DietPlanORM"] = relationship("DietPlanORM", back_populates="meals")
