import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.products import router as products_router
from app.api.routes import router
from app.api.scan import router as scan_router
from app.db.seed import seed_products
from app.db.session import SessionLocal, engine
from app.models.diet import Base


def _apply_migrations() -> None:
    """Añade columnas nuevas a tablas existentes (migración manual sin Alembic)."""
    _migrations = [
        "ALTER TABLE diet_plans ADD COLUMN rating INTEGER",
        "ALTER TABLE diet_meals ADD COLUMN recipe_name TEXT",
        "ALTER TABLE products ADD COLUMN supermarket TEXT DEFAULT 'mercadona'",
    ]
    with engine.connect() as conn:
        for stmt in _migrations:
            try:
                conn.execute(text(stmt))
                conn.commit()
            except Exception:
                # Columna ya existe — ignorar
                pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Crea tablas si no existen.
    # TODO: reemplazar con `alembic upgrade head` cuando el esquema se estabilice
    # y haya datos de producción que proteger.
    Base.metadata.create_all(bind=engine)
    _apply_migrations()
    db = SessionLocal()
    try:
        seed_products(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="CalorIA API",
    description=(
        "Generador de dietas personalizadas optimizadas por nutrición y precio "
        "usando datos de supermercados españoles."
    ),
    version="0.2.0",
    lifespan=lifespan,
)

_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:3000",
    "http://localhost:8001",
    "http://localhost:8002",
    "http://localhost:8003",
]
if _extra := os.environ.get("EXTRA_CORS_ORIGINS"):
    _CORS_ORIGINS.extend(o.strip() for o in _extra.split(",") if o.strip())

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_origin_regex=r"https://.*\.devtunnels\.ms",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

app.include_router(auth_router)
app.include_router(router)
app.include_router(products_router)
app.include_router(scan_router)
app.include_router(chat_router, prefix="/api")

# Servir el frontend React (build de producción) — debe ir al final como catch-all
_FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.exists(_FRONTEND_DIST):
    from fastapi import Request
    from fastapi.responses import FileResponse

    # index.html sin caché — los assets llevan hash de contenido y se cachean solos
    @app.get("/")
    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str = ""):
        # Rutas de API y static las maneja el router antes de llegar aquí
        index = os.path.join(_FRONTEND_DIST, "index.html")
        assets = os.path.join(_FRONTEND_DIST, full_path)
        if full_path and os.path.isfile(assets):
            return FileResponse(assets)
        return FileResponse(
            index,
            headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
        )
