"""Borrador para la prueba de factibilidad: carga el corpus y busca recetas por ingredientes.

No es la herramienta final. Sirve para generar, a mano, el resultado de búsqueda que se pega en el
prompt (versión mínima de la prueba, sin loop). Usa solo el subconjunto de recetasgratis.net, que
trae los ingredientes como lista de líneas.
"""
import ast
import csv
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

CSV = Path(__file__).resolve().parent.parent / "datos" / "recetas" / "main.csv"

# sinónimos regionales: la clave es el nombre canónico
SINONIMOS = {
    "papa": ["papa", "patata"], "tomate": ["tomate", "jitomate"], "lenteja": ["lenteja"],
    "arroz": ["arroz"], "huevo": ["huevo"], "cebolla": ["cebolla"], "pollo": ["pollo"],
    "zanahoria": ["zanahoria"], "harina": ["harina"], "leche": ["leche"],
    "manteca": ["mantequilla", "manteca"],
}


def normalizar(texto: str) -> str:
    sin_tildes = "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))
    return sin_tildes.casefold()


def _patron(ingrediente: str) -> re.Pattern:
    formas = SINONIMOS.get(ingrediente, [ingrediente])
    return re.compile(r"\b(" + "|".join(normalizar(f) for f in formas) + r")(e?s)?\b")


@lru_cache(maxsize=1)
def corpus() -> list[dict]:
    csv.field_size_limit(10**9)
    recetas = []
    with open(CSV, encoding="utf-8-sig", newline="") as archivo:
        for fila in csv.DictReader(archivo):
            if "recetasgratis.net" not in fila["URL"]:
                continue
            try:
                lineas = ast.literal_eval(fila["Ingredientes"])
            except (ValueError, SyntaxError):
                continue
            comensales = re.match(r"\d+", fila["Comensales"])
            h, m = (fila["Duracion"].split(":") + ["0"])[:2] if fila["Duracion"] else ("", "")
            recetas.append({
                "id": int(fila["Id"]), "nombre": fila["Nombre"].strip(),
                "comensales": int(comensales.group()) if comensales else None,
                "minutos": int(h) * 60 + int(m) if h.isdigit() and m.isdigit() else None,
                "ingredientes": [l.strip() for l in lineas],
                "categoria": fila["Categoria"],
            })
    return recetas


def _usa(receta: dict, ingrediente: str) -> bool:
    patron = _patron(ingrediente)
    return any(patron.search(normalizar(l)) for l in receta["ingredientes"])


def buscar_recetas(con: list[str], sin: list[str] = (), limite: int = 5) -> dict:
    hallados = [r for r in corpus() if all(_usa(r, i) for i in con) and not any(_usa(r, i) for i in sin)]
    hallados.sort(key=lambda r: (len(r["ingredientes"]), r["id"]))
    return {"total": len(hallados), "recetas": [
        {"id": r["id"], "nombre": r["nombre"], "comensales": r["comensales"], "minutos": r["minutos"],
         "cantidad_ingredientes": len(r["ingredientes"])} for r in hallados[:limite]]}


def detalle_receta(receta_id: int) -> dict:
    receta = next((r for r in corpus() if r["id"] == receta_id), None)
    if receta is None:
        return {"error": f"No existe la receta {receta_id}."}
    return {k: receta[k] for k in ("id", "nombre", "comensales", "minutos", "ingredientes")}
