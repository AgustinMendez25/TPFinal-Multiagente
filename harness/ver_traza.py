"""Una traza JSONL en texto legible, para mirarla en los notebooks."""
import json
from itertools import zip_longest
from pathlib import Path


def _corto(texto, ancho: int) -> str:
    texto = " ".join(str(texto).split())
    return texto if len(texto) <= ancho else texto[: ancho - 1] + "…"


def _linea(e: dict, ancho: int) -> str:
    tipo, paso = e["evento"], e.get("paso")
    pre = f"[{paso}] " if paso is not None else ""
    if tipo == "corrida_inicio":
        config = e.get("config", {})
        num_ctx = config.get("modelo", {}).get("num_ctx", config.get("num_ctx"))
        return f"INICIO {e['tarea']} · {e['modelo']} · num_ctx {num_ctx}"
    if tipo == "llamada_modelo":
        extra = f" · escribió: {_corto(e['texto'], ancho // 2)}" if e.get("texto") else ""
        return f"{pre}modelo · {e['tokens_entrada']} → {e['tokens_salida']} tokens · {e['duracion_ms'] / 1000:.1f} s{extra}"
    if tipo == "llamada_herramienta":
        argumentos = e["argumentos"] if isinstance(e["argumentos"], str) else json.dumps(e["argumentos"], ensure_ascii=False)
        return f"{pre}→ {e['nombre']}({argumentos})"
    if tipo == "resultado_herramienta":
        marca = "ok" if e["ok"] else "ERROR"
        recorte = " (recortado)" if e["truncado"] else ""
        return f"{pre}← {marca}{recorte} {e['caracteres']} car.: {_corto(e.get('contenido', ''), ancho)}"
    if tipo == "reintento_modelo":
        return f"{pre}reintento {e['intento']}: {_corto(e['motivo'], ancho)}"
    if tipo == "sin_llamadas":
        return f"{pre}sin llamadas, escribió: {_corto(e['texto'], ancho)}"
    if tipo == "corrida_fin":
        return f"FIN {e['estado']} · respuesta: {e['respuesta']!r} · motivo: {e.get('motivo')}"
    return f"{pre}{tipo}"


def _lineas(ruta: Path, ancho: int) -> list[str]:
    eventos = [json.loads(l) for l in Path(ruta).read_text(encoding="utf-8").splitlines() if l.strip()]
    return [_linea(e, ancho) for e in eventos]


def resumen(ruta: Path, *, ancho: int = 160) -> str:
    return "\n".join(_lineas(ruta, ancho))


def comparar(ruta_a: Path, ruta_b: Path, *, ancho: int = 70) -> str:
    filas = zip_longest(_lineas(ruta_a, ancho), _lineas(ruta_b, ancho), fillvalue="")
    return "\n".join(f"{_corto(a, ancho):<{ancho}} | {_corto(b, ancho)}" for a, b in filas)
