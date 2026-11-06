import os
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    user_context: dict | None = None


class ChatResponse(BaseModel):
    reply: str


_SYSTEM_PROMPT = """Eres NutriBot, el asistente nutricional de CalorIA.
Ayudas a los usuarios a entender su plan de dieta, resolver dudas sobre nutrición,
y sacar el máximo partido a la aplicación. Responde siempre en español, de forma
concisa y amigable. No inventes datos médicos específicos ni sustituyes a un
dietista profesional — recuérdalo si el usuario pide consejo médico concreto.

Cuando el usuario tenga un perfil cargado, úsalo como contexto para personalizar
tus respuestas (calorías objetivo, macros, presupuesto, supermercado, etc.)."""


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return ChatResponse(reply="⚠️ El asistente no está configurado (falta GROQ_API_KEY).")

    system = _SYSTEM_PROMPT
    if req.user_context:
        ctx = req.user_context
        system += f"""

Perfil actual del usuario:
- Nombre: {ctx.get('name', 'Usuario')}
- Calorías objetivo: {ctx.get('kcal_target', '?')} kcal/día
- Proteína mínima: {ctx.get('min_protein_g', '?')} g
- Grasa máxima: {ctx.get('max_fat_g', '?')} g
- Carbos: {ctx.get('min_carbs_g', '?')}–{ctx.get('max_carbs_g', '?')} g
- Presupuesto: {ctx.get('budget_eur', '?')} €/día
- Supermercado: {ctx.get('supermarket', '?')}"""

        if ctx.get('current_diet'):
            diet   = ctx['current_diet']
            meals  = diet.get('meals', [])
            macros = diet.get('macros', {})
            meal_lines = '\n'.join(
                f"  - {m.get('name','').capitalize()}: {m.get('recipe_name','?')} "
                f"({float(m.get('kcal_actual', 0)):.0f} kcal, {float(m.get('cost_eur', 0)):.2f}€)"
                for m in meals
            )
            system += f"""

Dieta generada hoy para el usuario:
{meal_lines}
- Total: {float(macros.get('kcal', 0)):.0f} kcal | {float(macros.get('protein_g', 0)):.0f}g proteína | {float(macros.get('fat_g', 0)):.0f}g grasa | {float(macros.get('carbs_g', 0)):.0f}g carbos | {float(macros.get('cost_eur', 0)):.2f}€"""

    from groq import AsyncGroq
    client = AsyncGroq(api_key=api_key)
    messages = [{"role": "system", "content": system}] + [
        {"role": m.role, "content": m.content} for m in req.messages
    ]

    response = await client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=1000,
    )

    return ChatResponse(reply=response.choices[0].message.content)
