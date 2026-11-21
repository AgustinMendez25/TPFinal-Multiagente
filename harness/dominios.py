"""Los dominios del agente: qué herramientas ve el modelo y con qué instrucciones.

El loop (`harness/bucle.py`) es el mismo para todos; acá cambia solo lo propio de cada uno.
"""
from harness.bucle import Dominio
from herramientas import mundial

SISTEMA_MUNDIAL = """Sos un agente que responde preguntas sobre los Mundiales de fútbol usando solo las herramientas.

Reglas:
1. Cada número, nombre o fecha de tu respuesta tiene que salir de un resultado de herramienta. No respondas de memoria.
2. En las herramientas, los nombres de las selecciones van en inglés (Argentina, Germany, Brazil, Netherlands).
3. Si un jugador es ambiguo, la herramienta te devuelve candidatos con su id: usá el id, no repitas el nombre.
4. Para cuentas y diferencias entre fechas usá `calcular`; no hagas cuentas de cabeza.
5. Cuando tengas la respuesta, llamá a terminar(respuesta, motivo) con la respuesta en el formato que pide la pregunta y, en el motivo, de qué resultado sale.
6. Si los datos de las herramientas no alcanzan para responder, llamá a terminar con respuesta null y decí en el motivo qué dato falta. No inventes.
7. Contestá siempre llamando a una herramienta; nunca con texto suelto."""

DOMINIOS = ("mundial",)


def construir(nombre: str) -> Dominio:
    if nombre == "mundial":
        return Dominio("mundial", SISTEMA_MUNDIAL, mundial.FICHAS, mundial.HERRAMIENTAS)
    raise ValueError(f"dominio desconocido: {nombre!r}. Los que hay: {', '.join(DOMINIOS)}")
