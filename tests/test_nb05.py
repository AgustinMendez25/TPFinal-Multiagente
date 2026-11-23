"""Las celdas de código del notebook 05 corren de punta a punta sobre una medición sintética.

No usa el modelo ni Drive: arma en una carpeta temporal los CSV que dejaría el 04 (las 25 tandas, con las
tareas congeladas) y trazas mínimas, y ejecuta las celdas en orden. Sirve para encontrar errores de código
antes de abrir el notebook en Colab; los números no significan nada.
"""
import csv
import importlib.util
import json
import random
import sys
import types
from pathlib import Path

import pytest

from colab import tandas
from trazas.registro import Registro

RAIZ = Path(__file__).resolve().parent.parent
COLUMNAS = ["tarea", "dificultad", "respondible", "esperado", "obtenido", "estado", "resultado", "detalle",
            "llamadas_modelo", "tokens_entrada", "tokens_salida", "costo", "tiempo_s", "tiempo_modelo_s"]


def _medicion_sintetica(base: Path) -> dict:
    rutas = {k: base / k for k in ("corridas", "resultados", "registros", "trabajo")}
    for carpeta in rutas.values():
        carpeta.mkdir(parents=True)
    lista = tandas.tareas("congelado")
    for i, tanda in enumerate(tandas.TANDAS_CONGELADAS):
        azar = random.Random(i)
        nombre = tandas.nombre_de(tanda)
        filas = []
        for t in lista:
            acierta = azar.random() < 0.6
            obtenido = (str(t["respuesta"]) if acierta else "otra") if t["respondible"] else (None if acierta else "9")
            resultado = ("acierto" if acierta else "error_respuesta") if t["respondible"] else \
                ("acierto" if acierta else "invento")
            filas.append({"tarea": t["id"], "dificultad": t["dificultad"], "respondible": t["respondible"],
                          "esperado": t["respuesta"], "obtenido": obtenido, "estado": "respondida",
                          "resultado": resultado, "detalle": "", "llamadas_modelo": azar.randint(1, 9),
                          "tokens_entrada": azar.randint(500, 9000), "tokens_salida": 50, "costo": 1000.0,
                          "tiempo_s": 3.0, "tiempo_modelo_s": 2.5})
        with open(rutas["resultados"] / f"{nombre}.csv", "w", encoding="utf-8", newline="") as archivo:
            escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS)
            escritor.writeheader()
            escritor.writerows(filas)
        r = Registro(rutas["corridas"] / nombre, lista[0]["id"])
        r.evento("corrida_inicio", modelo="qwen3:8b", config={"num_ctx": 8192})
        r.evento("verificacion", paso=1, ok=False, problema="x", rechazada=True)
        r.evento("corrida_fin", estado="respondida", respuesta="1", pasos=1)
    (rutas["corridas"] / "mundial__agente-antes__t0__s1337").mkdir()
    return rutas


def test_las_celdas_del_05_corren(tmp_path, monkeypatch):
    rutas = _medicion_sintetica(tmp_path)
    monkeypatch.chdir(RAIZ)
    monkeypatch.syspath_prepend(str(RAIZ / "colab" / "fuentes"))
    spec = importlib.util.spec_from_file_location("nb05", RAIZ / "colab" / "fuentes" / "nb05_analisis.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    codigo = [texto for tipo, texto in modulo.CELDAS if tipo == "code"][2:]    # sin clonar ni preparar
    espacio = {"entorno": types.SimpleNamespace(rutas=lambda: rutas)}
    try:
        import matplotlib
        matplotlib.use("Agg")
    except ImportError:
        codigo = [c for c in codigo if "matplotlib" not in c]
    for celda in codigo:
        exec(celda, espacio)
    salida = rutas["resultados"] / "analisis"
    assert {"tabla_principal.csv", "comparaciones.csv", "pass_k.csv", "por_grupo.csv",
            "corridas_reportadas.txt"} <= {p.name for p in salida.iterdir()}
    comparaciones = list(csv.DictReader(open(salida / "comparaciones.csv", encoding="utf-8")))
    assert len(comparaciones) == 7 and all(int(c["pares"]) == 63 for c in comparaciones)
    reportadas = (salida / "corridas_reportadas.txt").read_text(encoding="utf-8").split()
    assert len(reportadas) == 26 and "mundial__agente-antes__t0__s1337" in reportadas
