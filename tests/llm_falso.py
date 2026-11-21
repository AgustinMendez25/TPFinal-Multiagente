"""Un LLM con guion: devuelve las respuestas (o levanta los errores) en el orden dado.

Se llama igual que `llm.chat` y guarda cada pedido, para que los tests miren qué mensajes recibió el modelo.
"""
import copy

import llm


class LLMFalso:
    def __init__(self, guion):
        self.guion = list(guion)
        self.pedidos = []

    def __call__(self, mensajes, **opciones):
        self.pedidos.append({"mensajes": copy.deepcopy(mensajes), **opciones})
        if not self.guion:
            raise AssertionError("el guion del LLM falso se terminó")
        siguiente = self.guion.pop(0)
        if isinstance(siguiente, Exception):
            raise siguiente
        return siguiente


def llamada(*pares, contenido="", entrada=100, salida=20) -> llm.Respuesta:
    """Una respuesta con llamadas a herramientas. Cada par: (nombre, argumentos) o (nombre, argumentos, id)."""
    llamadas = []
    for par in pares:
        item = {"function": {"name": par[0], "arguments": par[1]}}
        if len(par) > 2:
            item["id"] = par[2]
        llamadas.append(item)
    return llm.Respuesta({"role": "assistant", "content": contenido, "tool_calls": llamadas},
                         entrada, salida, 50, "stop")


def texto(contenido, entrada=100, salida=20) -> llm.Respuesta:
    """Una respuesta sin llamadas a herramientas."""
    return llm.Respuesta({"role": "assistant", "content": contenido}, entrada, salida, 50, "stop")
