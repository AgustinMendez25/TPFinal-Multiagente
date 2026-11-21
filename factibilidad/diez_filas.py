"""Escribe factibilidad/diez_filas.md: diez recetas del dataset final, con la fila cruda del CSV y lo que
se decidió con cada línea de ingrediente.

    python factibilidad/diez_filas.py      (después de factibilidad/preparar_dataset.py)
"""
import csv
import random
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
DATOS = RAIZ.parent / "datos"
SEMILLA = 2026
COLUMNAS = ["URL", "Comensales", "Duracion", "Categoria", "Dificultad", "Valor nutricional"]

csv.field_size_limit(10**9)
final = list(csv.DictReader(open(DATOS / "recetas_final.csv", encoding="utf-8", newline="")))
lineas = {}
for f in csv.DictReader(open(DATOS / "normalizacion" / "lineas.csv", encoding="utf-8", newline="")):
    lineas.setdefault(f["receta_id"], []).append(f)
crudas = {f["Id"]: f for f in csv.DictReader(open(DATOS / "recetas" / "main.csv", encoding="utf-8-sig", newline=""))}

# 4 sin problema y 6 corregidas (al azar con semilla fija), de hasta 10 líneas para que se puedan leer
rng = random.Random(SEMILLA)
legibles = [r for r in final if len(lineas[r["id"]]) <= 10]
elegidas = (rng.sample([r for r in legibles if r["estado"] == "sin_problema"], 4)
            + rng.sample([r for r in legibles if r["estado"] == "corregida"], 6))

salida = ["# Diez filas reales del dataset final",
          "",
          "RecetasDeLaAbuela, `main.csv`, commit `c9879423`. Diez recetas tomadas al azar (semilla "
          f"{SEMILLA}) de `datos/recetas_final.csv`: 4 que no necesitaron ningún cambio y 6 corregidas. De cada una "
          "va la fila cruda del CSV (sin `Pasos` ni `Contexto`) y, abajo, qué se decidió con cada línea de "
          "ingrediente. Las reglas (U01, D02, P01…) están en `datos/normalizacion/equivalencias.csv`; «PAR» es la "
          "cantidad que la propia receta escribe entre paréntesis.",
          ""]
for r in elegidas:
    cruda = crudas[r["id"]]
    salida += [f"## Id {r['id']}: {r['nombre']} ({r['estado'].replace('_', ' ')})", ""]
    salida += [f"- **{c}:** `{cruda[c]!r}`" for c in COLUMNAS]
    salida += ["- **Ingredientes (crudo):**", "", "  ```", f"  {cruda['Ingredientes']}", "  ```", "",
               "| Línea cruda | Ingrediente | Leído | Normalizado | Estado | Reglas |", "|---|---|---|---|---|---|"]
    for f in lineas[r["id"]]:
        leido = f"{float(f['cantidad_leida']):g} {f['unidad_leida']}" if f["cantidad_leida"] else "—"
        norm = f"{float(f['cantidad_normalizada']):g} {f['unidad_normalizada']}" if f["cantidad_normalizada"] else "—"
        salida.append(f"| {f['texto']} | {f['ingrediente']} | {leido} | {norm} | {f['estado']} | {f['reglas']} |")
    salida.append("")
(RAIZ / "diez_filas.md").write_text("\n".join(salida), encoding="utf-8")
print(len(elegidas), "recetas:", [(r["id"], r["estado"]) for r in elegidas])
