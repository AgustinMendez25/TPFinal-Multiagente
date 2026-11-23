"""Los dominios del agente: qué herramientas ve el modelo y con qué instrucciones.

El loop (`harness/bucle.py`) es el mismo para todos; acá cambia solo lo propio de cada uno. En recetas,
la configuración decide además si se enganchan la planificación (`agente.planificacion`) y la
verificación antes de terminar (`agente.verificacion`): son las dos decisiones que medimos.
"""
from functools import partial

from harness import planificacion, verificacion
from harness.bucle import Dominio
from herramientas import mundial, recetas

SISTEMA_MUNDIAL = """Sos un agente que responde preguntas sobre los Mundiales de fútbol usando solo las herramientas.

Reglas:
1. Cada número, nombre o fecha de tu respuesta tiene que salir de un resultado de herramienta. No respondas de memoria.
2. En las herramientas, los nombres de las selecciones van en inglés (Argentina, Germany, Brazil, Netherlands).
3. Si un jugador es ambiguo, la herramienta te devuelve candidatos con su id: usá el id, no repitas el nombre.
4. Para cuentas y diferencias entre fechas usá `calcular`; no hagas cuentas de cabeza.
5. Cuando tengas la respuesta, llamá a terminar(respuesta, motivo) con la respuesta en el formato que pide la pregunta y, en el motivo, de qué resultado sale.
6. Si los datos de las herramientas no alcanzan para responder, llamá a terminar con respuesta null y decí en el motivo qué dato falta. No inventes.
7. Contestá siempre llamando a una herramienta; nunca con texto suelto."""

PRIORITARIO_DIAS = 3


def tabla_inventario() -> str:
    """El inventario ordenado por vencimiento, con los prioritarios marcados (lo calcula el harness)."""
    filas = []
    for i in recetas.inventario():
        marca = "  ← PRIORITARIO: vence pronto" if i["vence_en_dias"] <= PRIORITARIO_DIAS else ""
        filas.append(f"- {i['ingrediente']}: {i['cantidad']} {i['unidad']}, vence en {i['vence_en_dias']} días{marca}")
    return "\n".join(filas)


def sistema_recetas() -> str:
    return f"""Sos un agente que ayuda a cocinar con lo que hay en la heladera, usando un recetario y sus herramientas.

La heladera tiene esto, ordenado por vencimiento (lo primero vence antes):
{tabla_inventario()}

Reglas:
1. Toda receta, cantidad o ingrediente de tu respuesta tiene que salir de un resultado de herramienta. No respondas de memoria.
2. Los ingredientes se nombran simple y en singular: pollo, papa, queso, lenteja, morron.
3. buscar_recetas ordena por duración: «la más rápida» es la primera que cumple todo lo que pide la pregunta. Si la pregunta pide una dieta, comprobala con es_apta, una candidata por vez y en orden.
4. Para lo que falta comprar, usá faltantes con las porciones de la pregunta. Para cantidades de una receta, detalle_receta con esas porciones. Sal, pimienta, aceite, agua, condimentos y hierbas se suponen disponibles.
5. Si la pregunta pide comparar recetas (la que deja menos por comprar, cuántas alcanzan, cuál se hace sin comprar nada), revisá todas las candidatas que correspondan antes de responder.
6. Respondé en el formato que pide la pregunta: el nombre exacto de la receta como lo devuelve la herramienta, un número solo, o los ingredientes separados por punto y coma.
7. Si los datos del recetario no alcanzan (calorías, precios, comercios, o ninguna receta cumple), llamá a terminar con respuesta null y decí qué falta. No inventes.
8. Contestá siempre llamando a una herramienta; nunca con texto suelto. Al final, terminar(respuesta, motivo)."""


DOMINIOS = ("mundial", "recetas")


def construir(nombre: str, config: dict | None = None) -> Dominio:
    if nombre == "mundial":
        return Dominio("mundial", SISTEMA_MUNDIAL, mundial.FICHAS, mundial.HERRAMIENTAS)
    if nombre == "recetas":
        agente = (config or {}).get("agente", {})
        sistema = sistema_recetas()
        return Dominio(
            "recetas", sistema, recetas.FICHAS, recetas.HERRAMIENTAS,
            antes_del_loop=partial(planificacion.planificar, sistema=sistema) if agente.get("planificacion") else None,
            antes_de_terminar=verificacion.verificar if agente.get("verificacion") else None)
    raise ValueError(f"dominio desconocido: {nombre!r}. Los que hay: {', '.join(DOMINIOS)}")


def sistema_libro_cerrado_recetas() -> str:
    """El libro cerrado de recetas ve la misma heladera que el agente, para que la comparación sea justa."""
    return f"""Ayudás a cocinar con lo que hay en la heladera, de memoria y sin herramientas. Las recetas son las del sitio recetasgratis.net.

La heladera tiene esto, ordenado por vencimiento:
{tabla_inventario()}

Si no lo sabés o no se puede saber, respondé exactamente: NO SE."""
