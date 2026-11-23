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
    orden = [i["ingrediente"] for i in recetas.inventario()]
    # Vuelta 2 (dev-005, dev-019): el modelo no traducía «el que vence primero» a un ingrediente. Lo dice el harness.
    filas.append(f"El ingrediente que vence primero es {orden[0]}; los dos que vencen antes son {orden[0]} y {orden[1]}.")
    return "\n".join(filas)


def sistema_recetas() -> str:
    return f"""Sos un agente que ayuda a cocinar con lo que hay en la heladera, usando un recetario y sus herramientas.

La heladera tiene esto, ordenado por vencimiento (lo primero vence antes):
{tabla_inventario()}

Reglas:
1. Toda receta, cantidad o ingrediente de tu respuesta tiene que salir de un resultado de herramienta. No respondas de memoria.
2. Los ingredientes se nombran simple y en singular: pollo, papa, queso, lenteja, morron. Lo que la pregunta dice que la receta lleva («con X», «que lleva X») va en `contiene`; en `excluye` va solo lo que dice que NO lleva.
3. Una dieta no es un ingrediente: no la pongas en buscar_recetas; comprobala con es_apta. «Sin carne ni pescado» o «para vegetarianos» = vegetariana; «sin nada de origen animal» o «para veganos» = vegana; «sin gluten» o «para celíacos» = sin_gluten; «sin lácteos» o «sin lactosa» = sin_lactosa.
4. Si la pregunta nombra una receta por su número, usá ese receta_id directamente, sin buscar.
5. buscar_recetas ordena por duración (la posición 1 es la más rápida): «la más rápida» es la PRIMERA de la lista que cumple lo que pide la pregunta. Si pide una dieta, comprobá las candidatas con es_apta, una por vez y en orden, y quedate con la primera apta. No uses faltantes para elegirla, salvo que la pregunta hable de lo que falta o de no comprar nada.
6. detalle_receta y faltantes con `porciones` ya devuelven las cantidades escaladas a esas porciones: usá esos números tal cual, sin volver a multiplicar. Para lo que falta comprar usá faltantes: trae la lista `faltan`, cuántos son (`cuantos_faltan`) y, para cada ingrediente de la heladera, cuándo vence y para cuántas porciones alcanza lo que hay. Sal, pimienta, aceite, agua, condimentos y hierbas se suponen disponibles.
7. Si la pregunta pide comparar recetas (la que deja menos por comprar, cuántas alcanzan, cuál se hace sin comprar nada), revisá todas las candidatas que correspondan antes de responder.
8. Para saber qué ingrediente vence antes, usá la lista de la heladera de arriba (ya está ordenada) o el `vence_en_dias` de faltantes.
9. Respondé en el formato que pide la pregunta: el nombre exacto de la receta como lo devuelve la herramienta, un número solo, o los ingredientes separados por punto y coma.
10. Si los datos del recetario no alcanzan (calorías, precios, comercios, o ninguna receta cumple), llamá a terminar con respuesta null (no con un texto) y decí en el motivo qué falta. No inventes.
11. Contestá siempre llamando a una herramienta; nunca con texto suelto. Al final, terminar(respuesta, motivo)."""


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
