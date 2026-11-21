"""Borrador del verificador: calcula la respuesta esperada de cada tarea directo sobre el dataset final
(datos/recetas_final.csv), sin pasar por las herramientas del agente.

    python factibilidad/borrador_respuestas.py
    # escribe tareas/recetas.json (congeladas), tareas/recetas_dev.json (desarrollo),
    # tareas/recetas_inventario.json y factibilidad/borrador_tareas.json

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


# ingredientes frecuentes (no básicos), para generar opciones extra del conjunto de desarrollo
_FRECUENCIA = {}
for _r in CORPUS:
    for _i in ingredientes(_r) - N.BASICOS:
        _FRECUENCIA[_i] = _FRECUENCIA.get(_i, 0) + 1
COMUNES = sorted(_FRECUENCIA, key=lambda k: (-_FRECUENCIA[k], k))[:25]
PARES = [(a, b) for i, a in enumerate(COMUNES) for b in COMUNES[i + 1:]]
DIETAS_TAREA = ("vegetariana", "sin_gluten", "sin_lactosa", "vegana")


def primera(lista, condicion=lambda r: True):
    return next((r for r in lista if condicion(r)), None)


def texto_lineas(r, ing):
    return " / ".join(i["texto"] for i in lineas_de(r, ing))


def numero(x):
    x = round(x, 2)
    return int(x) if x == int(x) else x


def tareas(conjunto="congelado", congelado=None):
    """conjunto="congelado": las tareas del informe (rec-NNN). conjunto="desarrollo": las mismas plantillas con
    otras opciones y otras recetas (dev-NNN), para ajustar el harness sin mirar las congeladas. `congelado` son
    las tareas congeladas ya generadas: el conjunto de desarrollo no repite ninguna opción ni receta de ellas."""
    t = []
    dev = conjunto == "desarrollo"
    assert dev == (congelado is not None)
    firmas_prohibidas = {x["firma"] for x in congelado or [] if x.get("firma")}
    recetas_prohibidas = {x["receta_id"] for x in congelado or [] if x.get("receta_id")}
    firma_actual = [None]

    def agregar(pregunta, respuesta, tipo, dificultad, cadena, respondible=True, nota="", en_esquema=True,
                usa_vencimiento=False, receta=None):
        """en_esquema: la resuelve el camino fijo (§6): buscar(contiene, excluye) → la primera candidata apta
        para la dieta → detalle o faltantes con las porciones → un dato. None en las imposibles (el pipeline
        siempre devuelve algo). Se declara acá, antes de medir."""
        assert receta not in recetas_prohibidas, f"receta {receta} ya está en el conjunto congelado"
        t.append({"id": f"{'dev' if dev else 'rec'}-{len(t) + 1:03d}", "pregunta": pregunta, "respuesta": respuesta,
                  "tipo": tipo, "tolerancia": 0, "dificultad": dificultad, "respondible": respondible,
                  "cadena_esperada": cadena, "nota": nota,
                  "en_esquema": en_esquema if respondible else None, "usa_vencimiento": usa_vencimiento,
                  "receta_id": receta, "firma": firma_actual[0]})

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

    def probar(nombre, opciones, construir, extra=()):
        """Usa la primera opción que pasa todas las comprobaciones (si cambian los datos, la tarea se adapta).
        `extra`: más opciones, solo para el conjunto de desarrollo (van después, así no cambian las congeladas)."""
        opciones = list(opciones) + (list(extra) if dev else [])
        base = nombre.split(" (")[0]   # «qué falta (1)» y «qué falta (2)» comparten opciones
        for opcion in opciones:
            firma = f"{base}: {opcion!r}"
            if firma in firmas_prohibidas or any(x["firma"] == firma for x in t):
                continue
            firma_actual[0] = firma
            try:
                return construir(*opcion)
            except AssertionError:
                continue
            finally:
                firma_actual[0] = None
        raise AssertionError(f"ninguna opción sirve para la tarea «{nombre}»: hay que agregar candidatas")

    def dietas(dieta):
        return {"vegetariana": ("vegetariano", "vegetariana"), "vegana": ("vegano", "vegana"),
                "sin_gluten": ("sin gluten", "sin gluten"), "sin_lactosa": ("sin lactosa", "sin lactosa")}[dieta]

    # recetas que ya son respuesta de otra tarea (o del conjunto congelado): no se repiten
    usadas = set(recetas_prohibidas)

    # --- fáciles: una llamada
    contar = "espinaca" if dev else "lenteja"
    agregar(f"¿Cuántas recetas del corpus llevan {nom(contar)}?", len(buscar([contar])), "numero", "facil",
            ["buscar_recetas"])

    def mas_rapida(a, b):
        r = unica_mas_rapida(buscar([a, b]))
        assert r["id"] not in usadas
        usadas.add(r["id"])
        agregar(f"¿Cuál es la receta más rápida que lleva {nom(a)} y {nom(b)}?", r["nombre"], "texto", "facil",
                ["buscar_recetas"], receta=r["id"], nota=f"id {r['id']}, {r['minutos']} min")
    probar("más rápida", [("papa", "huevo"), ("papa", "cebolla"), ("tomate", "cebolla"), ("huevo", "cebolla")],
           mas_rapida, extra=PARES)

    # en desarrollo la respuesta es «no», para no ajustar el harness a un único caso
    r = primera(buscar(["lenteja"]), lambda x: apta(x, "vegana") != dev and not sospechosa(x) and x["id"] not in usadas)
    agregar(f"¿La receta {r['id']} es apta para veganos? Respondé sí o no.", "no" if dev else "sí", "texto", "facil",
            ["es_apta"], receta=r["id"], nota=f"{r['nombre']}: {sorted(ingredientes(r))}")
    r = primera(buscar(["arroz", "pollo"]), lambda x: exacto(x, "arroz") and x["comensales"] in (2, 3, 4)
                and not sospechosa(x) and x["id"] not in usadas)
    agregar(f"¿Cuántos gramos de arroz lleva la receta {r['id']} si la hago para 6 personas?",
            numero(necesario(r, "arroz", 6)), "numero", "facil", ["detalle_receta"],
            receta=r["id"], nota=f"{r['nombre']}, {r['comensales']} comensales, línea: {texto_lineas(r, 'arroz')}")
    vence = min(INVENTARIO, key=lambda k: INVENTARIO[k][1])

    def vence_primero(otro):
        r = unica_mas_rapida(buscar([vence, otro]))
        assert r["id"] not in usadas
        usadas.add(r["id"])
        agregar(f"¿Cuál es la receta más rápida que lleva {nom(otro)} y el ingrediente de mi inventario que vence "
                "primero?", r["nombre"], "texto", "facil", ["buscar_recetas"],
                receta=r["id"], nota=f"vence primero: {vence} (lo marca el harness en el prompt); id {r['id']}",
                usa_vencimiento=True)
    probar("vence primero", [("papa",), ("cebolla",), ("tomate",), ("morron",), ("zanahoria",), ("leche",),
                             ("limon",), ("queso",)], vence_primero,
           extra=[(x,) for x in COMUNES])

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
                receta=r["id"], nota=f"id {r['id']}; posición {cand.index(r) + 1} en la búsqueda; la primera ({cand[0]['id']} "
                     f"{cand[0]['nombre']}) no es {dietas(dieta)[1]}")
    probar("más rápida con dieta (1)", CON_DIETA, mas_rapida_con_dieta,
           extra=[(a, b, d) for a, b in PARES for d in DIETAS_TAREA])
    probar("más rápida con dieta (2)", CON_DIETA, mas_rapida_con_dieta,
           extra=[(a, b, d) for a, b in PARES for d in DIETAS_TAREA])

    def gramos_de_pollo(otro, sin=None):
        r = unica_mas_rapida(buscar(["pollo", otro], [sin] if sin else []))
        assert exacto(r, "pollo"), "el pollo tiene que venir sin conversión"
        porc = 6 if r["comensales"] != 6 else 8
        excl = f" y no lleva {nom(sin)}" if sin else ""
        agregar(f"Para la receta más rápida que lleva pollo y {nom(otro)}{excl}, ¿cuántos gramos de pollo necesito "
                f"para {porc} personas?", numero(necesario(r, "pollo", porc)), "numero", "media",
                ["buscar_recetas", "detalle_receta"],
                receta=r["id"], nota=f"id {r['id']}, {r['comensales']} comensales, línea: {texto_lineas(r, 'pollo')}")
    probar("gramos de pollo", [("cebolla",), ("tomate",), ("morron", "cebolla"), ("limon", "queso"),
                               ("vino", "cebolla"), ("leche", "queso"), ("limon", "tomate")], gramos_de_pollo,
           extra=[(x,) for x in COMUNES] + [(x, y) for x, y in PARES if 'pollo' not in (x, y)])

    def huevos_que_faltan(otro):
        r = unica_mas_rapida(buscar([otro, "huevo"]))
        assert exacto(r, "huevo")
        cant = necesario(r, "huevo", 10)
        assert cant > INVENTARIO["huevo"][0], "tiene que faltar al menos un huevo"
        agregar(f"Si hago para 10 personas la receta más rápida que lleva {nom(otro)} y huevo, ¿cuántos huevos me "
                "faltan con lo que tengo?", numero(cant - INVENTARIO["huevo"][0]), "numero", "media",
                ["buscar_recetas", "faltantes"],
                receta=r["id"], nota=f"id {r['id']}, {r['comensales']} comensales, línea: {texto_lineas(r, 'huevo')}; "
                     f"necesita {numero(cant)}")
    probar("huevos que faltan", [("papa",), ("cebolla",), ("tomate",), ("leche",), ("harina",), ("queso",)],
           huevos_que_faltan, extra=[(x,) for x in COMUNES])

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
                receta=r["id"], nota=f"id {r['id']} {r['nombre']}; posición {cand.index(r) + 1} en la búsqueda")
    DIFICILES = [(["arroz", "tomate"], [], "vegetariana", 4), (["pollo", "queso"], ["cebolla"], "sin_gluten", 3),
                 (["tomate", "queso"], [], "vegetariana", 4), (["huevo", "arroz"], ["cebolla"], "vegetariana", 4),
                 (["queso", "morron"], ["huevo"], "sin_gluten", 4), (["tomate", "leche"], ["huevo"], "sin_gluten", 4),
                 (["zanahoria", "queso"], ["huevo"], "vegetariana", 4), (["pollo", "queso"], ["huevo"], "sin_gluten", 3)]
    probar("qué falta (1)", DIFICILES, que_falta,
           extra=[([a, b], [], d, p) for a, b in PARES for d in DIETAS_TAREA for p in (4, 3)])
    probar("qué falta (2)", DIFICILES, que_falta,
           extra=[([a, b], [], d, p) for a, b in PARES for d in DIETAS_TAREA for p in (4, 3)])

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
                receta=r["id"], nota=f"id {r['id']} {r['nombre']}: faltan {falta}")
    probar("cuántos faltan", [(["papa", "harina"], ["manteca"], "vegetariana", 8),
                              (["huevo", "pasta"], ["manteca"], "vegetariana", 8),
                              (["zanahoria", "queso"], ["manteca"], "vegetariana", 8),
                              (["queso", "morron"], ["manteca"], "vegetariana", 8),
                              (["tomate", "queso"], ["manteca"], "vegetariana", 8)], cuantos_faltan,
           extra=[([a, b], [s], 'vegetariana', 8) for s in ('manteca', 'cebolla', 'huevo') for a, b in PARES if s not in (a, b)])

    # --- imposibles
    if not dev:
        r = buscar(["lenteja"])[0]
        agregar(f"¿Cuántas calorías por porción tiene la receta {r['id']}?", None, "numero", "facil",
                ["detalle_receta"], respondible=False, receta=r["id"], nota="el corpus no tiene calorías numéricas")
        n = len(buscar(["lenteja", "frutilla", "pescado"]))
        assert n == 0
        agregar("Tengo lentejas, frutillas y pescado y quiero usar los tres: ¿cuál es la receta más rápida que "
                "los lleve?", None, "texto", "media", ["buscar_recetas"], respondible=False,
                nota=f"{n} recetas los llevan a los tres")
        agregar(f"¿Cuánto me cuesta comprar lo que me falta para hacer la receta {r['id']} para 4 personas?", None,
                "numero", "media", ["faltantes"], respondible=False, nota="el corpus no tiene precios")
    else:
        r = primera(buscar(["arroz"]), lambda x: x["id"] not in usadas)
        agregar(f"¿Cuántos gramos de proteína tiene una porción de la receta {r['id']}?", None, "numero", "facil",
                ["detalle_receta"], respondible=False, receta=r["id"], nota="el corpus no tiene datos nutricionales")
        n = len(buscar(["arroz", "frutilla", "cerdo"]))
        assert n == 0
        agregar("Quiero una receta que lleve arroz, frutillas y cerdo a la vez: ¿cuál es la más rápida?", None,
                "texto", "media", ["buscar_recetas"], respondible=False, nota=f"{n} recetas los llevan a los tres")
        agregar(f"¿En qué supermercado me conviene comprar lo que me falta para la receta {r['id']} para 2 personas?",
                None, "texto", "media", ["faltantes"], respondible=False, nota="el corpus no tiene comercios ni precios")

    # --- agregadas tras la devolución de la v2 (van al final para no cambiar los ids rec-001 a rec-015)
    VISIBLES = 10   # buscar_recetas muestra las primeras 10: la respuesta tiene que estar entre ellas

    def robusto(r, porciones):
        """faltantes(r) o None si la conclusión depende de una equivalencia aproximada."""
        try:
            return faltantes(r, porciones)
        except AssertionError:
            return None

    # fuera del esquema: obligan a recorrer y comparar varias candidatas
    def menos_compras(a, b, porciones):
        cand = buscar([a, b])
        assert 3 <= len(cand) <= VISIBLES, f"{len(cand)} candidatas"
        cuentas = [robusto(x, porciones) for x in cand]
        assert None not in cuentas, "alguna candidata depende de una aproximación"
        minimo = min(len(c) for c in cuentas)
        pos = [i for i, c in enumerate(cuentas) if len(c) == minimo]
        assert len(pos) == 1 and pos[0] != 0, f"mínimo en {pos}"
        r = cand[pos[0]]
        assert r["id"] not in usadas and not sospechosa(r)
        usadas.add(r["id"])
        agregar(f"De las recetas con {nom(a)} y {nom(b)}, ¿cuál me deja menos ingredientes por comprar para hacerla "
                f"para {porciones} personas?", r["nombre"], "texto", "dificil",
                ["buscar_recetas"] + ["faltantes"] * len(cand),
                receta=r["id"], nota=f"id {r['id']}; posición {pos[0] + 1} de {len(cand)}; faltan {cuentas[pos[0]]}; "
                     f"cantidad de faltantes por candidata: {[len(c) for c in cuentas]}", en_esquema=False)
    # combinaciones con 3 a 10 recetas (buscar_recetas las muestra todas); con pollo hay pocas
    probar("menos compras", [(a, b, p) for a, b in [("pollo", "vino"), ("pollo", "maiz"), ("arroz", "vino"),
                                                    ("leche", "espinaca"), ("zanahoria", "miel")]
                             for p in (4, 2)], menos_compras,
           extra=[(a, b, p) for a, b in PARES for p in (4, 2)])

    def huevos_alcanzan(otro):
        for r in buscar([otro, "huevo"]):
            if r["id"] in usadas or sospechosa(r) or not exacto(r, "huevo"):
                continue
            maximo = int(INVENTARIO["huevo"][0] * r["comensales"] / necesario(r, "huevo", r["comensales"]) + 1e-9)
            if 2 <= maximo <= 20 and maximo != r["comensales"]:
                usadas.add(r["id"])
                agregar(f"¿Para cuántas personas como máximo me alcanzan los huevos que tengo si hago la receta "
                        f"{r['id']}?", maximo, "numero", "media", ["detalle_receta"],
                        receta=r["id"], nota=f"{r['nombre']}, {r['comensales']} comensales, línea: {texto_lineas(r, 'huevo')}; "
                             f"hay {INVENTARIO['huevo'][0]} huevos", en_esquema=False)
                return
        raise AssertionError("ninguna receta sirve")
    probar("huevos alcanzan", [("harina",), ("leche",), ("papa",), ("cebolla",)], huevos_alcanzan,
           extra=[(x,) for x in COMUNES])

    def sin_comprar(a, b, porciones):
        cand = buscar([a, b])[:VISIBLES]
        for i, x in enumerate(cand):
            f = robusto(x, porciones)
            assert f is not None, f"la candidata {x['id']} depende de una aproximación"
            if not f:
                break
        else:
            raise AssertionError("ninguna visible se hace sin comprar")
        r = cand[i]
        assert i > 0 and r["id"] not in usadas and not sospechosa(r)
        siguientes = [y for y in buscar([a, b])[i + 1:] if robusto(y, porciones) == []]
        assert not siguientes or siguientes[0]["minutos"] > r["minutos"], "empata en duración"
        usadas.add(r["id"])
        agregar(f"De las recetas con {nom(a)} y {nom(b)}, ¿cuál es la más rápida que puedo hacer para {porciones} "
                "personas sin comprar nada?", r["nombre"], "texto", "dificil",
                ["buscar_recetas"] + ["faltantes"] * (i + 1),
                receta=r["id"], nota=f"id {r['id']}; posición {i + 1} en la búsqueda; las anteriores necesitan comprar algo",
                en_esquema=False)
    probar("sin comprar", [(a, b, p) for a, b in [("papa", "huevo"), ("huevo", "cebolla"), ("papa", "cebolla"),
                                                  ("huevo", "harina"), ("huevo", "leche"), ("arroz", "leche"),
                                                  ("tomate", "cebolla"), ("arroz", "cebolla")]
                           for p in (2, 1)], sin_comprar,
           extra=[(a, b, p) for a, b in PARES for p in (2, 1)])

    # vencimientos: priorizar es parte de la respuesta
    prioritarios = sorted((k for k in INVENTARIO if INVENTARIO[k][1] <= 3), key=lambda k: INVENTARIO[k][1])
    assert len(prioritarios) == 2

    def los_que_vencen(extra):
        r = unica_mas_rapida(buscar(prioritarios + list(extra)))
        assert r["id"] not in usadas
        usadas.add(r["id"])
        resto = f", junto con {nom(extra[0])}" if extra else ""
        agregar(f"Quiero usar los dos ingredientes de mi heladera que vencen antes{resto}. ¿Cuál es la receta más "
                f"rápida que {'lleva los tres' if extra else 'los lleva'}?", r["nombre"], "texto", "facil", ["buscar_recetas"],
                receta=r["id"], nota=f"vencen antes: {prioritarios} (lo marca el harness en el prompt); id {r['id']}",
                usa_vencimiento=True)
    # con pollo y tomate solos empatan dos de 15 min: se agrega un tercero que desempate
    probar("los que vencen", [((),), (("pasta",),), (("caldo",),)], los_que_vencen,
           extra=[((x,),) for x in COMUNES])

    def vence_primero_de_receta(a, b):
        r = unica_mas_rapida(buscar([a, b]))
        assert r["id"] not in usadas
        tengo = sorted(ingredientes(r) & INVENTARIO.keys(), key=lambda k: INVENTARIO[k][1])
        assert len(tengo) >= 3, "tiene que haber para elegir"
        assert INVENTARIO[tengo[0]][1] < INVENTARIO[tengo[1]][1], "empate en vencimiento"
        assert tengo[0] not in (a, b), "la respuesta no puede estar en la pregunta"
        usadas.add(r["id"])
        agregar(f"Para la receta más rápida que lleva {nom(a)} y {nom(b)}: de los ingredientes que usa y tengo en la "
                "heladera, ¿cuál vence primero?", tengo[0], "texto", "media", ["buscar_recetas", "detalle_receta"],
                receta=r["id"], nota=f"id {r['id']} {r['nombre']}; del inventario usa {[(k, INVENTARIO[k][1]) for k in tengo]}",
                en_esquema=False, usa_vencimiento=True)
    probar("vence primero de la receta", [("lenteja", "zanahoria"), ("huevo", "lenteja"), ("zanahoria", "morron"),
                                          ("harina", "lenteja"), ("papa", "arroz"), ("arroz", "harina")],
           vence_primero_de_receta, extra=PARES)

    def pollo_alcanza(otro, porciones):
        """Cuenta en vez de pedir «la más rápida»: entre las recetas con pollo hay muchos empates en duración."""
        cand = buscar(["pollo", otro])
        assert 3 <= len(cand) <= VISIBLES, f"{len(cand)} candidatas"
        hay = INVENTARIO["pollo"][0]

        def alcanza(x):
            nec = necesario(x, "pollo", porciones)
            if not exacto(x, "pollo"):
                assert (nec * 0.7 <= hay) == (nec * 1.3 <= hay), f"{x['id']}: depende de la aproximación"
            return nec <= hay + 1e-9
        si = [x for x in cand if alcanza(x)]
        assert 0 < len(si) < len(cand), "tiene que haber de las dos"
        agregar(f"El pollo me vence en {INVENTARIO['pollo'][1]} días y no quiero comprar más. De las recetas con "
                f"pollo y {nom(otro)}, ¿cuántas puedo hacer para {porciones} personas con el pollo que tengo?",
                len(si), "numero", "dificil", ["buscar_recetas"] + ["faltantes"] * len(cand),
                nota=f"{len(cand)} candidatas; alcanzan {[x['id'] for x in si]}; gramos de pollo por candidata: "
                     f"{[numero(necesario(x, 'pollo', porciones)) for x in cand]} (hay {hay})",
                en_esquema=False)   # el vencimiento está en la pregunta: no hace falta priorizar
    probar("pollo alcanza", [(o, p) for o in ("zanahoria", "arroz", "caldo", "leche", "crema de leche", "palta",
                                              "huevo", "pasta", "morron") for p in (4, 6, 8)], pollo_alcanza,
           extra=[(o, p) for o in COMUNES for p in (4, 6, 8)])
    return reformular(t) if dev else t


# --- otras formas de pedir lo mismo (solo en el conjunto de desarrollo)
# Las congeladas dicen siempre «para N personas» y «es vegetariana / sin gluten / sin lactosa». Si el detector del
# harness se ajustara solo con esas redacciones, quedaría hecho a la medida de ellas. Las de desarrollo rotan
# redacciones equivalentes: la respuesta esperada no cambia porque solo cambia la forma de la pregunta.
EN_LETRAS = {2: "dos", 3: "tres", 4: "cuatro", 5: "cinco", 6: "seis", 7: "siete", 8: "ocho", 9: "nueve", 10: "diez"}
PORCIONES = [lambda n: f"para {n} comensales", lambda n: f"para {n} porciones",
             lambda n: f"para {EN_LETRAS.get(n, n)} personas", lambda n: f"para {n} personas"]
DIETA = [  # (forma congelada, alternativas)
    ("y es vegetariana", ["y no lleva carne ni pescado", "y es apta para vegetarianos"]),
    ("y es sin lactosa", ["y no lleva lácteos", "y es apta para intolerantes a la lactosa"]),
    ("y es sin gluten", ["y es apta para celíacos", "y no lleva gluten"]),
    ("que sea vegetariana", ["que no lleve carne ni pescado", "que sea apta para vegetarianos"]),
    ("que sea sin lactosa", ["que no lleve lácteos", "que sea apta para intolerantes a la lactosa"]),
    ("que sea sin gluten", ["que sea apta para celíacos", "que no lleve gluten"]),
    ("De las recetas vegetarianas con", ["De las recetas sin carne ni pescado con", "De las recetas aptas para vegetarianos con"]),
]


def reformular(t):
    import re
    k = {"porciones": 0, "dieta": 0}

    def porciones(m):
        k["porciones"] += 1
        return PORCIONES[(k["porciones"] - 1) % len(PORCIONES)](int(m.group(1)))
    for x in t:
        x["pregunta"] = re.sub(r"para (\d+) personas", porciones, x["pregunta"])
        for forma, alternativas in DIETA:
            if forma in x["pregunta"]:
                x["pregunta"] = x["pregunta"].replace(forma, alternativas[k["dieta"] % len(alternativas)])
                k["dieta"] += 1
    return t


def kit(x):
    return {k: x[k] for k in ("id", "pregunta", "respuesta", "tipo", "tolerancia", "dificultad", "respondible")}


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    t = tareas()
    d = tareas("desarrollo", congelado=t)
    preguntas = {x["pregunta"] for x in t}
    assert not any(x["pregunta"] in preguntas for x in d)
    assert not {x["receta_id"] for x in t if x["receta_id"]} & {x["receta_id"] for x in d if x["receta_id"]}
    inventario = [{"ingrediente": k, "cantidad": c, "unidad": UNIDAD[k], "vence_en_dias": d}
                  for k, (c, d) in INVENTARIO.items()]
    (RAIZ / "borrador_tareas.json").write_text(json.dumps({"inventario": inventario, "tareas": t, "desarrollo": d},
                                                          ensure_ascii=False, indent=2), encoding="utf-8")
    (TAREAS / "recetas.json").write_text(json.dumps([kit(x) for x in t], ensure_ascii=False, indent=2) + "\n",
                                         encoding="utf-8")
    (TAREAS / "recetas_dev.json").write_text(json.dumps([kit(x) for x in d], ensure_ascii=False, indent=2) + "\n",
                                             encoding="utf-8")
    (TAREAS / "recetas_inventario.json").write_text(json.dumps(inventario, ensure_ascii=False, indent=2) + "\n",
                                                    encoding="utf-8")
    print("inventario:", [(i["ingrediente"], i["cantidad"], i["unidad"]) for i in inventario])
    for x in t + d:
        print(x["id"], x["dificultad"], repr(x["respuesta"]), "|", x["nota"])
