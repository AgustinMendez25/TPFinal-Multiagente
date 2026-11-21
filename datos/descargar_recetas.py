"""Baja RecetasDeLaAbuela (SomosNLP, OpenRAIL) en un commit fijado a datos/recetas/main.csv.

    python datos/descargar_recetas.py
"""
import urllib.request
from pathlib import Path

COMMIT = "c9879423aeb4b151fb8941f79098e9606d25c782"
URL = f"https://huggingface.co/datasets/somosnlp/RecetasDeLaAbuela/resolve/{COMMIT}/main.csv"
DESTINO = Path(__file__).resolve().parent / "recetas" / "main.csv"

if __name__ == "__main__":
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(URL, DESTINO)
    print(f"{DESTINO} ({DESTINO.stat().st_size} bytes)")
