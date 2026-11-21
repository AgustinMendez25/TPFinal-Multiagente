"""El loop del agente, compartido por los dominios (Mundial y recetas).

Lo que resuelve, en el orden de la sección 4 del enunciado:
  1. el ciclo: llamar al modelo, ejecutar cada llamada a herramienta, devolver un resultado por llamada;
  2. el contrato: cada herramienta tiene su ficha JSON y los argumentos se validan contra ella;
  3. la salida mal formada: JSON roto, herramienta inexistente o argumentos equivocados vuelven al
     modelo como error, y el loop sigue;
  4. las herramientas que fallan: excepciones, timeouts y resultados vacíos también vuelven como texto;
  5. el contexto: un resultado más largo que `contexto.tope_resultado_caracteres` se recorta;
  6. los reintentos: un error del servidor se reintenta `frenos.reintentos` veces, con espera creciente;
  7. la parada: topes de pasos, de tokens y (opcional) de segundos, y `terminar(respuesta, motivo)`;
  8. las trazas: un evento por cada cosa que pasa.
"""
import json
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturoVencido
from dataclasses import dataclass
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


def _atender(llamada: dict, indice: int, paso: int, dominio: Dominio, fichas: dict, config: dict, registro,
             mensajes: list, vistos: set) -> Fin | None:
    """Ejecuta una llamada a herramienta y agrega su resultado. Devuelve un Fin si fue `terminar`."""
    funcion = llamada.get("function") or {}
    nombre = funcion.get("name") or "(sin nombre)"
    ident = llamada.get("id")
    if not ident or ident in vistos:          # el id tiene que ser único en toda la traza
        ident = f"p{paso}-{indice + 1}"
    vistos.add(ident)
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
        texto, truncado, caracteres = _texto_resultado({"ok": "respuesta registrada"}, tope)
        _registrar(registro, mensajes, paso, ident, nombre, True, texto, truncado, caracteres, inicio)
        respuesta = argumentos["respuesta"]
        return Fin("respondida" if respuesta is not None else "negada", respuesta, paso, argumentos.get("motivo"))
    datos = {"error": error} if error is not None else \
        _ejecutar(dominio.herramientas[nombre], argumentos, config["contexto"]["herramienta_timeout_s"])
    ok = not (isinstance(datos, dict) and "error" in datos)
    texto, truncado, caracteres = _texto_resultado(datos, tope)
    _registrar(registro, mensajes, paso, ident, nombre, ok, texto, truncado, caracteres, inicio)
    return None


def _registrar(registro, mensajes, paso, ident, nombre, ok, texto, truncado, caracteres, inicio):
    registro.evento("resultado_herramienta", paso=paso, id=ident, ok=ok, truncado=truncado, caracteres=caracteres,
                    duracion_ms=round((time.perf_counter() - inicio) * 1000), contenido=texto)
    mensajes.append({"role": "tool", "content": texto, "tool_name": nombre})


def bucle(pregunta: str, config: dict, registro, dominio: Dominio, *, chat=llm.chat,
          dormir=time.sleep) -> Fin:
    frenos = config["frenos"]
    fichas = {f["function"]["name"]: f for f in dominio.fichas}
    mensajes = [{"role": "system", "content": dominio.sistema}, {"role": "user", "content": pregunta}]
    tokens = 0
    vistos: set[str] = set()
    inicio = time.monotonic()
    for paso in range(1, frenos["max_pasos"] + 1):
        if tokens >= frenos["max_tokens"]:
            return Fin("tope_tokens", None, paso - 1, f"se usaron {tokens} tokens (tope {frenos['max_tokens']})")
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
        tokens += respuesta.tokens_entrada + respuesta.tokens_salida
        llamadas = mensaje.get("tool_calls") or []
        mensajes.append({"role": "assistant", "content": contenido, **({"tool_calls": llamadas} if llamadas else {})})
        if not llamadas:
            registro.evento("sin_llamadas", paso=paso, texto=contenido[:500])
            mensajes.append({"role": "user", "content": RECORDATORIO})
            continue
        for indice, llamada in enumerate(llamadas):
            fin = _atender(llamada, indice, paso, dominio, fichas, config, registro, mensajes, vistos)
            if fin is not None:
                return fin
    return Fin("tope_pasos", None, frenos["max_pasos"], f"se llegó al tope de {frenos['max_pasos']} pasos")
