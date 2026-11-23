"""Verificación en código antes de `terminar` (propuesta, §4, decisión 2).

No usa el modelo. Mira la pregunta, la respuesta y las herramientas que se ejecutaron en esta corrida, y
devuelve None si la respuesta puede salir, o un texto que le dice al modelo qué le falta. El loop se lo
devuelve como resultado de `terminar` y le da una vuelta más (hasta `agente.max_rechazos`).

Qué comprueba:
  1. que se haya consultado alguna herramienta antes de responder;
  2. si la pregunta pide una dieta (lo dice el detector), que haya un `es_apta` con esa dieta, y si la
     respuesta es una receta, que sea apta;
  3. si la pregunta pide porciones, que haya un `faltantes` o un `detalle_receta` con esas porciones;
  4. si la respuesta es el nombre de una receta del corpus, que esa receta haya salido en algún resultado, y
     si la pregunta pide «la más rápida», que todas las candidatas anteriores de la búsqueda hayan quedado
     descartadas (con es_apta, o con faltantes si pide no comprar);
  5. que los números grandes de la respuesta (más de 20) aparezcan en algún resultado o en la pregunta.
     Los chicos se dejan pasar porque pueden ser cuentas legítimas (cuántos faltan, cuántas alcanzan);
  6. si la respuesta es una lista, que cada elemento haya aparecido en algún resultado;
  7. que la respuesta no sea una frase que dice que no se puede responder («No hay recetas que…»): eso
     es negarse, y se hace con respuesta null.

Negarse (`respuesta = null`) no se verifica: decir que los datos no alcanzan siempre está permitido.
"""
import json
import re
import unicodedata

from harness.detector import detectar
from herramientas import recetas

NUMERO = re.compile(r"\d+(?:[.,]\d+)?")
TOPE_NUMEROS_CHICOS = 20
NEGATIVA = re.compile(r"^(no (hay|existe|existen|se puede|es posible|tengo|encontre|se encontr)|ninguna?)")


def _normalizar(texto: str) -> str:
    sin_tildes = "".join(c for c in unicodedata.normalize("NFKD", str(texto)) if not unicodedata.combining(c))
    return " ".join(sin_tildes.casefold().split()).strip(" .")


def _id_de_receta(respuesta: str) -> int | None:
    buscado = _normalizar(respuesta)
    return next((r["id"] for r in recetas._corpus().values() if _normalizar(r["nombre"]) == buscado), None)


def _numeros(texto: str) -> set[float]:
    return {float(n.replace(",", ".")) for n in NUMERO.findall(texto)}


def _texto_de(historial: list[dict]) -> str:
    return _normalizar(" ".join(json.dumps(h["datos"], ensure_ascii=False) for h in historial))


MAS_RAPIDA = re.compile(r"\bmas rapid[ao]s?\b")
SIN_COMPRAR = re.compile(r"\bsin comprar\b|\bno (quiero )?comprar\b")


def _orden(pregunta: str, dieta: str | None, receta: int | None, historial: list[dict]) -> str | None:
    """Si la pregunta pide «la más rápida», la receta respondida tiene que ser la primera de la búsqueda que no
    quedó descartada. Una candidata anterior cuenta como descartada si es_apta dijo que no cumple la dieta
    pedida, o (si la pregunta pide no comprar) si faltantes dijo que falta algo. Sin dieta ni «sin comprar»,
    tiene que ser la primera. Vuelta 2: dev-008 y dev-019 eligieron una receta del medio de la lista."""
    texto = _normalizar(pregunta)
    if receta is None or not MAS_RAPIDA.search(texto):
        return None
    busquedas = [h for h in historial if h["nombre"] == "buscar_recetas"
                 and any(c["id"] == receta for c in h["datos"].get("recetas", []))]
    if not busquedas:
        return None
    candidatas = busquedas[-1]["datos"]["recetas"]
    sin_comprar = bool(SIN_COMPRAR.search(texto))

    def descartada(c: dict) -> bool:
        for h in historial:
            if h["argumentos"].get("receta_id") != c["id"]:
                continue
            if dieta and h["nombre"] == "es_apta" and h["argumentos"].get("dieta") == dieta \
                    and h["datos"].get("apta") is False:
                return True
            if sin_comprar and h["nombre"] == "faltantes" and h["datos"].get("faltan"):
                return True
        return False

    for c in candidatas:
        if c["id"] == receta:
            return None
        if not descartada(c):
            como = (f"comprobala con es_apta(receta_id, \"{dieta}\")" if dieta else
                    "comprobala con faltantes" if sin_comprar else "es la primera de la lista: la más rápida es esa")
            return (f"la pregunta pide la más rápida, y en la búsqueda «{c['nombre']}» (id {c['id']}, posición "
                    f"{c.get('posicion', '?')}) está antes que tu respuesta y no la descartaste: {como}.")
    return None


def verificar(pregunta: str, respuesta: str, historial: list[dict]) -> str | None:
    problemas = []
    if NEGATIVA.search(_normalizar(respuesta)) and len(respuesta.split()) >= 3:
        return ("tu respuesta es una frase que dice que no se puede responder. Si es así, terminá con respuesta "
                "null y explicá en el motivo qué dato falta; si sí se puede, respondé solo el dato que pide la "
                "pregunta.")
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

    orden = _orden(pregunta, pedido["dieta"], receta, historial)
    if orden:
        problemas.append(orden)

    if receta is not None and _normalizar(respuesta) not in resultados:
        problemas.append("la receta de tu respuesta no apareció en ningún resultado de herramienta.")

    vistos = _numeros(resultados) | _numeros(_normalizar(pregunta))   # números enteros: 0.25 no cuenta como 25
    for numero in NUMERO.findall(respuesta):
        valor = float(numero.replace(",", "."))
        if valor > TOPE_NUMEROS_CHICOS and valor not in vistos:
            problemas.append(f"el número {numero} no aparece en ningún resultado de herramienta: no lo inventes. Si "
                             f"usaste detalle_receta o faltantes con las porciones de la pregunta, las cantidades "
                             f"ya vienen escaladas: respondé con el número tal como aparece ahí.")

    if ";" in respuesta:
        for elemento in (e for e in respuesta.split(";") if e.strip()):
            if _normalizar(elemento) not in resultados:
                problemas.append(f"«{elemento.strip()}» no apareció en ningún resultado de herramienta.")

    return " ".join(problemas) if problemas else None
