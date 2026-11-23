"""Verificación en código antes de `terminar` (propuesta, §4, decisión 2).

No usa el modelo. Mira la pregunta, la respuesta y las herramientas que se ejecutaron en esta corrida, y
devuelve None si la respuesta puede salir, o un texto que le dice al modelo qué le falta. El loop se lo
devuelve como resultado de `terminar` y le da una vuelta más (hasta `agente.max_rechazos`).

Qué comprueba:
  1. que se haya consultado alguna herramienta antes de responder;
  2. si la pregunta pide una dieta (lo dice el detector), que haya un `es_apta` con esa dieta, y si la
     respuesta es una receta, que sea apta;
  3. si la pregunta pide porciones, que haya un `faltantes` o un `detalle_receta` con esas porciones;
  4. si la respuesta es el nombre de una receta del corpus, que esa receta haya salido en algún resultado;
  5. que los números grandes de la respuesta (más de 20) aparezcan en algún resultado o en la pregunta.
     Los chicos se dejan pasar porque pueden ser cuentas legítimas (cuántos faltan, cuántas alcanzan);
  6. si la respuesta es una lista, que cada elemento haya aparecido en algún resultado.

Negarse (`respuesta = null`) no se verifica: decir que los datos no alcanzan siempre está permitido.
"""
import json
import re
import unicodedata

from harness.detector import detectar
from herramientas import recetas

NUMERO = re.compile(r"\d+(?:[.,]\d+)?")
TOPE_NUMEROS_CHICOS = 20


def _normalizar(texto: str) -> str:
    sin_tildes = "".join(c for c in unicodedata.normalize("NFKD", str(texto)) if not unicodedata.combining(c))
    return " ".join(sin_tildes.casefold().split()).strip(" .")


def _id_de_receta(respuesta: str) -> int | None:
    buscado = _normalizar(respuesta)
    return next((r["id"] for r in recetas._corpus().values() if _normalizar(r["nombre"]) == buscado), None)


def _texto_de(historial: list[dict]) -> str:
    return _normalizar(" ".join(json.dumps(h["datos"], ensure_ascii=False) for h in historial))


def verificar(pregunta: str, respuesta: str, historial: list[dict]) -> str | None:
    problemas = []
    if not historial:
        return ("respondiste sin consultar ninguna herramienta. La respuesta tiene que salir de los datos del "
                "recetario; si no se puede saber con las herramientas, terminá con respuesta null.")
    pedido = detectar(pregunta)
    resultados = _texto_de(historial)
    receta = _id_de_receta(respuesta)

    if pedido["dieta"]:
        aptas = [h for h in historial if h["nombre"] == "es_apta" and h["argumentos"].get("dieta") == pedido["dieta"]]
        if not aptas:
            problemas.append(f"la pregunta pide una dieta ({pedido['dieta']}) y no comprobaste ninguna receta con "
                             f"es_apta(receta_id, \"{pedido['dieta']}\").")
        elif receta is not None:
            propia = [h for h in aptas if h["argumentos"].get("receta_id") == receta]
            if not propia:
                problemas.append(f"no comprobaste con es_apta que la receta {receta} sea {pedido['dieta']}.")
            elif not any(h["datos"].get("apta") for h in propia):
                problemas.append(f"según es_apta, la receta {receta} no es {pedido['dieta']}.")

    if pedido["porciones"]:
        con_porciones = [h for h in historial if h["nombre"] in ("faltantes", "detalle_receta")
                         and h["argumentos"].get("porciones") == pedido["porciones"]]
        if not con_porciones:
            problemas.append(f"la pregunta es para {pedido['porciones']} personas y no usaste faltantes ni "
                             f"detalle_receta con porciones={pedido['porciones']}.")

    if receta is not None and _normalizar(respuesta) not in resultados:
        problemas.append("la receta de tu respuesta no apareció en ningún resultado de herramienta.")

    texto_pregunta = _normalizar(pregunta)
    for numero in NUMERO.findall(respuesta):
        valor = float(numero.replace(",", "."))
        if valor > TOPE_NUMEROS_CHICOS and numero not in resultados and numero not in texto_pregunta:
            problemas.append(f"el número {numero} no aparece en ningún resultado de herramienta: no lo inventes.")

    if ";" in respuesta:
        for elemento in (e for e in respuesta.split(";") if e.strip()):
            if _normalizar(elemento) not in resultados:
                problemas.append(f"«{elemento.strip()}» no apareció en ningún resultado de herramienta.")

    return " ".join(problemas) if problemas else None
