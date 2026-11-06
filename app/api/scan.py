"""Scan endpoints — barcode, photo, fridge, label."""
import base64
import json
import os

from fastapi import APIRouter, File, HTTPException, UploadFile
from groq import AsyncGroq

router = APIRouter(prefix="/scan", tags=["scan"])

_VISION_MODEL = "llama-3.2-11b-vision-preview"
_TEXT_MODEL   = "llama-3.3-70b-versatile"


def _groq() -> AsyncGroq:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY no configurada")
    return AsyncGroq(api_key=api_key)


def _parse_json(text: str) -> dict:
    text = text.strip().strip("`")
    if text.startswith("json"):
        text = text[4:]
    return json.loads(text)


@router.post("/barcode", summary="Busca un producto por código de barras en OpenFoodFacts")
async def scan_barcode(barcode: str):
    import httpx
    try:
        async with httpx.AsyncClient(headers={"User-Agent": "CalorIA/1.0"}, timeout=10) as client:
            r = await client.get(f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="OpenFoodFacts tardó demasiado. Inténtalo de nuevo.")

    if r.status_code != 200 or r.json().get("status") != 1:
        raise HTTPException(status_code=404, detail="Producto no encontrado en la base de datos")

    product    = r.json()["product"]
    nutriments = product.get("nutriments", {})
    return {
        "found":    True,
        "barcode":  barcode,
        "name":     product.get("product_name") or product.get("product_name_es") or "Producto desconocido",
        "brand":    product.get("brands", ""),
        "image_url": product.get("image_front_small_url", ""),
        "quantity": product.get("quantity", ""),
        "nutriscore": (product.get("nutriscore_grade") or "").upper(),
        "macros_per_100g": {
            "kcal":    round(float(nutriments.get("energy-kcal_100g") or 0), 1),
            "protein": round(float(nutriments.get("proteins_100g")    or 0), 1),
            "fat":     round(float(nutriments.get("fat_100g")         or 0), 1),
            "carbs":   round(float(nutriments.get("carbohydrates_100g") or 0), 1),
            "fiber":   round(float(nutriments.get("fiber_100g")       or 0), 1),
            "sugar":   round(float(nutriments.get("sugars_100g")      or 0), 1),
            "salt":    round(float(nutriments.get("salt_100g")        or 0), 1),
        },
        "ingredients": product.get("ingredients_text_es") or product.get("ingredients_text", ""),
        "allergens": [a.replace("en:", "").replace("es:", "") for a in product.get("allergens_tags", [])],
    }


@router.post("/photo", summary="Analiza una foto de un plato con Groq Vision y estima los macros")
async def scan_photo(file: UploadFile = File(...)):
    image_b64  = base64.standard_b64encode(await file.read()).decode("utf-8")
    media_type = file.content_type or "image/jpeg"
    client     = _groq()

    prompt = """Analiza esta foto de comida y estima los macronutrientes.

Responde ÚNICAMENTE con un JSON válido con esta estructura exacta (sin texto adicional):
{
  "dish_name": "nombre del plato en español",
  "confidence": "alta|media|baja",
  "estimated_grams": 400,
  "calories": 520,
  "protein_g": 35,
  "fat_g": 18,
  "carbs_g": 45,
  "fiber_g": 6,
  "ingredients_detected": ["pollo", "arroz", "brócoli"],
  "notes": "estimación basada en porción estándar visible"
}

Si no puedes identificar comida responde: {"error": "No se detectó comida en la imagen"}

Sé conservador. Considera el plato como referencia estándar de 26cm."""

    try:
        response = await client.chat.completions.create(
            model=_VISION_MODEL,
            messages=[{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{image_b64}"}},
                {"type": "text", "text": prompt},
            ]}],
            max_tokens=512, temperature=0.1,
        )
        result = _parse_json(response.choices[0].message.content)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return {"found": True, "source": "groq_vision", **result}
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Error al procesar la respuesta de la IA")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/fridge", summary="Detecta ingredientes de una foto de nevera y sugiere recetas")
async def scan_fridge(file: UploadFile = File(...)):
    image_b64  = base64.standard_b64encode(await file.read()).decode("utf-8")
    media_type = file.content_type or "image/jpeg"
    client     = _groq()

    try:
        r1 = await client.chat.completions.create(
            model=_VISION_MODEL,
            messages=[{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{image_b64}"}},
                {"type": "text", "text": (
                    "Analiza esta foto de una nevera o despensa y lista todos los alimentos visibles.\n\n"
                    'Responde ÚNICAMENTE con un JSON válido:\n'
                    '{\n  "ingredients": ["pollo", "huevos", "leche", "tomate"],\n'
                    '  "confidence": "alta|media|baja",\n  "notes": "observación si procede"\n}\n\n'
                    'Si no ves una nevera o alimentos responde: {"error": "No se detectaron alimentos"}\n\n'
                    "Lista solo ingredientes claramente identificables. Usa nombres simples en español."
                )},
            ]}],
            max_tokens=256, temperature=0.1,
        )
        detection = _parse_json(r1.choices[0].message.content)
        if "error" in detection:
            raise HTTPException(status_code=400, detail=detection["error"])

        ingredients = detection.get("ingredients", [])
        if not ingredients:
            raise HTTPException(status_code=400, detail="No se detectaron ingredientes")

        r2 = await client.chat.completions.create(
            model=_TEXT_MODEL,
            messages=[{"role": "user", "content": (
                f"Tengo estos ingredientes disponibles: {', '.join(ingredients)}\n\n"
                "Sugiere 3 recetas que pueda hacer con algunos de estos ingredientes. "
                "Intenta usar los más proteicos primero.\n\n"
                "Responde ÚNICAMENTE con un JSON válido:\n"
                '{\n  "recipes": [\n    {\n      "name": "Tortilla de huevos con tomate",\n'
                '      "ingredients_used": ["huevos", "tomate"],\n'
                '      "missing_ingredients": ["aceite"],\n'
                '      "prep_time_min": 10,\n      "difficulty": "fácil|media|difícil",\n'
                '      "estimated_kcal": 350,\n      "estimated_protein_g": 22,\n'
                '      "steps": ["Bate los huevos con sal.", "Sofríe el tomate picado 2 min."]\n'
                "    }\n  ]\n}"
            )}],
            max_tokens=1024, temperature=0.3,
        )
        recipes_data = _parse_json(r2.choices[0].message.content)
        return {
            "found": True, "source": "groq_vision",
            "ingredients_detected": ingredients,
            "confidence": detection.get("confidence", "media"),
            "recipes": recipes_data.get("recipes", []),
        }
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Error al procesar la respuesta de la IA")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/label", summary="Lee una etiqueta nutricional con IA y extrae los macros")
async def scan_label(file: UploadFile = File(...)):
    image_b64  = base64.standard_b64encode(await file.read()).decode("utf-8")
    media_type = file.content_type or "image/jpeg"
    client     = _groq()

    prompt = (
        "Analiza esta imagen de una etiqueta nutricional de un producto alimenticio.\n\n"
        "Extrae los valores nutricionales y responde ÚNICAMENTE con un JSON válido (sin texto adicional):\n"
        '{\n  "product_name": "nombre del producto si es visible, si no \'Producto desconocido\'",\n'
        '  "serving_size_g": 100,\n'
        '  "per_100g": {"kcal": 245, "protein_g": 22, "fat_g": 8, "saturated_fat_g": 2.5,\n'
        '               "carbs_g": 28, "sugar_g": 3, "fiber_g": 4, "salt_g": 0.8},\n'
        '  "per_serving": {"kcal": 245, "protein_g": 22, "fat_g": 8, "carbs_g": 28},\n'
        '  "confidence": "alta|media|baja",\n  "notes": "cualquier observación relevante"\n}\n\n'
        'Si no puedes leer una etiqueta nutricional responde: {"error": "No se detectó etiqueta nutricional"}\n\n'
        "Extrae los valores exactamente como aparecen en la etiqueta. Si un valor no está visible pon null."
    )

    try:
        response = await client.chat.completions.create(
            model=_VISION_MODEL,
            messages=[{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{image_b64}"}},
                {"type": "text", "text": prompt},
            ]}],
            max_tokens=512, temperature=0.1,
        )
        result = _parse_json(response.choices[0].message.content)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return {"found": True, "source": "groq_vision", **result}
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Error al procesar la respuesta de la IA")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
