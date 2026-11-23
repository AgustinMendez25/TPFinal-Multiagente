"""Planificación antes de usar herramientas (plan-and-execute; propuesta, §4, decisión 1).

Una llamada al modelo, sin herramientas y con la salida restringida a un esquema JSON, escribe el plan:
qué buscar, qué candidatas hay que recorrer, con qué criterio compararlas y cuándo parar. El plan entra
a la conversación como un mensaje antes del loop, y el loop sigue como siempre.

Falla que apunta a arreglar: quedarse con la primera candidata de la búsqueda cuando la pregunta exige
recorrer y comparar varias (las tareas fuera del esquema del camino fijo).

La llamada queda en la traza como `llamada_modelo` del paso 1 (cuenta para el costo y para el tope de
tokens), seguida de un evento `plan` con lo que escribió el modelo.
"""
import json

import llm

ESQUEMA = {
    "type": "object",
    "properties": {
        "buscar": {"type": "array", "items": {"type": "string"},
                   "description": "ingredientes que tiene que llevar la receta"},
        "excluir": {"type": "array", "items": {"type": "string"}},
        "dieta": {"type": ["string", "null"], "enum": ["vegetariana", "vegana", "sin_gluten", "sin_lactosa", None]},
        "porciones": {"type": ["integer", "null"]},
        "receta_id": {"type": ["integer", "null"], "description": "el número de receta si la pregunta lo nombra"},
        "candidatas": {"type": "string", "description": "qué recetas hay que mirar: la primera, todas, hasta encontrar una que cumpla"},
        "criterio": {"type": "string", "description": "cómo se elige o se calcula la respuesta"},
        "pasos": {"type": "array", "items": {"type": "string"}},
        "cuando_parar": {"type": "string"},
        "se_puede_responder": {"type": "boolean", "description": "false si la pregunta pide datos que el recetario no tiene"},
    },
    "required": ["buscar", "excluir", "dieta", "porciones", "receta_id", "candidatas", "criterio", "pasos", "cuando_parar",
                 "se_puede_responder"],
}

INSTRUCCION = """Antes de usar las herramientas, escribí un plan para responder la pregunta. No la respondas todavía.

Las herramientas son: buscar_recetas(contiene, excluye), detalle_receta(receta_id, porciones), es_apta(receta_id, dieta) y faltantes(receta_id, porciones). El recetario tiene ingredientes, cantidades, duración y comensales; no tiene calorías, precios ni comercios.

Decí:
- qué ingredientes buscar (todos los que la pregunta dice que la receta lleva) y cuáles excluir (solo los que dice que NO lleva);
- la dieta va en dieta, nunca en excluir: «sin carne ni pescado» o «para vegetarianos» = vegetariana; «sin nada de origen animal» o «para veganos» = vegana; «sin gluten» o «para celíacos» = sin_gluten; «sin lácteos» o «sin lactosa» = sin_lactosa;
- qué dieta y cuántas porciones pide la pregunta: null si la pregunta no lo dice, no los inventes;
- receta_id: el número de receta si la pregunta lo nombra (entonces no hace falta buscar), o null;
- qué candidatas hay que mirar. Si pide «la más rápida», recorrelas en orden y pará en la primera que cumpla. Solo si la pregunta pide comparar (la que deja menos por comprar, cuántas alcanzan, cuál se hace sin comprar nada) hay que revisar todas;
- con qué criterio se elige o se calcula la respuesta, los pasos en orden y cuándo parar.
Si la pregunta pide un dato que el recetario no tiene, poné se_puede_responder en false.

Pregunta: """


def planificar(pregunta: str, config: dict, registro, chat=llm.chat, sistema: str = "") -> tuple[list[dict], int]:
    modelo = config["modelo"]
    mensajes = [{"role": "system", "content": sistema}, {"role": "user", "content": INSTRUCCION + pregunta}]
    try:
        respuesta = chat(mensajes, modelo=modelo["nombre"], num_ctx=modelo["num_ctx"],
                         temperatura=modelo["temperatura"], semilla=modelo["semilla"], think=modelo["think"],
                         num_predict=modelo["num_predict"], formato=ESQUEMA, timeout_s=modelo["timeout_s"])
    except llm.LLMError as error:
        registro.evento("plan", paso=1, ok=False, error=str(error)[:300])
        return [], 0
    contenido = respuesta.mensaje.get("content") or ""
    registro.evento("llamada_modelo", paso=1, modelo=modelo["nombre"], num_ctx=modelo["num_ctx"],
                    tokens_entrada=respuesta.tokens_entrada, tokens_salida=respuesta.tokens_salida,
                    duracion_ms=respuesta.duracion_ms, razon_fin=respuesta.razon_fin, texto=contenido[:500],
                    rol="planificador")
    tokens = respuesta.tokens_entrada + respuesta.tokens_salida
    try:
        plan = json.loads(contenido)
    except json.JSONDecodeError:
        registro.evento("plan", paso=1, ok=False, error="el plan no es JSON válido", texto=contenido[:500])
        return [], tokens
    registro.evento("plan", paso=1, ok=True, plan=plan)
    texto = ("Este es tu plan. Seguilo con las herramientas, pero si los resultados muestran otra cosa, "
             "corregilo:\n" + json.dumps(plan, ensure_ascii=False, indent=1))
    return [{"role": "user", "content": texto}], tokens
