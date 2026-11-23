"""Corridas en Drive que se pueden retomar.

Una corrida es una carpeta en Drive con una traza por tarea. Cada tarea corre en el disco local de
Colab y, cuando su traza se cerró, se copia a Drive con un nombre provisorio y se renombra: en Drive
nunca queda una traza a medias. Para retomar se vuelve a llamar a `correr_tanda`: saltea las tareas que
ya tienen en Drive una traza que pasa el validador del kit.

`manifiesto.json` fija el commit con que se corrió: retomar con otro commit es un error, para no mezclar
versiones del harness en una medición. `tomada.json` avisa que alguien está corriendo esa tanda.
"""
import copy
import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Callable

import correr_todas
import libro_cerrado
from trazas import esquema

RAIZ = Path(__file__).resolve().parent.parent


class CommitDistinto(RuntimeError):
    pass


class TandaTomada(RuntimeError):
    pass


def nombre_corrida(conjunto: str, config: str, temperatura: float, semilla: int) -> str:
    return f"{conjunto}__{config}__t{temperatura:g}__s{semilla}"


def config_con(base: dict, **modelo) -> dict:
    nueva = copy.deepcopy(base)
    nueva["modelo"].update(modelo)
    return nueva


def _valor_toml(valor) -> str:
    if isinstance(valor, bool):
        return "true" if valor else "false"
    if isinstance(valor, (int, float)):
        return repr(valor)
    if isinstance(valor, str):
        return json.dumps(valor, ensure_ascii=False)
    raise TypeError(f"no sé escribir en TOML: {valor!r}")


def a_toml(config: dict) -> str:
    """Solo lo que usa config.toml: secciones con valores sueltos."""
    lineas = []
    for seccion, claves in config.items():
        lineas.append(f"[{seccion}]")
        lineas += [f"{clave} = {_valor_toml(valor)}" for clave, valor in claves.items()]
        lineas.append("")
    return "\n".join(lineas)


def _escribir_atomico(ruta: Path, texto: str) -> None:
    provisorio = ruta.with_name(ruta.name + ".tmp")
    provisorio.write_text(texto, encoding="utf-8")
    os.replace(provisorio, ruta)


def _leer_json(ruta: Path) -> dict:
    return json.loads(ruta.read_text(encoding="utf-8"))


def preparar(destino: Path, manifiesto: dict) -> dict:
    destino.mkdir(parents=True, exist_ok=True)
    ruta = destino / "manifiesto.json"
    if ruta.exists():
        previo = _leer_json(ruta)
        if previo["commit"] != manifiesto["commit"]:
            raise CommitDistinto(
                f"La corrida {destino.name} empezó con el commit {previo['commit'][:8]} y ahora el código está en "
                f"{manifiesto['commit'][:8]}. Para retomarla: git checkout {previo['commit'][:8]}. Si no, empezá "
                f"una corrida nueva con otro nombre.")
        return previo
    _escribir_atomico(ruta, json.dumps(manifiesto, ensure_ascii=False, indent=2))
    return manifiesto


def hecha(destino: Path, tarea_id: str) -> bool:
    ruta = destino / f"{tarea_id}.jsonl"
    return ruta.exists() and not esquema.validar_archivo(ruta)


def tomar(destino: Path, quien: str, *, ahora: float | None = None, vigencia_h: float = 2.0) -> None:
    ahora = time.time() if ahora is None else ahora
    destino.mkdir(parents=True, exist_ok=True)
    ruta = destino / "tomada.json"
    if ruta.exists():
        previa = _leer_json(ruta)
        hace = ahora - previa["latido"]
        if previa["quien"] != quien and hace < vigencia_h * 3600:
            raise TandaTomada(f"La tanda {destino.name} la está corriendo {previa['quien']} (último avance hace "
                              f"{hace / 60:.0f} min). Elegí otra.")
    _escribir_atomico(ruta, json.dumps({"quien": quien, "inicio": ahora, "latido": ahora}))


def latido(destino: Path, quien: str, *, ahora: float | None = None) -> None:
    ruta = destino / "tomada.json"
    datos = _leer_json(ruta) if ruta.exists() else {"quien": quien, "inicio": ahora}
    datos |= {"quien": quien, "latido": time.time() if ahora is None else ahora}
    _escribir_atomico(ruta, json.dumps(datos))


def copiar_traza(trabajo: Path, destino: Path, tarea_id: str) -> None:
    """La salida primero y la traza al final: si hay .jsonl en Drive, la tarea terminó."""
    for sufijo in (".salida.txt", ".jsonl"):
        origen = trabajo / f"{tarea_id}{sufijo}"
        if origen.exists():
            provisorio = destino / f"{tarea_id}{sufijo}.tmp"
            shutil.copyfile(origen, provisorio)
            os.replace(provisorio, destino / f"{tarea_id}{sufijo}")


def estado(destino: Path, tareas: list[dict], *, ahora: float | None = None) -> dict:
    ahora = time.time() if ahora is None else ahora
    en_drive = sum(hecha(destino, t["id"]) for t in tareas) if destino.exists() else 0
    tomada = destino / "tomada.json"
    datos = _leer_json(tomada) if tomada.exists() else None
    return {"en_drive": en_drive, "total": len(tareas), "tomada_por": datos["quien"] if datos else None,
            "hace_min": round((ahora - datos["latido"]) / 60) if datos else None}


def correr_tanda(tareas: list[dict], destino: Path, trabajo: Path, correr_una: Callable[[dict, Path], None], *,
                 manifiesto: dict, quien: str, antes_de_cada: Callable[[], None] | None = None,
                 al_avanzar: Callable[[str], None] = print) -> dict:
    # Una tanda completa no corre nada, así que no importa con qué commit está el código ahora: sin
    # este atajo, volver a abrir un notebook después de un push trababa las celdas de corridas ya hechas.
    if all(hecha(destino, t["id"]) for t in tareas):
        return {"tareas": len(tareas), "en_drive": len(tareas), "corridas_ahora": 0, "completa": True}
    preparar(destino, manifiesto)
    tomar(destino, quien)
    trabajo.mkdir(parents=True, exist_ok=True)
    corridas_ahora = 0
    for tarea in tareas:
        if hecha(destino, tarea["id"]):
            continue
        if antes_de_cada:
            antes_de_cada()
        correr_una(tarea, trabajo)
        copiar_traza(trabajo, destino, tarea["id"])
        latido(destino, quien)
        corridas_ahora += 1
        listas = sum(hecha(destino, t["id"]) for t in tareas)
        al_avanzar(f"{tarea['id']}: lista · {listas}/{len(tareas)} en Drive")
    en_drive = sum(hecha(destino, t["id"]) for t in tareas)
    completa = en_drive == len(tareas)
    if completa:
        (destino / "tomada.json").unlink(missing_ok=True)
    return {"tareas": len(tareas), "en_drive": en_drive, "corridas_ahora": corridas_ahora, "completa": completa}


def corredor_agente(config_path: Path, dominio: str, timeout_s: float = 600) -> Callable[[dict, Path], None]:
    def correr(tarea: dict, trabajo: Path) -> None:
        correr_todas.correr_tarea(tarea, trabajo, RAIZ / "agente.py", sys.executable, timeout_s, config_path,
                                  dominio=dominio)
    return correr


def corredor_libro_cerrado(config: dict, sistema: str | None = None) -> Callable[[dict, Path], None]:
    """`sistema`: el prompt de sistema; por defecto, el del Mundial (libro_cerrado.SISTEMA)."""
    modelo = config["modelo"]

    def correr(tarea: dict, trabajo: Path) -> None:
        libro_cerrado.responder_tarea(tarea, trabajo, modelo=modelo["nombre"], num_ctx=modelo["num_ctx"],
                                      temperatura=modelo["temperatura"], semilla=modelo["semilla"],
                                      sistema=sistema or libro_cerrado.SISTEMA)
    return correr


def corredor_camino_fijo(config: dict) -> Callable[[dict, Path], None]:
    from lineas_de_base import camino_fijo

    def correr(tarea: dict, trabajo: Path) -> None:
        camino_fijo.responder_tarea(tarea, trabajo, config=config)
    return correr
