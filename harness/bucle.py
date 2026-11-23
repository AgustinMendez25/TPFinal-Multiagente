"""El loop del agente, compartido por los dominios (Mundial y recetas).

Lo que resuelve, en el orden de la sección 4 del enunciado:
  1. el ciclo: llamar al modelo, ejecutar cada llamada a herramienta, devolver un resultado por llamada
     (también la llamada que el modelo escribió como texto en vez de mandarla como tool_call);
  2. el contrato: cada herramienta tiene su ficha JSON y los argumentos se validan contra ella;
  3. la salida mal formada: JSON roto, herramienta inexistente o argumentos equivocados vuelven al
     modelo como error, y el loop sigue;
  4. las herramientas que fallan: excepciones, timeouts y resultados vacíos también vuelven como texto;
  5. el contexto: un resultado más largo que `contexto.tope_resultado_caracteres` se recorta, y una
     llamada idéntica a una anterior no se vuelve a ejecutar (devolvería lo mismo y llenaría la ventana);
  6. los reintentos: un error del servidor se reintenta `frenos.reintentos` veces, con espera creciente;
  7. la parada: topes de pasos, de tokens y (opcional) de segundos, y `terminar(respuesta, motivo)`;
  8. las trazas: un evento por cada cosa que pasa.
"""
import ast
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturoVencido
from dataclasses import dataclass, field
from typing import Callable

import llm

RECORDATORIO = ("No llamaste a ninguna herramienta. Si necesitás datos, llamá a una herramienta. Si ya tenés "
                "la respuesta, llamá a terminar(respuesta, motivo); si los datos no alcanzan, a "
                "terminar(null, motivo). No contestes con texto suelto.")
_TIPOS = {"string": str, "integer": int, "number": (int, float), "boolean": bool, "array": list,
          "object": dict, "null": type(None)}
_EJECUTOR = ThreadPoolExecutor(max_workers=4)


@dataclass
class Dominio:
    nombre: str
    sistema: str                         # el prompt de sistema
    fichas: list[dict]                   # los esquemas JSON, incluida la de `terminar`
    herramientas: dict[str, Callable]    # nombre -> función; `terminar` no está: la atiende el loop
    # Enganches opcionales (Bloque 2). Sin ellos, el loop es el del Bloque 1.
    #   antes_del_loop(pregunta, config, registro, chat) -> (mensajes que se agregan, tokens que usó)
    #   antes_de_terminar(pregunta, respuesta, historial) -> None si puede terminar, o qué le falta
    antes_del_loop: Callable | None = None
    antes_de_terminar: Callable | None = None


@dataclass
class _Estado:
    """Lo que el loop recuerda durante una corrida."""
    pregunta: str
    max_rechazos: int
    tokens: int = 0
    rechazos: int = 0
    vistos: set = field(default_factory=set)        # ids de llamadas ya usados en la traza
    historial: list = field(default_factory=list)   # herramientas ejecutadas: nombre, argumentos, datos, ok
    hechas: dict = field(default_factory=dict)      # llamada (nombre + argumentos) -> (paso, vino recortada)


@dataclass
class Fin:
    estado: str                          # respondida, negada, tope_pasos, tope_tokens o error
    respuesta: str | None
    pasos: int
    motivo: str | None = None


def _es_tipo(valor, tipo) -> bool:
    for nombre in (tipo if isinstance(tipo, list) else [tipo]):
        if nombre in ("integer", "number") and isinstance(valor, bool):
            continue
        if isinstance(valor, _TIPOS[nombre]):
            return True
    return False


def validar_argumentos(ficha: dict, argumentos) -> str | None:
    """None si los argumentos cumplen la ficha; si no, el error explicado para el modelo."""
    parametros = ficha["function"]["parameters"]
    propiedades = parametros.get("properties", {})
    if not isinstance(argumentos, dict):
        return "los argumentos tienen que ser un objeto JSON"
    faltan = [r for r in parametros.get("required", []) if r not in argumentos]
    if faltan:
        return f"faltan argumentos obligatorios: {', '.join(faltan)}"
    sobran = [k for k in argumentos if k not in propiedades]
    if sobran:
        return f"argumentos que no existen: {', '.join(sobran)}. Los válidos son: {', '.join(propiedades)}"
    for clave, valor in argumentos.items():
        tipo = propiedades[clave].get("type")
        if tipo and not _es_tipo(valor, tipo):
            return f"«{clave}» tiene que ser {tipo}, y llegó {type(valor).__name__}: {valor!r}"
    return None


def _parsear(crudos) -> tuple[dict | None, str | None]:
    if isinstance(crudos, dict):
        return crudos, None
    if isinstance(crudos, str):
        try:
            valor = json.loads(crudos) if crudos.strip() else {}
        except json.JSONDecodeError as error:
            return None, f"los argumentos no son JSON válido ({error.msg}). Mandalos como un objeto JSON"
        return (valor, None) if isinstance(valor, dict) else (None, "los argumentos tienen que ser un objeto JSON")
    return None, "los argumentos tienen que ser un objeto JSON"


def _respuesta_final(valor) -> str | None:
    """`terminar` puede traer un número, una lista o el texto «null»: todo se lleva a texto o None."""
    if valor is None:
        return None
    if isinstance(valor, list):
        valor = "; ".join(str(x) for x in valor)
    texto = str(valor).strip()
    return None if texto.casefold() in ("", "null", "none") else texto


def _ejecutar(funcion: Callable, argumentos: dict, timeout_s: float):
    futuro = _EJECUTOR.submit(funcion, **argumentos)
    try:
        return futuro.result(timeout=timeout_s)
    except FuturoVencido:
        return {"error": f"la herramienta tardó más de {timeout_s:g} s y se cortó"}
    except Exception as error:  # noqa: BLE001 (cualquier falla de la herramienta vuelve al modelo)
        return {"error": f"la herramienta falló: {type(error).__name__}: {error}"}


def _texto_resultado(datos, tope: int) -> tuple[str, bool, int]:
    if datos is None or datos == [] or datos == {} or datos == "":
        datos = {"resultado": "vacío", "nota": "la herramienta no encontró nada con esos argumentos"}
    texto = datos if isinstance(datos, str) else json.dumps(datos, ensure_ascii=False)
    if len(texto) <= tope:
        return texto, False, len(texto)
    resto = len(texto) - tope
    return texto[:tope] + f"\n[…recortado: {resto} caracteres más. Pedí algo más específico.]", True, len(texto)


# --- llamadas escritas como texto -------------------------------------------------------------------
# qwen3:8b a veces escribe la llamada en el contenido en vez de mandarla como tool_call. Vimos tres
# formas en la corrida "antes" del Bloque 1 (mun-007, mun-008, mun-009, mun-012):
#   {"name": "terminar", "arguments": {...}}     terminar{"respuesta": ...}     terminar("8", "motivo")
# Si el texto tiene una sola llamada reconocible a una herramienta que existe, se la atiende como
# si hubiera llegado bien. Si no, sigue valiendo el recordatorio.

_LITERALES = {"null": None, "None": None, "true": True, "True": True, "false": False, "False": False}


def _literal(nodo):
    """Como ast.literal_eval, pero acepta null/true/false de JSON."""
    if isinstance(nodo, ast.Name) and nodo.id in _LITERALES:
        return _LITERALES[nodo.id]
    if isinstance(nodo, (ast.List, ast.Set)):          # {"a", "b"}: un conjunto se lee como lista
        return [_literal(n) for n in nodo.elts]
    if isinstance(nodo, ast.Dict):
        return {_literal(k): _literal(v) for k, v in zip(nodo.keys, nodo.values)}
    return ast.literal_eval(nodo)


def _sin_envoltorio(texto: str) -> str:
    texto = re.sub(r"</?tool_call>", "", texto)
    texto = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", texto.strip())
    return texto.strip()


def _objeto_json(texto: str, desde: int):
    try:
        valor, _ = json.JSONDecoder().raw_decode(texto, desde)
    except json.JSONDecodeError:
        return None
    return valor if isinstance(valor, dict) else None


def rescatar_llamada(texto: str, fichas: dict) -> dict | None:
    """La llamada a herramienta escrita en el texto, en el formato de tool_calls; None si no hay una clara."""
    texto = _sin_envoltorio(texto or "")
    if not texto:
        return None
    # 1. {"name": ..., "arguments": {...}}
    if texto.startswith("{"):
        objeto = _objeto_json(texto, 0)
        if objeto and objeto.get("name") in fichas:
            argumentos = objeto.get("arguments", objeto.get("parameters", {}))
            return {"function": {"name": objeto["name"], "arguments": argumentos}}
    # 2. nombre{...} o nombre({...})   3. nombre(arg1, arg2, clave=valor)
    encontradas = [m for m in re.finditer(r"\b([a-z_]+)\s*([({])", texto) if m.group(1) in fichas]
    if len(encontradas) != 1:
        return None
    nombre = encontradas[0].group(1)
    inicio = encontradas[0].end() - 1
    llave = texto.find("{", inicio)
    if texto[inicio] == "{" or texto[inicio + 1:].lstrip().startswith("{"):
        objeto = _objeto_json(texto, llave)
        if objeto is not None:
            return {"function": {"name": nombre, "arguments": objeto}}
        if texto[inicio] == "{":
            return None
        # terminar({"a;b"}, "motivo"): no es un objeto JSON sino un conjunto de Python (dev-010, dev-011);
        # se sigue con la lectura posicional de abajo
    cierre = texto.rfind(")")
    if cierre < inicio:
        return None
    try:
        llamada = ast.parse(texto[encontradas[0].start():cierre + 1], mode="eval").body
        if not isinstance(llamada, ast.Call):
            return None
        orden = list(fichas[nombre]["function"]["parameters"].get("properties", {}))
        if len(llamada.args) > len(orden):
            return None
        argumentos = {orden[i]: _literal(n) for i, n in enumerate(llamada.args)}
        argumentos |= {k.arg: _literal(k.value) for k in llamada.keywords if k.arg}
    except (SyntaxError, ValueError, TypeError):
        return None
    return {"function": {"name": nombre, "arguments": argumentos}}


def _clave(nombre: str, argumentos) -> str:
    return nombre + json.dumps(argumentos, sort_keys=True, ensure_ascii=False)


def _llamar_modelo(mensajes, dominio, config, registro, paso, chat, dormir) -> llm.Respuesta:
    modelo, frenos = config["modelo"], config["frenos"]
    for intento in range(1, frenos["reintentos"] + 2):
        try:
            return chat(mensajes, modelo=modelo["nombre"], num_ctx=modelo["num_ctx"],
                        temperatura=modelo["temperatura"], semilla=modelo["semilla"], think=modelo["think"],
                        num_predict=modelo["num_predict"], herramientas=dominio.fichas,
                        timeout_s=modelo["timeout_s"])
        except llm.ContextOverflow:
            raise
        except llm.LLMError as error:
            if intento > frenos["reintentos"]:
                raise
            registro.evento("reintento_modelo", paso=paso, motivo=str(error)[:300] or "error del servidor",
                            intento=intento)
            dormir(frenos["espera_reintento_s"] * 2 ** (intento - 1))
    raise AssertionError("no se llega acá")


def _repetida(hecha: tuple) -> str:
    paso, truncado, fallo = (*hecha, None)[:3]
    if fallo:                             # repetir una llamada que falló da el mismo error: hay que cambiar algo
        return (f"ya hiciste esta misma llamada en el paso {paso} y falló con: «{fallo}». Con los mismos "
                f"argumentos va a volver a fallar: cambiá los argumentos, probá otra herramienta o llamá a terminar.")
    consejo = ("Esa vez el resultado vino recortado: pedí menos datos usando los filtros de la herramienta. "
               if truncado else "")
    return (f"ya hiciste esta misma llamada en el paso {paso} y el resultado no cambia: está más arriba en la "
            f"conversación. {consejo}Si con eso no alcanza, probá otra herramienta o llamá a terminar.")


def _atender(llamada: dict, indice: int, paso: int, dominio: Dominio, fichas: dict, config: dict, registro,
             mensajes: list, estado: "_Estado") -> Fin | None:
    """Ejecuta una llamada a herramienta y agrega su resultado. Devuelve un Fin si fue `terminar`."""
    funcion = llamada.get("function") or {}
    nombre = funcion.get("name") or "(sin nombre)"
    ident = llamada.get("id")
    if not ident or ident in estado.vistos:   # el id tiene que ser único en toda la traza
        ident = f"p{paso}-{indice + 1}"
    estado.vistos.add(ident)
    crudos = funcion.get("arguments", {})
    argumentos, error = _parsear(crudos)
    registro.evento("llamada_herramienta", paso=paso, id=ident, nombre=nombre,
                    argumentos=argumentos if error is None else str(crudos))
    inicio = time.perf_counter()
    if error is None and nombre not in fichas:
        error = f"la herramienta «{nombre}» no existe. Las que hay: {', '.join(fichas)}"
    if error is None and nombre == "terminar" and "respuesta" in argumentos:
        argumentos = {**argumentos, "respuesta": _respuesta_final(argumentos["respuesta"])}
    if error is None:
        error = validar_argumentos(fichas[nombre], argumentos)
    tope = config["contexto"]["tope_resultado_caracteres"]
    if error is None and nombre == "terminar":
        respuesta = argumentos["respuesta"]
        problema = _verificar(dominio, estado, respuesta, registro, paso)
        if problema is not None:
            texto, truncado, caracteres = _texto_resultado(
                {"error": f"Todavía no podés terminar: {problema} Corregilo y volvé a llamar a terminar."}, tope)
            _registrar(registro, mensajes, paso, ident, nombre, False, texto, truncado, caracteres, inicio)
            return None
        texto, truncado, caracteres = _texto_resultado({"ok": "respuesta registrada"}, tope)
        _registrar(registro, mensajes, paso, ident, nombre, True, texto, truncado, caracteres, inicio)
        return Fin("respondida" if respuesta is not None else "negada", respuesta, paso, argumentos.get("motivo"))
    clave = _clave(nombre, argumentos) if error is None else None
    if clave in estado.hechas:            # las herramientas son deterministas: repetir solo llena el contexto
        error = _repetida(estado.hechas[clave])
    datos = {"error": error} if error is not None else \
        _ejecutar(dominio.herramientas[nombre], argumentos, config["contexto"]["herramienta_timeout_s"])
    ok = not (isinstance(datos, dict) and "error" in datos)
    if error is None:
        estado.historial.append({"nombre": nombre, "argumentos": argumentos, "datos": datos, "ok": ok})
    texto, truncado, caracteres = _texto_resultado(datos, tope)
    if error is None:
        estado.hechas[clave] = (paso, truncado, None if ok else str(datos["error"]))
    _registrar(registro, mensajes, paso, ident, nombre, ok, texto, truncado, caracteres, inicio)
    return None


def _verificar(dominio: Dominio, estado: "_Estado", respuesta, registro, paso: int) -> str | None:
    """Corre la verificación antes de terminar. Negarse no se verifica, y se rechaza hasta max_rechazos."""
    if dominio.antes_de_terminar is None or respuesta is None:
        return None
    problema = dominio.antes_de_terminar(estado.pregunta, respuesta, estado.historial)
    if problema is not None and estado.rechazos >= estado.max_rechazos:
        registro.evento("verificacion", paso=paso, ok=False, problema=problema, rechazada=False,
                        nota="se llegó al máximo de rechazos: termina igual")
        return None
    registro.evento("verificacion", paso=paso, ok=problema is None, problema=problema,
                    rechazada=problema is not None)
    if problema is not None:
        estado.rechazos += 1
    return problema


def _registrar(registro, mensajes, paso, ident, nombre, ok, texto, truncado, caracteres, inicio):
    registro.evento("resultado_herramienta", paso=paso, id=ident, ok=ok, truncado=truncado, caracteres=caracteres,
                    duracion_ms=round((time.perf_counter() - inicio) * 1000), contenido=texto)
    mensajes.append({"role": "tool", "content": texto, "tool_name": nombre})


def bucle(pregunta: str, config: dict, registro, dominio: Dominio, *, chat=llm.chat,
          dormir=time.sleep) -> Fin:
    frenos = config["frenos"]
    fichas = {f["function"]["name"]: f for f in dominio.fichas}
    mensajes = [{"role": "system", "content": dominio.sistema}, {"role": "user", "content": pregunta}]
    estado = _Estado(pregunta, config.get("agente", {}).get("max_rechazos", 1))
    inicio = time.monotonic()
    if dominio.antes_del_loop is not None:
        extra, usados = dominio.antes_del_loop(pregunta, config, registro, chat)
        mensajes += extra
        estado.tokens += usados
    for paso in range(1, frenos["max_pasos"] + 1):
        if estado.tokens >= frenos["max_tokens"]:
            return Fin("tope_tokens", None, paso - 1,
                       f"se usaron {estado.tokens} tokens (tope {frenos['max_tokens']})")
        if frenos.get("max_seg") and time.monotonic() - inicio > frenos["max_seg"]:
            return Fin("error", None, paso - 1, f"se pasó el tope de {frenos['max_seg']} s")
        try:
            respuesta = _llamar_modelo(mensajes, dominio, config, registro, paso, chat, dormir)
        except llm.ContextOverflow as error:
            return Fin("error", None, paso, f"el contexto no entra en num_ctx: {error}")
        except llm.LLMError as error:
            return Fin("error", None, paso, f"el servidor no respondió después de {frenos['reintentos']} "
                                            f"reintentos: {error}")
        mensaje = respuesta.mensaje
        contenido = mensaje.get("content") or ""
        registro.evento("llamada_modelo", paso=paso, modelo=config["modelo"]["nombre"],
                        num_ctx=config["modelo"]["num_ctx"], tokens_entrada=respuesta.tokens_entrada,
                        tokens_salida=respuesta.tokens_salida, duracion_ms=respuesta.duracion_ms,
                        razon_fin=respuesta.razon_fin, texto=contenido[:500])
        estado.tokens += respuesta.tokens_entrada + respuesta.tokens_salida
        llamadas = mensaje.get("tool_calls") or []
        if not llamadas and (rescatada := rescatar_llamada(contenido, fichas)):
            registro.evento("llamada_rescatada", paso=paso, texto=contenido[:500])
            llamadas = [rescatada]
        mensajes.append({"role": "assistant", "content": contenido, **({"tool_calls": llamadas} if llamadas else {})})
        if not llamadas:
            registro.evento("sin_llamadas", paso=paso, texto=contenido[:500])
            mensajes.append({"role": "user", "content": RECORDATORIO})
            continue
        for indice, llamada in enumerate(llamadas):
            fin = _atender(llamada, indice, paso, dominio, fichas, config, registro, mensajes, estado)
            if fin is not None:
                return fin
    return Fin("tope_pasos", None, frenos["max_pasos"], f"se llegó al tope de {frenos['max_pasos']} pasos")
