"""Prueba de factibilidad, versión mínima (sin loop): las cinco tareas de la sección 6 con qwen3:8b.

1. Libro cerrado: la pregunta sola, sin herramientas.
2. Para las tareas 2 y 3: la misma pregunta con el resultado real de una búsqueda en el corpus pegado
   en el prompt, como si lo hubiera devuelto una herramienta (buscar_recetas + detalle_receta).

Usa llm.chat y trazas.registro del kit, con la decodificación de config.toml (temperatura 0, semilla
fija, think apagado). Escribe trazas en factibilidad/trazas/<variante>/ y las respuestas en
factibilidad/respuestas.json.

    python factibilidad/libro_cerrado_5.py
"""
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path[:0] = [str(RAIZ.parent), str(RAIZ)]
import config as configuracion  # noqa: E402
import llm  # noqa: E402
import recetas  # noqa: E402
from trazas.registro import Registro  # noqa: E402

TAREAS = {
    "fac-1": "Tengo huevos, cebolla y papa. ¿Qué puedo cocinar para dos personas?",
    "fac-2": "Tengo arroz, tomate y lentejas. Buscá una receta que use esos ingredientes y decime qué me falta.",
    "fac-3": "Tengo zanahoria, cebolla, papa y pollo. El pollo vence en dos días y el resto en una semana. "
             "Quiero cocinar para cuatro personas: encontrá una receta que priorice el pollo y ajustá las cantidades.",
    "fac-4": "Tengo harina, leche y huevos, pero no tengo manteca. Buscá una receta posible y evaluá si hay "
             "una sustitución disponible.",
    "fac-5": "Quiero una receta vegetariana para tres personas, sin huevo, usando lo que tengo: arroz, tomate y "
             "cebolla. Además, quiero priorizar los ingredientes que estén próximos a vencer.",
}
# lo que "habría llamado" el agente en cada tarea con resultado pegado
BUSQUEDAS = {
    "fac-2": {"con": ["arroz", "tomate", "lenteja"], "sin": []},
    "fac-3": {"con": ["pollo", "zanahoria", "cebolla", "papa"], "sin": []},
}
SISTEMA_CERRADO = ("Sos un asistente de cocina. Respondé de memoria, sin herramientas. Si no lo sabés o no se "
                   "puede saber, decilo.")
SISTEMA_PEGADO = ("Sos un asistente de cocina. Respondé usando solo las recetas que devolvieron las "
                  "herramientas, que salen de un corpus de recetas. Citá el id de la receta que elegís. Si los "
                  "datos no alcanzan, decilo.")


def resultado_pegado(tarea: str) -> str:
    args = BUSQUEDAS[tarea]
    busqueda = recetas.buscar_recetas(args["con"], args["sin"], limite=3)
    bloques = [f"Resultado de buscar_recetas({json.dumps(args, ensure_ascii=False)}):\n"
               + json.dumps(busqueda, ensure_ascii=False)]
    for r in busqueda["recetas"]:
        bloques.append(f"Resultado de detalle_receta({{\"receta_id\": {r['id']}}}):\n"
                       + json.dumps(recetas.detalle_receta(r["id"]), ensure_ascii=False))
    return "\n\n".join(bloques)


def correr(variante: str, tarea: str, sistema: str, usuario: str, cfg: dict) -> dict:
    registro = Registro(RAIZ / "trazas" / variante, tarea)
    m = cfg["modelo"]
    registro.evento("corrida_inicio", modelo=m["nombre"], config=cfg | {"ollama_version": llm.version()})
    mensajes = [{"role": "system", "content": sistema}, {"role": "user", "content": usuario}]
    r = llm.chat(mensajes, modelo=m["nombre"], num_ctx=m["num_ctx"], temperatura=m["temperatura"],
                 semilla=m["semilla"], think=m["think"], num_predict=m["num_predict"], timeout_s=900)
    registro.evento("llamada_modelo", paso=1, modelo=m["nombre"], num_ctx=m["num_ctx"],
                    tokens_entrada=r.tokens_entrada, tokens_salida=r.tokens_salida, duracion_ms=r.duracion_ms)
    texto = r.mensaje.get("content", "").strip()
    registro.evento("corrida_fin", estado="respondida", respuesta=texto, pasos=1)
    print(f"[{variante} {tarea}] {r.tokens_entrada}+{r.tokens_salida} tokens, {r.duracion_ms/1000:.0f}s, "
          f"fin={r.razon_fin}", flush=True)
    return {"variante": variante, "tarea": tarea, "prompt_usuario": usuario, "respuesta": texto,
            "tokens_entrada": r.tokens_entrada, "tokens_salida": r.tokens_salida,
            "duracion_ms": r.duracion_ms, "razon_fin": r.razon_fin}


if __name__ == "__main__":
    cfg = configuracion.cargar()
    salida = []
    for tarea, pregunta in TAREAS.items():
        salida.append(correr("libro_cerrado", tarea, SISTEMA_CERRADO, pregunta, cfg))
    for tarea in BUSQUEDAS:
        usuario = TAREAS[tarea] + "\n\n" + resultado_pegado(tarea)
        salida.append(correr("resultado_pegado", tarea, SISTEMA_PEGADO, usuario, cfg))
    (RAIZ / "respuestas.json").write_text(json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8")
