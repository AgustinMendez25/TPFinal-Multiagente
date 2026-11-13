"""Planilla para revisar a mano las equivalencias dudosas, y aplicar lo que se decida.

    python factibilidad/planilla_revision.py            # arma datos/normalizacion/revision_equivalencias.csv
    python factibilidad/planilla_revision.py --aplicar  # pasa las decisiones a equivalencias.csv

La planilla tiene una fila por equivalencia dudosa, ordenadas por cuántas recetas destraba aprobarla, con
tres líneas reales que la usan. Quien revisa completa cuatro columnas:

  decision     aprobar   -> la equivalencia pasa a «ok» con su factor actual
               corregir  -> pasa a «ok» con el factor de `factor_nuevo`
               mantener  -> sigue «dudosa» (esas recetas quedan apartadas)
               (vacío)   -> todavía no se revisó; no se toca
  factor_nuevo solo con «corregir»: un número (con punto o coma decimal)
  revisor      quién la revisó (obligatorio si hay decisión)
  comentario   opcional: por qué

Después de --aplicar hay que volver a correr preparar_dataset.py, diez_filas.py y borrador_respuestas.py.
Rearmar la planilla no pisa una que ya tenga decisiones, salvo con --forzar.
"""
import argparse
import collections
import csv
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent.parent / "datos" / "normalizacion"
EQUIVALENCIAS = DIR / "equivalencias.csv"
PLANILLA = DIR / "revision_equivalencias.csv"
EJEMPLOS = 3
COLUMNAS = ["id", "equivalencia", "nota", "recetas_que_destraba", "recetas_que_la_usan", "lineas_que_la_usan",
            "ejemplo_1", "ejemplo_2", "ejemplo_3", "factor_actual", "decision", "factor_nuevo", "revisor",
            "comentario"]
DECISIONES = {"aprobar", "corregir", "mantener", ""}


def leer(ruta: Path, **kw) -> list[dict]:
    with open(ruta, encoding="utf-8-sig", newline="") as archivo:
        return list(csv.DictReader(archivo, **kw))


def escribir(ruta: Path, filas: list[dict], campos: list[str], bom: bool = False) -> None:
    with open(ruta, "w", encoding="utf-8-sig" if bom else "utf-8", newline="") as archivo:
        w = csv.DictWriter(archivo, fieldnames=campos, lineterminator=chr(10))
        w.writeheader()
        w.writerows(filas)


def legible(e: dict) -> str:
    ing = "cualquier ingrediente" if e["ingrediente"] == "*" else e["ingrediente"]
    return f"{ing}: 1 {e['unidad_origen']} = {e['factor']} {e['unidad_destino']}"


def armar(forzar: bool) -> None:
    if PLANILLA.exists() and not forzar and any(f["decision"].strip() for f in leer(PLANILLA)):
        sys.exit(f"{PLANILLA.name} ya tiene decisiones cargadas. Aplicalas con --aplicar, o rearmala con --forzar "
                 "(se pierden).")
    dudosas = [e for e in leer(EQUIVALENCIAS) if e["estado"] == "dudosa"]
    ids = {e["id"] for e in dudosas}

    # qué recetas y líneas usa cada regla, y cuántas recetas tienen esa regla como única duda
    recetas, lineas, textos = (collections.defaultdict(set), collections.Counter(),
                               collections.defaultdict(collections.Counter))
    for f in leer(DIR / "lineas.csv"):
        for regla in f["reglas"].split():
            if regla in ids:
                recetas[regla].add(f["receta_id"])
                lineas[regla] += 1
                convertido = f"{float(f['cantidad_normalizada']):g} {f['unidad_normalizada']}"
                textos[regla][f"{f['texto']} → {convertido} (receta {f['receta_id']})"] += 1
    destraba = collections.Counter()
    for f in leer(DIR / "revision_dudosas.csv"):
        reglas = f["reglas_dudosas"].split()
        if len(reglas) == 1:
            destraba[reglas[0]] += 1

    filas = []
    for e in dudosas:
        # los ejemplos más repetidos, sin repetir el mismo texto
        vistos, ejemplos = set(), []
        for texto, _ in textos[e["id"]].most_common():
            clave = texto.split(" → ")[0].casefold()
            if clave not in vistos:
                vistos.add(clave)
                ejemplos.append(texto)
            if len(ejemplos) == EJEMPLOS:
                break
        ejemplos += [""] * (EJEMPLOS - len(ejemplos))
        filas.append({"id": e["id"], "equivalencia": legible(e), "nota": e["nota"],
                      "recetas_que_destraba": destraba[e["id"]], "recetas_que_la_usan": len(recetas[e["id"]]),
                      "lineas_que_la_usan": lineas[e["id"]], "ejemplo_1": ejemplos[0], "ejemplo_2": ejemplos[1],
                      "ejemplo_3": ejemplos[2], "factor_actual": e["factor"], "decision": "", "factor_nuevo": "",
                      "revisor": "", "comentario": ""})
    filas.sort(key=lambda f: (-f["recetas_que_destraba"], -f["recetas_que_la_usan"], f["id"]))
    escribir(PLANILLA, filas, COLUMNAS, bom=True)   # con BOM para que Excel lea bien las tildes
    print(f"{PLANILLA} — {len(filas)} equivalencias dudosas; las 10 primeras destraban "
          f"{sum(f['recetas_que_destraba'] for f in filas[:10])} recetas")


def aplicar() -> None:
    if not PLANILLA.exists():
        sys.exit(f"No existe {PLANILLA.name}: armala primero.")
    equivalencias = leer(EQUIVALENCIAS)
    por_id = {e["id"]: e for e in equivalencias}
    errores, cambios = [], collections.Counter()
    for n, f in enumerate(leer(PLANILLA), 2):   # n = fila en la planilla (la 1 es el encabezado)
        decision = f["decision"].strip().casefold()
        if decision not in DECISIONES:
            errores.append(f"fila {n} ({f['id']}): decisión «{f['decision']}» no válida; usá aprobar, corregir o mantener")
            continue
        if not decision:
            continue
        if f["id"] not in por_id:
            errores.append(f"fila {n}: no existe la equivalencia {f['id']}")
            continue
        if not f["revisor"].strip():
            errores.append(f"fila {n} ({f['id']}): falta quién la revisó")
            continue
        e = por_id[f["id"]]
        if decision == "corregir":
            try:
                factor = float(f["factor_nuevo"].strip().replace(",", "."))
                assert factor > 0
            except (ValueError, AssertionError):
                errores.append(f"fila {n} ({f['id']}): «corregir» necesita un factor_nuevo positivo")
                continue
            e["factor"] = f"{factor:g}"
        if decision in ("aprobar", "corregir"):
            e["estado"] = "ok"
        marca = f"revisada por {f['revisor'].strip()}: {decision}"
        if f["comentario"].strip():
            marca += f" ({f['comentario'].strip()})"
        e["nota"] = f"{e['nota']}; {marca}" if e["nota"] else marca
        cambios[decision] += 1
    if errores:
        sys.exit("No se aplicó nada. Errores:\n  " + "\n  ".join(errores))
    escribir(EQUIVALENCIAS, equivalencias, list(equivalencias[0]))
    print(f"equivalencias.csv actualizado: {dict(cambios) or 'ninguna decisión cargada'}")
    print("Ahora: preparar_dataset.py, diez_filas.py y borrador_respuestas.py; después, planilla_revision.py "
          "para rearmar la planilla con lo que quede dudoso.")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--aplicar", action="store_true", help="pasar las decisiones a equivalencias.csv")
    parser.add_argument("--forzar", action="store_true", help="rearmar aunque la planilla tenga decisiones")
    args = parser.parse_args()
    aplicar() if args.aplicar else armar(args.forzar)
