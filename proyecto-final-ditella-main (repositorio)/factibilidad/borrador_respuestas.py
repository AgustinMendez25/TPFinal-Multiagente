"""Borrador del verificador: calcula la respuesta esperada de cada tarea propuesta directo sobre el
corpus normalizado, sin pasar por las herramientas del agente (que todavía no existen).

    python factibilidad/borrador_respuestas.py   # escribe factibilidad/borrador_tareas.json
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import normalizar as N  # noqa: E402

RAIZ = Path(__file__).resolve().parent
# inventario de la sesión: ingrediente canónico -> (cantidad, unidad, días hasta vencer)
INVENTARIO = {"pollo": (500, "g", 2), "tomate": (3, "unidad", 3), "leche": (1000, "ml", 5),
              "zanahoria": (3, "unidad", 6), "cebolla": (2, "unidad", 10), "huevo": (6, "unidad", 12),
              "papa": (1000, "g", 15), "arroz": (1000, "g", 60), "harina": (1000, "g", 90),
              "lenteja": (500, "g", 90)}

CORPUS = [r for r in N.corpus_trabajo() if all(i["ingrediente"] for i in r["ingredientes"])]
POR_ID = {r["id"]: r for r in CORPUS}


def ingredientes(r):
    return {i["ingrediente"] for i in r["ingredientes"]}


def buscar(con, sin=()):
    hallados = [r for r in CORPUS if set(con) <= ingredientes(r) and not set(sin) & ingredientes(r)]
    return sorted(hallados, key=lambda r: (r["minutos"], r["id"]))


def apta(r, dieta):
    return not any(N.LEXICO[c][1] & N.DIETAS[dieta] for c in ingredientes(r))


def necesario(r, ingrediente, porciones):
    """Cantidad total escalada de un ingrediente, o (None, None) si no hay una cantidad comparable."""
    lineas = [i for i in r["ingredientes"] if i["ingrediente"] == ingrediente]
    if not lineas or any(i["cantidad"] is None for i in lineas) or len({i["unidad"] for i in lineas}) != 1:
        return None, None
    return sum(i["cantidad"] for i in lineas) * porciones / r["comensales"], lineas[0]["unidad"]


def faltantes(r, porciones):
    falta = []
    for ing in sorted(ingredientes(r) - N.BASICOS):
        if ing not in INVENTARIO:
            falta.append(ing)
            continue
        cant, unidad = necesario(r, ing, porciones)
        if cant is not None and unidad == INVENTARIO[ing][1] and cant > INVENTARIO[ing][0]:
            falta.append(ing)
    return falta


def primera(lista, condicion=lambda r: True):
    return next((r for r in lista if condicion(r)), None)


def linea(r, ing):
    return " / ".join(i["texto"] for i in r["ingredientes"] if i["ingrediente"] == ing)


def tareas():
    t = []

    def agregar(pregunta, respuesta, tipo, dificultad, cadena, respondible=True, nota=""):
        t.append({"id": f"rec-{len(t) + 1:03d}", "pregunta": pregunta, "respuesta": respuesta, "tipo": tipo,
                  "tolerancia": 0, "dificultad": dificultad, "respondible": respondible,
                  "cadena_esperada": cadena, "nota": nota})

    # --- fáciles: una llamada
    agregar("¿Cuántas recetas del corpus llevan lentejas y arroz?", len(buscar(["lenteja", "arroz"])),
            "numero", "facil", ["buscar_recetas"])
    r = buscar(["papa", "huevo"])[0]
    agregar("¿Cuál es la receta más rápida que lleva papa y huevo?", r["nombre"], "texto", "facil",
            ["buscar_recetas"], nota=f"id {r['id']}, {r['minutos']} min")
    r = POR_ID[3814]
    agregar("¿La receta 3814 es apta para veganos? Respondé sí o no.", "sí" if apta(r, "vegana") else "no",
            "texto", "facil", ["es_apta"], nota=r["nombre"])
    r = POR_ID[3628]
    agregar("¿Cuántos gramos de arroz lleva la receta 3628 si la hago para 6 personas?",
            necesario(r, "arroz", 6)[0], "numero", "facil", ["detalle_receta"],
            nota=f"{r['nombre']}, {r['comensales']} comensales, línea: {linea(r, 'arroz')}")
    vence = min(INVENTARIO, key=lambda k: INVENTARIO[k][2])
    r = buscar([vence, "zanahoria"])[0]
    agregar("¿Cuál es la receta más rápida que lleva zanahoria y el ingrediente de mi inventario que vence primero?",
            r["nombre"], "texto", "facil", ["buscar_recetas"],
            nota=f"vence primero: {vence} (lo marca el harness en el prompt); id {r['id']}")
    # --- medias: dos llamadas o más
    r = primera(buscar(["pollo", "zanahoria"]), lambda x: apta(x, "sin_lactosa"))
    agregar("¿Cuál es la receta más rápida que lleva pollo y zanahoria y es sin lactosa?", r["nombre"], "texto",
            "media", ["buscar_recetas", "es_apta"], nota=f"id {r['id']}")
    r = primera(buscar(["lenteja", "arroz"]), lambda x: apta(x, "vegana"))
    agregar("De las recetas que llevan lentejas y arroz, ¿cuál es la más rápida que sea vegana?", r["nombre"],
            "texto", "media", ["buscar_recetas", "es_apta", "es_apta"], nota=f"id {r['id']}")
    r = buscar(["pollo", "zanahoria"])[0]
    agregar("Para la receta más rápida que lleva pollo y zanahoria, ¿cuántas pechugas de pollo necesito para "
            "6 personas?", necesario(r, "pollo", 6)[0], "numero", "media", ["buscar_recetas", "detalle_receta"],
            nota=f"id {r['id']}, {r['comensales']} comensales, línea: {linea(r, 'pollo')}")
    r = buscar(["papa", "huevo"])[0]
    cant = necesario(r, "huevo", 10)[0]
    agregar("Si hago para 10 personas la receta más rápida que lleva papa y huevo, ¿cuántos huevos me faltan "
            "con lo que tengo?", max(0, cant - INVENTARIO["huevo"][0]) if cant is not None else None, "numero",
            "media", ["buscar_recetas", "faltantes"],
            nota=f"id {r['id']}, {r['comensales']} comensales, línea: {linea(r, 'huevo')}")
    # --- difíciles: tres llamadas o más
    r = primera(buscar(["arroz", "tomate"]), lambda x: apta(x, "vegetariana"))
    agregar("Quiero algo vegetariano con arroz y tomate: tomá la receta vegetariana más rápida que los lleve y "
            "decime qué me falta comprar para 4 personas.", faltantes(r, 4), "lista", "dificil",
            ["buscar_recetas", "es_apta", "faltantes"], nota=f"id {r['id']} {r['nombre']}")
    r = primera(buscar(["pollo", "zanahoria", "cebolla"], ["huevo"]), lambda x: apta(x, "sin_gluten"))
    agregar("De las recetas con pollo, zanahoria y cebolla que no llevan huevo, tomá la más rápida que sea sin "
            "gluten: ¿qué me falta comprar para hacerla para 6 personas?", faltantes(r, 6), "lista", "dificil",
            ["buscar_recetas", "es_apta", "faltantes"], nota=f"id {r['id']} {r['nombre']}")
    r = primera(buscar(["leche", "harina", "huevo"], ["manteca"]), lambda x: apta(x, "vegetariana"))
    agregar("No tengo manteca. De las recetas vegetarianas con leche, harina y huevo que no llevan manteca, "
            "tomá la más rápida: ¿cuántos ingredientes me faltan comprar para hacerla para 8 personas?",
            len(faltantes(r, 8)), "numero", "dificil", ["buscar_recetas", "es_apta", "faltantes"],
            nota=f"id {r['id']} {r['nombre']}: faltan {faltantes(r, 8)}")
    # --- imposibles
    agregar("¿Cuántas calorías por porción tiene la receta 9041?", None, "numero", "facil",
            ["detalle_receta"], respondible=False, nota="el corpus no tiene calorías numéricas")
    n = len(buscar(["lenteja", "frutilla", "pescado"]))
    agregar("Tengo lentejas, frutillas y pescado y quiero usar los tres: ¿cuál es la receta más rápida que "
            "los lleve?", None, "texto", "media", ["buscar_recetas"], respondible=False,
            nota=f"{n} recetas los llevan a los tres")
    agregar("¿Cuánto me cuesta comprar lo que me falta para hacer la receta 9041 para 4 personas?", None,
            "numero", "media", ["faltantes"], respondible=False, nota="el corpus no tiene precios")
    return t


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    t = tareas()
    (RAIZ / "borrador_tareas.json").write_text(json.dumps({"inventario": INVENTARIO, "tareas": t},
                                                          ensure_ascii=False, indent=2), encoding="utf-8")
    for x in t:
        print(x["id"], x["dificultad"], repr(x["respuesta"]), "|", x["nota"])
