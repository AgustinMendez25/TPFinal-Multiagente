"""Arma el dataset final de recetas con una unidad por ingrediente y registra cada decisión en CSV.

    python factibilidad/preparar_dataset.py

Entrada:
  datos/recetas/main.csv                    el CSV crudo (commit fijado, lo baja datos/descargar_recetas.py)
  datos/normalizacion/equivalencias.csv     la tabla de conversiones, editable; cada fila es "ok" o "dudosa"

Salida:
  datos/recetas_final.csv                       el dataset final: recetas sin problemas o corregidas
  datos/normalizacion/unidades_por_ingrediente.csv  la unidad elegida para cada ingrediente
  datos/normalizacion/lineas.csv                qué se decidió con cada línea de ingrediente
  datos/normalizacion/revision_dudosas.csv      recetas apartadas porque usan una equivalencia dudosa
  datos/normalizacion/RESUMEN.md                los conteos

Para aprobar una equivalencia dudosa: cambiar su `estado` a "ok" en equivalencias.csv y volver a correr.
"""
import collections
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import normalizar as N  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
DIR = REPO / "datos" / "normalizacion"
SALIDA = REPO / "datos" / "recetas_final.csv"
NO_CONVERTIBLES = {"pizca", "chorro", "puñado", "gota"}   # no son una cantidad: no se pueden convertir


# --- equivalencias -------------------------------------------------------------------------------

def cargar_equivalencias():
    universal, densidad, peso, especial = {}, {}, {}, {}
    with open(DIR / "equivalencias.csv", encoding="utf-8", newline="") as archivo:
        for f in csv.DictReader(archivo):
            regla = (float(f["factor"]), f["id"], f["estado"].strip())
            if f["tipo"] == "universal":
                universal[f["unidad_origen"]] = (f["unidad_destino"],) + regla
            elif f["tipo"] == "densidad":
                densidad[f["ingrediente"]] = regla                  # g por ml
            elif f["tipo"] == "peso_unidad":
                peso[f["ingrediente"]] = regla                      # g por unidad
            elif f["tipo"] == "especial":
                especial[(f["ingrediente"], f["unidad_origen"])] = (f["unidad_destino"],) + regla
    return universal, densidad, peso, especial


UNIVERSAL, DENSIDAD, PESO, ESPECIAL = cargar_equivalencias()
ESTADO_REGLA = {r[2]: r[3] for r in UNIVERSAL.values()} | {r[1]: r[2] for r in DENSIDAD.values()} | \
               {r[1]: r[2] for r in PESO.values()} | {r[2]: r[3] for r in ESPECIAL.values()}
ESTADO_REGLA["PAR"] = "ok"


def familia(ing: str, unidad: str) -> str:
    """La unidad después de las conversiones que no dependen de nada más (universales y especiales)."""
    for _ in range(3):
        if (ing, unidad) in ESPECIAL:
            unidad = ESPECIAL[(ing, unidad)][0]
        elif unidad in UNIVERSAL:
            unidad = UNIVERSAL[unidad][0]
        else:
            break
    return unidad


def convertir(ing: str, cantidad: float, unidad: str, destino: str):
    """Lleva (cantidad, unidad) a `destino`. Devuelve (cantidad, [ids de reglas]) o None si no hay camino."""
    reglas = []
    # se encadenan: "1 cucharadita de ajo" -> 5 ml (U03) -> 1 diente (E03)
    for _ in range(3):
        if unidad == destino:
            break
        if (ing, unidad) in ESPECIAL:
            nueva, factor, id_, _ = ESPECIAL[(ing, unidad)]
        elif unidad in UNIVERSAL:
            nueva, factor, id_, _ = UNIVERSAL[unidad]
        else:
            break
        cantidad, unidad = cantidad * factor, nueva
        reglas.append(id_)
    if unidad == destino:
        return cantidad, reglas
    par = {unidad, destino}
    if par == {"g", "ml"} and ing in DENSIDAD:
        factor, id_, _ = DENSIDAD[ing]
        return (cantidad * factor if destino == "g" else cantidad / factor), reglas + [id_]
    if par == {"g", "unidad"} and ing in PESO:
        factor, id_, _ = PESO[ing]
        return (cantidad * factor if destino == "g" else cantidad / factor), reglas + [id_]
    if par == {"ml", "unidad"} and ing in DENSIDAD and ing in PESO:
        (fd, id_d, _), (fp, id_p, _) = DENSIDAD[ing], PESO[ing]
        valor = cantidad * fd / fp if destino == "unidad" else cantidad * fp / fd
        return valor, reglas + [id_d, id_p]
    return None


# --- decisiones por línea ------------------------------------------------------------------------

def unidad_efectiva(linea: dict) -> str | None:
    if linea["parentesis"]:
        return linea["parentesis"][1]
    if linea["cantidad"] is None or linea["rango"] or linea["unidad"] in NO_CONVERTIBLES:
        return None
    return familia(linea["ingrediente"], linea["unidad"])


def decidir(linea: dict, destino: str) -> dict:
    """estado: basico, sin_cambio, corregida, dudosa o descartada."""
    ing = linea["ingrediente"]
    d = {"unidad_normalizada": destino, "cantidad_normalizada": None, "reglas": [], "motivo": ""}
    if ing in N.BASICOS:
        return d | {"estado": "basico", "unidad_normalizada": "", "motivo": "básico: no se cuenta ni se compara"}
    if linea["cantidad"] is None:
        return d | {"estado": "descartada", "motivo": "la línea no trae cantidad"}
    if linea["rango"]:
        return d | {"estado": "descartada", "motivo": "cantidad en rango (\"2 o 3\")"}
    if linea["parentesis"]:
        valor, unidad = linea["parentesis"]
        r = convertir(ing, valor, unidad, destino)
        if r:
            return d | {"estado": _estado(["PAR"] + r[1]), "cantidad_normalizada": r[0], "reglas": ["PAR"] + r[1],
                        "motivo": "se usa la cantidad que la receta escribe entre paréntesis"}
    if linea["unidad"] in NO_CONVERTIBLES:
        return d | {"estado": "descartada", "motivo": f"«{linea['unidad']}» no es una cantidad convertible"}
    r = convertir(ing, linea["cantidad"], linea["unidad"], destino)
    if r is None:
        return d | {"estado": "descartada", "motivo": f"sin equivalencia de «{linea['unidad']}» a «{destino}» para {ing}"}
    return d | {"estado": _estado(r[1]), "cantidad_normalizada": r[0], "reglas": r[1]}


def _estado(reglas: list[str]) -> str:
    if not reglas:
        return "sin_cambio"
    return "dudosa" if any(ESTADO_REGLA[r] == "dudosa" for r in reglas) else "corregida"


PRIORIDAD = ["sin_problema", "corregida", "dudosa", "descartada"]
DE_LINEA_A_RECETA = {"basico": "sin_problema", "sin_cambio": "sin_problema", "corregida": "corregida",
                     "dudosa": "dudosa", "descartada": "descartada"}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    trabajo = N.corpus_trabajo()
    base = [r for r in trabajo if all(i["ingrediente"] for i in r["ingredientes"])]

    # 1. la unidad de cada ingrediente: la más frecuente en el corpus base (no depende del inventario)
    frec = collections.defaultdict(collections.Counter)
    for r in base:
        for i in r["ingredientes"]:
            if i["ingrediente"] not in N.BASICOS:
                u = unidad_efectiva(i)
                if u:
                    frec[i["ingrediente"]][u] += 1
    unidad = {ing: c.most_common(1)[0][0] for ing, c in frec.items()}

    # 2. decidir cada línea y cada receta
    filas_lineas, finales, dudosas = [], [], []
    c_lineas, c_recetas = collections.Counter(), collections.Counter()
    motivos, uso_reglas = collections.Counter(), collections.defaultdict(set)
    bloquea = collections.Counter()   # recetas que se destrabarían si se aprueba la regla (es lo único dudoso)
    for r in base:
        decisiones = []
        for n, i in enumerate(r["ingredientes"], 1):
            d = decidir(i, unidad.get(i["ingrediente"], ""))
            decisiones.append((i, d))
            c_lineas[d["estado"]] += 1
            if d["estado"] == "descartada":
                motivos[d["motivo"].split(" para ")[0]] += 1
            for regla in d["reglas"]:
                uso_reglas[regla].add(r["id"])
            filas_lineas.append({"receta_id": r["id"], "linea": n, "texto": i["texto"], "ingrediente": i["ingrediente"],
                                 "cantidad_leida": i["cantidad"], "unidad_leida": i["unidad"] or "",
                                 "parentesis": f"{i['parentesis'][0]:g} {i['parentesis'][1]}" if i["parentesis"] else "",
                                 "estado": d["estado"], "unidad_normalizada": d["unidad_normalizada"],
                                 "cantidad_normalizada": "" if d["cantidad_normalizada"] is None
                                 else round(d["cantidad_normalizada"], 2),
                                 "reglas": " ".join(d["reglas"]), "motivo": d["motivo"]})
        estado = max((DE_LINEA_A_RECETA[d["estado"]] for _, d in decisiones), key=PRIORIDAD.index)
        c_recetas[estado] += 1
        if estado == "dudosa":
            reglas_dudosas = sorted({x for _, d in decisiones for x in d["reglas"] if ESTADO_REGLA[x] == "dudosa"})
            if len(reglas_dudosas) == 1:
                bloquea[reglas_dudosas[0]] += 1
            dudosas.append({"receta_id": r["id"], "nombre": r["nombre"], "url": r["url"],
                            "reglas_dudosas": " ".join(reglas_dudosas),
                            "lineas_dudosas": " | ".join(f"{i['texto']} [{' '.join(d['reglas'])}]"
                                                         for i, d in decisiones if d["estado"] == "dudosa")})
        if estado in ("sin_problema", "corregida"):
            finales.append({"id": r["id"], "nombre": r["nombre"], "url": r["url"], "comensales": r["comensales"],
                            "minutos": r["minutos"], "categoria": r["categoria"], "estado": estado,
                            "ingredientes": json.dumps(
                                [{"ingrediente": i["ingrediente"],
                                  "cantidad": None if d["cantidad_normalizada"] is None else round(d["cantidad_normalizada"], 2),
                                  "unidad": d["unidad_normalizada"] or None, "estado": d["estado"],
                                  "texto": i["texto"]}
                                 for i, d in decisiones], ensure_ascii=False)})

    # 3. escribir
    def escribir(ruta, filas, campos):
        with open(ruta, "w", encoding="utf-8", newline="") as archivo:
            w = csv.DictWriter(archivo, fieldnames=campos, lineterminator=chr(10))
            w.writeheader()
            w.writerows(filas)

    escribir(DIR / "unidades_por_ingrediente.csv",
             [{"ingrediente": ing, "unidad": unidad[ing], "lineas": sum(c.values()),
               "lineas_en_esa_unidad": c[unidad[ing]], "porcentaje": f"{c[unidad[ing]] / sum(c.values()):.0%}",
               "otras_unidades": " ".join(f"{u}:{n}" for u, n in c.most_common()[1:6])}
              for ing, c in sorted(frec.items(), key=lambda x: -sum(x[1].values()))],
             ["ingrediente", "unidad", "lineas", "lineas_en_esa_unidad", "porcentaje", "otras_unidades"])
    escribir(DIR / "lineas.csv", filas_lineas, list(filas_lineas[0]))
    escribir(DIR / "revision_dudosas.csv", dudosas, ["receta_id", "nombre", "url", "reglas_dudosas", "lineas_dudosas"])
    escribir(SALIDA, finales, list(finales[0]))

    # 4. resumen
    total_rg = sum(1 for f in csv.DictReader(open(N.CSV, encoding="utf-8-sig", newline=""))
                   if "recetasgratis.net" in f["URL"])
    no_basicas = sum(v for k, v in c_lineas.items() if k != "basico")
    reglas = {}
    with open(DIR / "equivalencias.csv", encoding="utf-8", newline="") as archivo:
        for f in csv.DictReader(archivo):
            reglas[f["id"]] = f
    usadas = [x for x in reglas if uso_reglas.get(x)]
    res = [
        "# Resumen de la normalización de unidades",
        "",
        "Generado por `factibilidad/preparar_dataset.py`. No editar a mano.",
        "",
        "## Embudo",
        "",
        "| Paso | Recetas |", "|---|---|",
        f"| recetasgratis.net | {total_rg} |",
        f"| con comensales, duración y al menos 3 líneas | {len(trabajo)} |",
        f"| con todas las líneas reconocidas por el léxico (corpus base) | {len(base)} |",
        f"| **dataset final** (sin problema + corregidas) | **{len(finales)}** |",
        "",
        "## Recetas del corpus base",
        "",
        "| Estado | Recetas | Qué significa |", "|---|---|---|",
        f"| sin_problema | {c_recetas['sin_problema']} ({c_recetas['sin_problema'] / len(base):.0%}) | todas sus cantidades ya venían en la unidad elegida |",
        f"| corregida | {c_recetas['corregida']} ({c_recetas['corregida'] / len(base):.0%}) | al menos una cantidad se convirtió con una equivalencia «ok» |",
        f"| dudosa | {c_recetas['dudosa']} ({c_recetas['dudosa'] / len(base):.0%}) | usa al menos una equivalencia «dudosa»: apartada para revisión |",
        f"| descartada | {c_recetas['descartada']} ({c_recetas['descartada'] / len(base):.0%}) | tiene una línea sin cantidad convertible |",
        "",
        "## Líneas de ingrediente del corpus base",
        "",
        "| Estado | Líneas | % de las no básicas |", "|---|---|---|",
        f"| basico (sal, aceite, condimentos, hierbas) | {c_lineas['basico']} | — |",
    ] + [f"| {k} | {c_lineas[k]} | {c_lineas[k] / no_basicas:.0%} |" for k in ("sin_cambio", "corregida", "dudosa", "descartada")] + [
        "",
        "## Por qué se descartan líneas",
        "",
        "| Motivo | Líneas |", "|---|---|",
    ] + [f"| {m} | {n} |" for m, n in motivos.most_common(15)] + [
        "",
        "## Equivalencias",
        "",
        f"La tabla tiene {len(reglas)} equivalencias: {sum(f['estado'] == 'ok' for f in reglas.values())} «ok» y "
        f"{sum(f['estado'] == 'dudosa' for f in reglas.values())} «dudosa». Se usan {len(usadas)}, más «PAR» (la "
        "cantidad que la propia receta escribe entre paréntesis).",
        "",
        "Equivalencias dudosas, ordenadas por cuántas recetas destrabaría aprobarlas (recetas cuya única duda es esa):",
        "",
        "| id | Equivalencia | Recetas que la usan | Se destraban si se aprueba | Nota |", "|---|---|---|---|---|",
    ] + [f"| {x} | {reglas[x]['ingrediente']}: 1 {reglas[x]['unidad_origen']} = {reglas[x]['factor']} "
         f"{reglas[x]['unidad_destino']} | {len(uso_reglas.get(x, ()))} | {bloquea[x]} | {reglas[x]['nota']} |"
         for x in sorted((x for x in reglas if reglas[x]["estado"] == "dudosa"), key=lambda x: (-bloquea[x], x))]
    (DIR / "RESUMEN.md").write_text("\n".join(res) + "\n", encoding="utf-8")
    print("\n".join(res))

    # 5. registro de decisiones, con lo que afectó cada una
    todas = [i for r in base for i in r["ingredientes"]]
    contar = lambda f: sum(1 for i in todas if f(i))
    con_texto = lambda t: contar(lambda i: t in N.normalizar_texto(i["texto"]))
    estados = collections.Counter(f["estado"] for f in filas_lineas)
    decisiones = [
        ("D01", "fuente", "Usar solo recetasgratis.net",
         "Es el 90% del CSV y trae los ingredientes como lista; los otros sitios suman ~250 recetas útiles y piden "
         "reparar mojibake (cookpad) o cortar por comas (el resto)", f"{total_rg} recetas", "aplicada"),
        ("D02", "filtro", "Exigir comensales, duración y al menos 3 líneas de ingredientes",
         "Un único corpus: todas las recetas sirven para escalar porciones y ordenar por tiempo",
         f"quedan {len(trabajo)} recetas", "aplicada"),
        ("D03", "filtro", "Exigir que el léxico reconozca todas las líneas",
         "Sin eso no se puede saber si una receta cumple una dieta ni qué falta; ampliar el léxico es una "
         "alternativa guardada (~150 nombres más, revisión manual)", f"quedan {len(base)} recetas", "aplicada"),
        ("D04", "léxico", "«pasta de ajo» es ajo y «pasta de ají» es ají, no pasta",
         "Se leían como pasta y aparecían como «1 pizca de pasta»", f"{con_texto('pasta de ajo') + con_texto('pasta de aji')} líneas", "aplicada"),
        ("D05", "léxico", "Perejil, cilantro y albahaca se tratan como básicos (como la sal)",
         "Vienen en pizcas, ramas y puñados, que no son cantidades convertibles",
         f"{contar(lambda i: i['ingrediente'] == 'perejil')} líneas", "aplicada"),
        ("D06", "léxico", "La cebolla de verdeo es un ingrediente distinto de la cebolla",
         "Viene en ramas y tallos; mezclada con la cebolla rompía su unidad",
         f"{contar(lambda i: i['ingrediente'] == 'cebolla de verdeo')} líneas", "aplicada"),
        ("D07", "léxico", "«Consomé» es caldo",
         "«Consomé de pollo» hacía aparecer como receta con pollo a recetas que no lo llevan",
         f"{con_texto('consome')} líneas", "aplicada"),
        ("D08", "unidades", "Cada ingrediente tiene una sola unidad: la más frecuente en el corpus base",
         "Una regla por ingrediente, que no depende del inventario; ver unidades_por_ingrediente.csv",
         f"{len(unidad)} ingredientes", "aplicada"),
        ("D09", "unidades", "kg, l, cl, dl y cc se pasan a g o ml sin aproximar", "Son conversiones exactas",
         "incluidas en las líneas sin_cambio", "aplicada"),
        ("D10", "unidades", "Si la receta escribe la cantidad métrica entre paréntesis, se usa esa",
         "«1 taza de harina (100 gr)»: el dato de la propia receta es mejor que una equivalencia",
         f"{sum('PAR' in f['reglas'].split() for f in filas_lineas)} líneas", "aplicada"),
        ("D11", "unidades", "Medidas caseras, pesos por unidad y envases se convierten con equivalencias estándar «ok»",
         "Ver equivalencias.csv; son aproximaciones declaradas",
         f"{estados['corregida']} líneas corregidas en {c_recetas['corregida']} recetas", "aplicada"),
        ("D12", "unidades", "Las equivalencias marcadas «dudosa» no se aplican: esas recetas quedan apartadas",
         "Ver revision_dudosas.csv; aprobar una equivalencia es cambiar su estado a «ok» y volver a correr",
         f"{estados['dudosa']} líneas en {c_recetas['dudosa']} recetas", "para_revision"),
        ("D13", "unidades", "Pizca, chorro, puñado y gota no se convierten: la receta se descarta",
         "No son una cantidad", f"{sum(f['motivo'].startswith('«') and 'no es una cantidad' in f['motivo'] for f in filas_lineas)} líneas", "aplicada"),
        ("D14", "unidades", "Las cantidades en rango («2 o 3») se descartan", "No hay una cantidad única",
         f"{sum(f['motivo'].startswith('cantidad en rango') for f in filas_lineas)} líneas", "aplicada"),
        ("D15", "unidades", "Un ingrediente no básico sin cantidad descarta la receta",
         "No se puede escalar ni comparar con el inventario",
         f"{sum(f['motivo'] == 'la línea no trae cantidad' for f in filas_lineas)} líneas", "aplicada"),
        ("D16", "unidades", "«Pieza» equivale a una unidad", "«2 piezas de chile» son 2 chiles",
         f"{contar(lambda i: i['unidad'] == 'pieza')} líneas", "aplicada"),
        ("D17", "inventario", "El inventario se expresa en la unidad elegida para cada ingrediente",
         "El corpus no cambia si cambia el inventario", "tareas/recetas_inventario.json", "aplicada"),
        ("D18", "unidades", "Equivalencias revisadas a mano (ver la nota «revisada por» en equivalencias.csv)",
         "Las 39 dudosas se aprobaron en bloque con su valor sugerido el 2026-11-13; registro en "
         "revision_equivalencias_2026-11-13_aprobada.csv",
         f"{sum('revisada por' in f['nota'] for f in reglas.values())} equivalencias revisadas", "aplicada"),
        ("D19", "léxico", "Tortillas (de maíz, de harina) y leches especiales (condensada, evaporada, de coco) son "
         "ingredientes propios",
         "Se leían como maíz, harina o leche: «9 tortillas de maíz» daba 9 choclos y la leche de coco figuraba "
         "como lácteo", f"{sum(contar(lambda i, c=c: i['ingrediente'] == c) for c in ('tortilla de maiz', 'tortilla de harina', 'leche condensada', 'leche evaporada', 'leche de coco'))} líneas",
         "aplicada"),
    ]
    escribir(DIR / "decisiones.csv",
             [dict(zip(["id", "tema", "decision", "motivo", "alcance", "estado"], d)) for d in decisiones],
             ["id", "tema", "decision", "motivo", "alcance", "estado"])


if __name__ == "__main__":
    main()
