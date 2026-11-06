"""
Entrena un modelo ML de recomendación de recetas para CalorIA.

Fuente de datos: GET /ml/training-data (requiere que el servidor esté corriendo).
Algoritmo: GradientBoostingClassifier (scikit-learn).
Salida: models/recipe_recommender.pkl

Uso:
    python scripts/train_model.py
    python scripts/train_model.py --url http://localhost:8000 --min-samples 5

El modelo predice si una receta gustará (rating=1) o no (rating=-1) en función
del contexto del usuario y las características de la comida.
"""

from __future__ import annotations

import argparse
import os
import sys

import joblib
import numpy as np
import requests
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import LabelEncoder

# ─────────────────────────────────────────────
# Configuración por defecto
# ─────────────────────────────────────────────

DEFAULT_URL = "http://localhost:8001"
MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "models")
MODEL_PATH = os.path.join(MODELS_DIR, "recipe_recommender.pkl")


def fetch_training_data(base_url: str) -> list[dict]:
    url = f"{base_url.rstrip('/')}/ml/training-data"
    print(f"  Obteniendo datos de {url} ...")
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.json()


def build_features(records: list[dict], recipe_enc: LabelEncoder, meal_enc: LabelEncoder) -> np.ndarray:
    """Convierte la lista de registros en una matriz de features numpy."""
    X = []
    for r in records:
        recipe_idx = (
            recipe_enc.transform([r["recipe_name"]])[0]
            if r["recipe_name"] in recipe_enc.classes_
            else -1
        )
        meal_idx = (
            meal_enc.transform([r["meal_type"]])[0]
            if r["meal_type"] in meal_enc.classes_
            else -1
        )
        X.append([
            r["kcal_target"],
            r["budget_eur"],
            meal_idx,
            recipe_idx,
            r["meal_kcal"],
            r["meal_cost_eur"],
        ])
    return np.array(X, dtype=float)


def main(base_url: str, min_samples: int) -> None:
    # ── 1. Obtener datos ──────────────────────────────────────────────
    print("\n[1/5] Descargando datos de entrenamiento...")
    records = fetch_training_data(base_url)

    if not records:
        print("  No hay registros de entrenamiento. Genera dietas y valóralas con 👍/👎.")
        sys.exit(1)

    print(f"  {len(records)} registros obtenidos.")

    # Filtrar registros sin recipe_name (no debería ocurrir, pero por seguridad)
    records = [r for r in records if r.get("recipe_name")]

    # ── 2. Construir encoders ─────────────────────────────────────────
    print("\n[2/5] Codificando variables categóricas...")
    recipe_enc = LabelEncoder().fit([r["recipe_name"] for r in records])
    meal_enc   = LabelEncoder().fit([r["meal_type"]   for r in records])

    unique_recipes = len(recipe_enc.classes_)
    print(f"  {unique_recipes} recetas únicas | {len(meal_enc.classes_)} tipos de comida")

    # ── 3. Preparar X, y ─────────────────────────────────────────────
    print("\n[3/5] Preparando features y etiquetas...")
    X = build_features(records, recipe_enc, meal_enc)
    # Convertir rating (-1, 1) → etiqueta binaria (0, 1)
    y = np.array([1 if r["rating"] == 1 else 0 for r in records])

    n_pos = int(y.sum())
    n_neg = int((y == 0).sum())
    print(f"  Positivos: {n_pos} | Negativos: {n_neg}")

    if n_pos < min_samples or n_neg < min_samples:
        print(
            f"\n  ATENCIÓN: Se necesitan al menos {min_samples} ejemplos de cada clase.\n"
            f"  Valora más dietas antes de entrenar.\n"
            f"  (Positivos: {n_pos}, Negativos: {n_neg})"
        )
        sys.exit(1)

    # ── 4. Entrenar y evaluar ─────────────────────────────────────────
    print("\n[4/5] Entrenando GradientBoostingClassifier...")
    clf = GradientBoostingClassifier(
        n_estimators=100,
        max_depth=3,
        learning_rate=0.1,
        subsample=0.8,
        random_state=42,
    )

    # Cross-validation si hay suficientes datos
    if len(records) >= 10:
        n_splits = min(5, n_pos, n_neg)
        if n_splits >= 2:
            skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
            scores = cross_val_score(clf, X, y, cv=skf, scoring="roc_auc")
            print(f"  ROC-AUC CV ({n_splits}-fold): {scores.mean():.3f} ± {scores.std():.3f}")

    clf.fit(X, y)

    # Métricas en train (referencia)
    y_pred = clf.predict(X)
    y_proba = clf.predict_proba(X)[:, 1]
    print("\n  Reporte en datos de entrenamiento:")
    print(classification_report(y, y_pred, target_names=["no_gustó", "gustó"], zero_division=0))
    if n_pos >= 2 and n_neg >= 2:
        print(f"  ROC-AUC (train): {roc_auc_score(y, y_proba):.3f}")

    # Feature importances
    feature_names = ["kcal_target", "budget_eur", "meal_type", "recipe_name", "meal_kcal", "meal_cost_eur"]
    print("\n  Importancias de features:")
    for name, imp in sorted(zip(feature_names, clf.feature_importances_), key=lambda x: -x[1]):
        bar = "█" * int(imp * 40)
        print(f"    {name:<20} {imp:.3f}  {bar}")

    # ── 5. Guardar modelo ─────────────────────────────────────────────
    print(f"\n[5/5] Guardando modelo en {MODEL_PATH} ...")
    os.makedirs(MODELS_DIR, exist_ok=True)
    bundle = {
        "model":          clf,
        "recipe_encoder": recipe_enc,
        "meal_encoder":   meal_enc,
        "feature_names":  feature_names,
        "n_train":        len(records),
    }
    joblib.dump(bundle, MODEL_PATH)
    print(f"  Modelo guardado. ({len(records)} muestras, {unique_recipes} recetas)")

    print("\n✓ Entrenamiento completado. Reinicia el servidor para aplicar el nuevo modelo.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Entrena el modelo ML de CalorIA")
    parser.add_argument("--url", default=DEFAULT_URL, help="URL base del servidor FastAPI")
    parser.add_argument("--min-samples", type=int, default=3,
                        help="Mínimo de ejemplos por clase requeridos (default: 3)")
    args = parser.parse_args()

    main(args.url, args.min_samples)
