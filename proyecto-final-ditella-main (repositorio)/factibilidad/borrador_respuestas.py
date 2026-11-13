"""Borrador del verificador: calcula la respuesta esperada de cada tarea directo sobre el dataset final
(datos/recetas_final.csv), sin pasar por las herramientas del agente.

    python factibilidad/borrador_respuestas.py
    # escribe tareas/recetas.json, tareas/recetas_inventario.json y factibilidad/borrador_tareas.json

Las recetas de cada tarea se eligen con una consulta (no con un id fijo), y cada tarea comprueba con
`assert` que su respuesta no sea ambigua ni dependa de una cantidad aproximada.
"""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import normalizar as N  # noqa: E402

RAIZ = Path(__file__).resolve().parent
DATOS = RAIZ.parent / "datos"
TAREAS = RAIZ.parent / "tareas"

csv.field_size_limit(10**9)
CORPUS = [r | {"id": int(r["id"]), "comensales": int(r["comensales"]), "minutos": int(r["minutos"]),
               "ingredientes": json.loads(r["ingredientes"])}
          for r in csv.DictReader(open(DATOS / "recetas_final.csv", encoding="utf-8", newline=""))]
POR_ID = {r["id"]: r for r in CORPUS}
UNIDAD = {f["ingrediente"]: f["unidad"]
          for f in csv.DictReader(open(DATOS / "normalizacion" / "unidades_por_ingrediente.csv", encoding="utf-8"))}

# inventario de la sesión: ingrediente -> (cantidad, días hasta vencer), en la unidad de cada ingrediente
INVENTARIO = {"pollo": (500, 2), "tomate": (3, 3), "leche": (1000, 5), "zanahoria": (3, 6), "cebolla": (2, 10),
              "huevo": (6, 12), "papa": (5, 15), "arroz": (1000, 60), "harina": (1000, 90), "lenteja": (500, 90)}


def ingredientes(r):
    return {i["ingrediente"] for i in r["ingredientes"]}


def buscar(con, sin=()):
    """El orden de buscar_recetas: por duración y, si empatan, por id."""
    hallados = [r for r in CORPUS if set(con) <= ingredientes(r) and not set(sin) & ingredientes(r)]
    return sorted(hallados, key=lambda r: (r["minutos"], r["id"]))


def apta(r, dieta):
    return not any(N.LEXICO[c][1] & N.DIETAS[dieta] for c in ingredientes(r))


def lineas_de(r, ing):
    return [i for i in r["ingredientes"] if i["ingrediente"] == ing]


def necesario(r, ing, porciones):
    """Cantidad escalada en la unidad del ingrediente (todas las líneas ya están en esa unidad)."""
    return sum(i["cantidad"] for i in lineas_de(r, ing)) * porciones / r["comensales"]


def exacto(r, ing):
    """True si todas las líneas del ingrediente vienen sin conversión aproximada."""
    return all(i["estado"] == "sin_cambio" for i in lineas_de(r, ing))


def faltantes(r, porciones):
    """Lo que falta: no está en el inventario o no alcanza. Si una comparación usa una cantidad aproximada
    (línea «corregida»), la conclusión tiene que valer aunque la equivalencia se equivoque en ±30%."""
    falta = []
    for ing in sorted(ingredientes(r) - N.BASICOS):
        if ing not in INVENTARIO:
            falta.append(ing)
            continue
        nec, hay = necesario(r, ing, porciones), INVENTARIO[ing][0]
        if not exacto(r, ing):
            assert (nec * 0.7 > hay) == (nec * 1.3 > hay), f"receta {r['id']}: «{ing}» depende de la aproximación"
        if nec > hay + 1e-9:
            falta.append(ing)
    return falta


NOMBRES = {"morron": "morrón", "limon": "limón", "maiz": "maíz", "jamon": "jamón", "champinon": "champiñón",
           "aji": "ají", "azucar": "azúcar", "brocoli": "brócoli", "lenteja": "lentejas"}


def nom(ingrediente):
    return NOMBRES.get(ingrediente, ingrediente)


# líneas con errores conocidos del léxico o de equivalencias gruesas: una receta que las tenga no puede
# ser respuesta de una tarea (ver «Fallas conocidas» en la propuesta)
SOSPECHOSAS = [(None, r"vaso\s+peque"),
               ("zapallo", r"calabaza"), ("crema de leche", r"pastelera"), ("manteca", r"vegetal")]


def sospechosa(r):
    import re
    return any((ing is None or i["ingrediente"] == ing) and re.search(patron, i["texto"].casefold())
               for i in r["ingredientes"] for ing, patron in SOSPECHOSAS)


def primera(lista, condicion=lambda r: True):
    return next((r for r in lista if condicion(r)), None)


def texto_lineas(r, ing):
    return " / ".join(i["texto"] for i in lineas_de(r, ing))


def numero(x):
    x = round(x, 2)
    return int(x) if x == int(x) else x


def tareas():
    t = []

    def agregar(pregunta, respuesta, tipo, dificultad, cadena, respondible=True, nota=""):
        t.append({"id": f"rec-{len(t) + 1:03d}", "pregunta": pregunta, "respuesta": respuesta, "tipo": tipo,
                  "tolerancia": 0, "dificultad": dificultad, "respondible": respondible,
                  "cadena_esperada": cadena, "nota": nota})

    def unica_mas_rapida(lista):
        """La primera es la más rápida y no comparte duración con la segunda (no depende del desempate)."""
        assert lista and (len(lista) == 1 or lista[0]["minutos"] < lista[1]["minutos"]), [x["id"] for x in lista[:3]]
        assert not sospechosa(lista[0]), f"receta {lista[0]['id']} con líneas sospechosas"
        return lista[0]

    def primera_apta(cand, dieta):
        """La primera apta de la búsqueda. Obliga a filtrar (la primera de la búsqueda no es apta) y es única
        (ninguna otra apta tiene la misma duración), así que no depende del desempate por id."""
        aptas = [x for x in cand if apta(x, dieta)]
        assert aptas and aptas[0] is not cand[0], "la tarea tiene que obligar a filtrar"
        assert len(aptas) == 1 or aptas[0]["minutos"] < aptas[1]["minutos"], [x["id"] for x in aptas[:3]]
        assert not sospechosa(aptas[0]), f"receta {aptas[0]['id']} con líneas sospechosas"
        return aptas[0]

    def probar(nombre, opciones, construir):
        """Usa la primera opción que pasa todas las comprobaciones (si cambian los datos, la tarea se adapta)."""
        for opcion in opciones:
            try:
                return construir(*opcion)
            except AssertionError:
                continue
        raise AssertionError(f"ninguna opción sirve para la tarea «{nombre}»: hay que agregar candidatas")

    def dietas(dieta):
        return {"vegetariana": ("vegetariano", "vegetariana"), "vegana": ("vegano", "vegana"),
                "sin_gluten": ("sin gluten", "sin gluten"), "sin_lactosa": ("sin lactosa", "sin lactosa")}[dieta]

    usadas = set()   # recetas que ya son respuesta de otra tarea: no se repiten

    # --- fáciles: una llamada
    agregar("¿Cuántas recetas del corpus llevan lentejas?", len(buscar(["lenteja"])), "numero", "facil",
            ["buscar_recetas"])

    def mas_rapida(a, b):
        r = unica_mas_rapida(buscar([a, b]))
        assert r["id"] not in usadas
        usadas.add(r["id"])
        agregar(f"¿Cuál es la receta más rápida que lleva {nom(a)} y {nom(b)}?", r["nombre"], "texto", "facil",
                ["buscar_recetas"], nota=f"id {r['id']}, {r['minutos']} min")
    probar("más rápida", [("papa", "huevo"), ("papa", "cebolla"), ("tomate", "cebolla"), ("huevo", "cebolla")],
           mas_rapida)

    r = primera(buscar(["lenteja"]), lambda x: apta(x, "vegana") and not sospechosa(x))
    agregar(f"¿La receta {r['id']} es apta para veganos? Respondé sí o no.", "sí", "texto", "facil", ["es_apta"],
            nota=f"{r['nombre']}: {sorted(ingredientes(r))}")
    r = primera(buscar(["arroz", "pollo"]), lambda x: exacto(x, "arroz") and x["comensales"] in (2, 3, 4) and not sospechosa(x))
    agregar(f"¿Cuántos gramos de arroz lleva la receta {r['id']} si la hago para 6 personas?",
            numero(necesario(r, "arroz", 6)), "numero", "facil", ["detalle_receta"],
            nota=f"{r['nombre']}, {r['comensales']} comensales, línea: {texto_lineas(r, 'arroz')}")
    vence = min(INVENTARIO, key=lambda k: INVENTARIO[k][1])

    def vence_primero(otro):
        r = unica_mas_rapida(buscar([vence, otro]))
        assert r["id"] not in usadas
        usadas.add(r["id"])
        agregar(f"¿Cuál es la receta más rápida que lleva {nom(otro)} y el ingrediente de mi inventario que vence "
                "primero?", r["nombre"], "texto", "facil", ["buscar_recetas"],
                nota=f"vence primero: {vence} (lo marca el harness en el prompt); id {r['id']}")
    probar("vence primero", [("papa",), ("cebolla",), ("tomate",), ("morron",), ("zanahoria",), ("leche",),
                             ("limon",), ("queso",)], vence_primero)

    # --- medias: dos llamadas o más
    CON_DIETA = [("huevo", "pasta", "sin_lactosa"), ("leche", "arroz", "vegetariana"),
                 ("cebolla", "huevo", "sin_lactosa"), ("papa", "harina", "vegetariana"),
                 ("zanahoria", "queso", "vegetariana"), ("tomate", "queso", "vegetariana"),
                 ("huevo", "arroz", "vegetariana"), ("queso", "morron", "vegetariana"),
                 ("leche", "queso", "sin_gluten"), ("pollo", "queso", "sin_gluten")]

    def mas_rapida_con_dieta(a, b, dieta):
        cand = buscar([a, b])
        r = primera_apta(cand, dieta)
        assert r["id"] not in usadas
        usadas.add(r["id"])
        agregar(f"¿Cuál es la receta más rápida que lleva {nom(a)} y {nom(b)} y es {dietas(dieta)[1]}?",
                r["nombre"], "texto", "media", ["buscar_recetas"] + ["es_apta"] * (cand.index(r) + 1),
                nota=f"id {r['id']}; posición {cand.index(r) + 1} en la búsqueda; la primera ({cand[0]['id']} "
                     f"{cand[0]['nombre']}) no es {dietas(dieta)[1]}")
    probar("más rápida con dieta (1)", CON_DIETA, mas_rapida_con_dieta)
    probar("más rápida con dieta (2)", CON_DIETA, mas_rapida_con_dieta)

    def gramos_de_pollo(otro, sin=None):
        r = unica_mas_rapida(buscar(["pollo", otro], [sin] if sin else []))
        assert exacto(r, "pollo"), "el pollo tiene que venir sin conversión"
        porc = 6 if r["comensales"] != 6 else 8
        excl = f" y no lleva {nom(sin)}" if sin else ""
        agregar(f"Para la receta más rápida que lleva pollo y {nom(otro)}{excl}, ¿cuántos gramos de pollo necesito "
                f"para {porc} personas?", numero(necesario(r, "pollo", porc)), "numero", "media",
                ["buscar_recetas", "detalle_receta"],
                nota=f"id {r['id']}, {r['comensales']} comensales, línea: {texto_lineas(r, 'pollo')}")
    probar("gramos de pollo", [("cebolla",), ("tomate",), ("morron", "cebolla"), ("limon", "queso"),
                               ("vino", "cebolla"), ("leche", "queso"), ("limon", "tomate")], gramos_de_pollo)

    def huevos_que_faltan(otro):
        r = unica_mas_rapida(buscar([otro, "huevo"]))
        assert exacto(r, "huevo")
        cant = necesario(r, "huevo", 10)
        assert cant > INVENTARIO["huevo"][0], "tiene que faltar al menos un huevo"
        agregar(f"Si hago para 10 personas la receta más rápida que lleva {nom(otro)} y huevo, ¿cuántos huevos me "
                "faltan con lo que tengo?", numero(cant - INVENTARIO["huevo"][0]), "numero", "media",
                ["buscar_recetas", "faltantes"],
                nota=f"id {r['id']}, {r['comensales']} comensales, línea: {texto_lineas(r, 'huevo')}; "
                     f"necesita {numero(cant)}")
    probar("huevos que faltan", [("papa",), ("cebolla",), ("tomate",), ("leche",), ("harina",), ("queso",)],
           huevos_que_faltan)

    # --- difíciles: buscar, es_apta (dos veces o más) y faltantes
    def que_falta(con, sin, dieta, porciones):
        cand = buscar(con, sin)
        r = primera_apta(cand, dieta)
        assert r["id"] not in usadas
        falta = faltantes(r, porciones)
        assert falta, "tiene que faltar algo"
        usadas.add(r["id"])
        excl = f" que no llevan {' ni '.join(nom(x) for x in sin)}" if sin else ""
        agregar(f"De las recetas con {nom(con[0])} y {nom(con[1])}{excl}, tomá la más rápida que sea "
                f"{dietas(dieta)[1]}: ¿qué me falta comprar para hacerla para {porciones} personas?", falta, "lista",
                "dificil", ["buscar_recetas"] + ["es_apta"] * (cand.index(r) + 1) + ["faltantes"],
                nota=f"id {r['id']} {r['nombre']}; posición {cand.index(r) + 1} en la búsqueda")
    DIFICILES = [(["arroz", "tomate"], [], "vegetariana", 4), (["pollo", "queso"], ["cebolla"], "sin_gluten", 3),
                 (["tomate", "queso"], [], "vegetariana", 4), (["huevo", "arroz"], ["cebolla"], "vegetariana", 4),
                 (["queso", "morron"], ["huevo"], "sin_gluten", 4), (["tomate", "leche"], ["huevo"], "sin_gluten", 4),
                 (["zanahoria", "queso"], ["huevo"], "vegetariana", 4), (["pollo", "queso"], ["huevo"], "sin_gluten", 3)]
    probar("qué falta (1)", DIFICILES, que_falta)
    probar("qué falta (2)", DIFICILES, que_falta)

    def cuantos_faltan(con, sin, dieta, porciones):
        cand = buscar(con, sin)
        r = primera_apta(cand, dieta)
        assert r["id"] not in usadas
        falta = faltantes(r, porciones)
        usadas.add(r["id"])
        agregar(f"No tengo {nom(sin[0])}. De las recetas {dietas(dieta)[1]}s con {nom(con[0])} y {nom(con[1])} "
                f"que no llevan {nom(sin[0])}, tomá la más rápida: ¿cuántos ingredientes me faltan comprar para "
                f"hacerla para {porciones} personas?", len(falta), "numero", "dificil",
                ["buscar_recetas"] + ["es_apta"] * (cand.index(r) + 1) + ["faltantes"],
                nota=f"id {r['id']} {r['nombre']}: faltan {falta}")
    probar("cuántos faltan", [(["papa", "harina"], ["manteca"], "vegetariana", 8),
                              (["huevo", "pasta"], ["manteca"], "vegetariana", 8),
                              (["zanahoria", "queso"], ["manteca"], "vegetariana", 8),
                              (["queso", "morron"], ["manteca"], "vegetariana", 8),
                              (["tomate", "queso"], ["manteca"], "vegetariana", 8)], cuantos_faltan)

    # --- imposibles
    r = buscar(["lenteja"])[0]
    agregar(f"¿Cuántas calorías por porción tiene la receta {r['id']}?", None, "numero", "facil",
            ["detalle_receta"], respondible=False, nota="el corpus no tiene calorías numéricas")
    n = len(buscar(["lenteja", "frutilla", "pescado"]))
    assert n == 0
    agregar("Tengo lentejas, frutillas y pescado y quiero usar los tres: ¿cuál es la receta más rápida que "
            "los lleve?", None, "texto", "media", ["buscar_recetas"], respondible=False,
            nota=f"{n} recetas los llevan a los tres")
    agregar(f"¿Cuánto me cuesta comprar lo que me falta para hacer la receta {r['id']} para 4 personas?", None,
            "numero", "media", ["faltantes"], respondible=False, nota="el corpus no tiene precios")
    return t


def kit(x):
    return {k: x[k] for k in ("id", "pregunta", "respuesta", "tipo", "tolerancia", "dificultad", "respondible")}


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    t = tareas()
    inventario = [{"ingrediente": k, "cantidad": c, "unidad": UNIDAD[k], "vence_en_dias": d}
                  for k, (c, d) in INVENTARIO.items()]
    (RAIZ / "borrador_tareas.json").write_text(json.dumps({"inventario": inventario, "tareas": t},
                                                          ensure_ascii=False, indent=2), encoding="utf-8")
    (TAREAS / "recetas.json").write_text(json.dumps([kit(x) for x in t], ensure_ascii=False, indent=2) + "\n",
                                         encoding="utf-8")
    (TAREAS / "recetas_inventario.json").write_text(json.dumps(inventario, ensure_ascii=False, indent=2) + "\n",
                                                    encoding="utf-8")
    print("inventario:", [(i["ingrediente"], i["cantidad"], i["unidad"]) for i in inventario])
    for x in t:
        print(x["id"], x["dificultad"], repr(x["respuesta"]), "|", x["nota"])
