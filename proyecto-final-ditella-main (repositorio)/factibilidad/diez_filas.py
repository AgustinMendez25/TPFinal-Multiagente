"""Escribe factibilidad/diez_filas.md: diez filas crudas del CSV, tal como vienen (sin la columna Pasos)."""
import csv
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
CSV = RAIZ.parent / "datos" / "recetas" / "main.csv"
# 6 de recetasgratis (el subconjunto que vamos a usar) y 1 de cada uno de los otros tres sitios grandes
IDS = [1, 5036, 8159, 8883, 7507, 17750, 9880, 15186]
COLUMNAS = ["Id", "Nombre", "URL", "Ingredientes", "Comensales", "Duracion", "Categoria", "Dificultad",
            "Valor nutricional"]

csv.field_size_limit(10**9)
filas = list(csv.DictReader(open(CSV, encoding="utf-8-sig", newline="")))
por_id = {int(f["Id"]): f for f in filas}
otros = [next(f for f in filas if sitio in f["URL"]) for sitio in ("yanuq.com", "cookpad.com")]
elegidas = [por_id[i] for i in IDS] + otros
salida = ["# Diez filas reales de RecetasDeLaAbuela (`main.csv`, commit c9879423)", "",
          "Copiadas tal cual del CSV, sin la columna `Pasos` ni `Contexto`. Las celdas vacías se muestran como `''`.", ""]
for f in elegidas:
    salida.append(f"## Id {f['Id']}: {f['Nombre'].strip()}")
    for c in COLUMNAS[2:]:
        salida.append(f"- **{c}:** `{f[c]!r}`" if c != "Ingredientes" else f"- **Ingredientes:**\n\n  ```\n  {f[c]}\n  ```")
    salida.append("")
(RAIZ / "diez_filas.md").write_text("\n".join(salida), encoding="utf-8")
print(len(elegidas), "filas")
