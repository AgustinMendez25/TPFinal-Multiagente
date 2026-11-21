"""Genera los notebooks de Colab a partir de colab/fuentes/nb*.py.

    uv run colab/construir.py

Cada fuente define NOMBRE (el archivo .ipynb) y CELDAS, una lista de ("md" | "code", texto). Así los
notebooks se revisan como código y se regeneran sin editar JSON a mano.
"""
import importlib.util
import json
from pathlib import Path

COLAB = Path(__file__).resolve().parent


def _lineas(texto: str) -> list[str]:
    partes = texto.strip("\n").split("\n")
    return [p + "\n" for p in partes[:-1]] + [partes[-1]]


def notebook(celdas: list[tuple[str, str]]) -> dict:
    cuerpo = []
    for tipo, texto in celdas:
        if tipo == "md":
            cuerpo.append({"cell_type": "markdown", "metadata": {}, "source": _lineas(texto)})
        elif tipo == "code":
            cuerpo.append({"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
                           "source": _lineas(texto)})
        else:
            raise ValueError(f"tipo de celda desconocido: {tipo}")
    return {"nbformat": 4, "nbformat_minor": 5, "cells": cuerpo,
            "metadata": {"accelerator": "GPU", "colab": {"provenance": [], "gpuType": "T4"},
                         "kernelspec": {"name": "python3", "display_name": "Python 3"},
                         "language_info": {"name": "python"}}}


def _cargar(ruta: Path):
    spec = importlib.util.spec_from_file_location(ruta.stem, ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def construir_todos(carpeta: Path = COLAB) -> list[Path]:
    rutas = []
    for fuente in sorted((COLAB / "fuentes").glob("nb*.py")):
        modulo = _cargar(fuente)
        ruta = Path(carpeta) / modulo.NOMBRE
        ruta.write_text(json.dumps(notebook(modulo.CELDAS), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        rutas.append(ruta)
    return rutas


if __name__ == "__main__":
    for ruta in construir_todos():
        print("escrito", ruta)
