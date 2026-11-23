"""El análisis de las mediciones (notebook 05): leer las corridas puntuadas y compararlas con el ruido a la vista.

Sigue la vara de la Clase 12 (Notebook B, §2):
  - el acierto con su intervalo del 95% (Wilson), y el costo al lado;
  - la frontera acierto/costo: lo mejor que se puede comprar con cada presupuesto;
  - las comparaciones de a pares, tarea por tarea, con el test de signo exacto: solo informan las tareas que
    cambian de una versión a otra;
  - pass@k y pass^k con las semillas: si el agente puede resolver una tarea y si se puede confiar en él;
  - el control «mismo gasto»: el voto de mayoría de las corridas del agente base.

Todo es Python común sobre los CSV que escribe evaluar.py (una fila por tarea). No llama al modelo.
"""
import csv
import math
from collections import Counter
from pathlib import Path

from evaluar import normalizar

ABSTENCION = "(se abstiene)"


# --- leer ----------------------------------------------------------------------------------------

def leer_csv(ruta: Path) -> list[dict]:
    with open(ruta, encoding="utf-8", newline="") as archivo:
        filas = list(csv.DictReader(archivo))
    for f in filas:
        for clave in ("llamadas_modelo", "tokens_entrada", "tokens_salida"):
            f[clave] = int(f[clave] or 0)
        for clave in ("costo", "tiempo_s", "tiempo_modelo_s"):
            f[clave] = float(f[clave] or 0)
        f["respondible"] = f["respondible"] in ("True", "true", True)
        f["acierto"] = f["resultado"] == "acierto"
    return filas


def por_tarea(filas: list[dict]) -> dict[str, dict]:
    return {f["tarea"]: f for f in filas}


# --- acierto y costo -----------------------------------------------------------------------------

def wilson(aciertos: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Intervalo de Wilson para una proporción: se porta mejor que la fórmula normal cerca de 0 y de 1."""
    if n == 0:
        return 0.0, 0.0
    p = aciertos / n
    centro = (p + z * z / (2 * n)) / (1 + z * z / n)
    radio = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(0.0, centro - radio), min(1.0, centro + radio)


def resumen(filas: list[dict]) -> dict:
    n = len(filas)
    aciertos = sum(f["acierto"] for f in filas)
    imposibles = [f for f in filas if not f["respondible"]]
    bajo, alto = wilson(aciertos, n)
    return {"tareas": n, "aciertos": aciertos, "acierto": aciertos / n if n else 0.0, "ic_bajo": bajo,
            "ic_alto": alto, "imposibles_bien": sum(f["acierto"] for f in imposibles),
            "imposibles": len(imposibles), "inventos": sum(f["resultado"] == "invento" for f in filas),
            "llamadas_por_tarea": sum(f["llamadas_modelo"] for f in filas) / n if n else 0.0,
            "tokens_por_tarea": sum(f["tokens_entrada"] + f["tokens_salida"] for f in filas) / n if n else 0.0,
            "segundos_por_tarea": sum(f["tiempo_s"] for f in filas) / n if n else 0.0}


def frontera(puntos: dict[str, tuple[float, float]]) -> list[str]:
    """Las versiones en la frontera de Pareto: recorridas de la más barata a la más cara, se queda cada una que
    acierta más que todas las anteriores. `puntos`: versión -> (costo, acierto)."""
    elegidas, mejor = [], -1.0
    for nombre, (costo, acierto) in sorted(puntos.items(), key=lambda kv: (kv[1][0], -kv[1][1])):
        if acierto > mejor:
            elegidas.append(nombre)
            mejor = acierto
    return elegidas


# --- comparaciones de a pares ------------------------------------------------------------------

def test_signo(ganadas: int, perdidas: int) -> float:
    """p de dos colas del test de signo exacto: si el cambio no hiciera nada, cada tarea que cambió sería
    una moneda. Cuenta lo desparejo para los dos lados."""
    n = ganadas + perdidas
    if n == 0:
        return 1.0
    extremo = min(ganadas, perdidas)
    cola = sum(math.comb(n, i) for i in range(extremo + 1)) / 2 ** n
    return min(1.0, 2 * cola)


def comparar(a: list[dict], b: list[dict]) -> dict:
    """B contra A, tarea por tarea (o par tarea-semilla, si se juntan varias corridas)."""
    fa, fb = por_tarea(a), por_tarea(b)
    comunes = sorted(set(fa) & set(fb))
    gana = [t for t in comunes if fb[t]["acierto"] and not fa[t]["acierto"]]
    pierde = [t for t in comunes if fa[t]["acierto"] and not fb[t]["acierto"]]
    return {"pares": len(comunes), "gana": len(gana), "pierde": len(pierde),
            "ambas": sum(fa[t]["acierto"] and fb[t]["acierto"] for t in comunes),
            "ninguna": sum(not fa[t]["acierto"] and not fb[t]["acierto"] for t in comunes),
            "p": test_signo(len(gana), len(pierde)), "tareas_gana": gana, "tareas_pierde": pierde}


def juntar_semillas(corridas: dict[str, list[dict]]) -> list[dict]:
    """Varias corridas de la misma versión como una sola lista de pares (tarea, semilla): la clave pasa a ser
    «tarea@semilla». Sirve para comparar dos versiones emparejando también la semilla."""
    return [f | {"tarea": f"{f['tarea']}@{semilla}"} for semilla, filas in corridas.items() for f in filas]


# --- repeticiones: pass@k, pass^k y el voto ----------------------------------------------------

def pass_k(corridas: list[list[dict]]) -> dict:
    """Con k corridas de la misma versión: pass@k (la resuelve en alguna), pass^k (en todas) y el acierto
    por intento."""
    tablas = [por_tarea(c) for c in corridas]
    tareas = sorted(set.intersection(*(set(t) for t in tablas))) if tablas else []
    alguna = sum(any(t[x]["acierto"] for t in tablas) for x in tareas)
    todas = sum(all(t[x]["acierto"] for t in tablas) for x in tareas)
    intentos = sum(t[x]["acierto"] for t in tablas for x in tareas)
    n = len(tareas)
    return {"k": len(corridas), "tareas": n, "pass_at_k": alguna / n if n else 0.0,
            "pass_hat_k": todas / n if n else 0.0, "por_intento": intentos / (n * len(corridas)) if n else 0.0,
            "mezcladas": [x for x in tareas if 0 < sum(t[x]["acierto"] for t in tablas) < len(tablas)]}


def _clave_respuesta(fila: dict) -> str:
    obtenido = fila.get("obtenido")
    return ABSTENCION if obtenido in (None, "", "None") else normalizar(str(obtenido))


def voto(corridas: list[list[dict]]) -> list[dict]:
    """Voto de mayoría entre corridas (self-consistency aplicado al agente entero). Por tarea gana la
    respuesta más repetida; si empatan, la de la primera corrida. El voto no mira la verdad: se puntúa con
    la fila de una corrida que dio esa respuesta, y su costo es la suma de las corridas."""
    tablas = [por_tarea(c) for c in corridas]
    tareas = sorted(set.intersection(*(set(t) for t in tablas)))
    votadas = []
    for tarea in tareas:
        filas = [t[tarea] for t in tablas]
        claves = [_clave_respuesta(f) for f in filas]
        conteo = Counter(claves)
        maximo = max(conteo.values())
        ganadora = next(c for c in claves if conteo[c] == maximo)       # empate: la primera corrida
        elegida = filas[claves.index(ganadora)]
        votadas.append(elegida | {
            "llamadas_modelo": sum(f["llamadas_modelo"] for f in filas),
            "tokens_entrada": sum(f["tokens_entrada"] for f in filas),
            "tokens_salida": sum(f["tokens_salida"] for f in filas),
            "costo": sum(f["costo"] for f in filas), "tiempo_s": sum(f["tiempo_s"] for f in filas),
            "votos": dict(conteo)})
    return votadas


# --- grupos -------------------------------------------------------------------------------------

def grupos_de(tareas_borrador: list[dict]) -> dict[str, set[str]]:
    """Los grupos declarados antes de medir (borrador_tareas.json): dentro y fuera del esquema del camino
    fijo, imposibles y las que usan el vencimiento."""
    return {
        "dentro del esquema": {t["id"] for t in tareas_borrador if t["en_esquema"] is True},
        "fuera del esquema": {t["id"] for t in tareas_borrador if t["en_esquema"] is False},
        "imposibles": {t["id"] for t in tareas_borrador if not t["respondible"]},
        "usan vencimiento": {t["id"] for t in tareas_borrador if t["usa_vencimiento"]},
    }


def filtrar(filas: list[dict], ids: set[str]) -> list[dict]:
    return [f for f in filas if f["tarea"].split("@")[0] in ids]


# --- trazas ------------------------------------------------------------------------------------

def rechazos(carpeta: Path) -> dict[str, int]:
    """Cuántas veces la verificación devolvió al modelo, por tarea, leído de las trazas de una corrida."""
    import json
    cuenta = {}
    for ruta in sorted(Path(carpeta).glob("*.jsonl")):
        eventos = [json.loads(l) for l in ruta.read_text(encoding="utf-8").splitlines() if l.strip()]
        cuenta[ruta.stem] = sum(e.get("evento") == "verificacion" and bool(e.get("rechazada")) for e in eventos)
    return cuenta
