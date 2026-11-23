"""Herramientas del dominio de recetas («Rescatá la heladera»), sobre el corpus normalizado.

Cuatro herramientas que hacen una sola cosa cada una (propuesta, §3):
  buscar_recetas  filtra por ingredientes canónicos y ordena por duración;
  detalle_receta  muestra los ingredientes de una receta, escalados a unas porciones;
  es_apta         dice si una receta cumple una dieta y qué ingredientes lo impiden;
  faltantes       compara la receta escalada con el inventario de la sesión.

El inventario es estado de la sesión: sale de `tareas/recetas_inventario.json`, y ninguna herramienta lo
recibe como argumento. La capa de datos (léxico, básicos, dietas) es la de `factibilidad/normalizar.py`,
la misma que usa el generador de respuestas esperadas.

Las funciones devuelven datos o {"error": ...}; no levantan excepciones por argumentos que no existen.
"""
import csv
import difflib
import json
import sys
from functools import lru_cache
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "factibilidad"))
import normalizar as N  # noqa: E402

CORPUS_CSV = RAIZ / "datos" / "recetas_final.csv"
INVENTARIO_JSON = RAIZ / "tareas" / "recetas_inventario.json"
DIETAS = tuple(N.DIETAS)
MAX_RECETAS = 10


# --- datos ---------------------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _corpus() -> dict[int, dict]:
    csv.field_size_limit(10**9)
    with open(CORPUS_CSV, encoding="utf-8", newline="") as archivo:
        return {int(r["id"]): {"id": int(r["id"]), "nombre": r["nombre"], "comensales": int(r["comensales"]),
                               "minutos": int(r["minutos"]), "ingredientes": json.loads(r["ingredientes"])}
                for r in csv.DictReader(archivo)}


@lru_cache(maxsize=1)
def _inventario() -> dict[str, dict]:
    return {i["ingrediente"]: i for i in json.loads(INVENTARIO_JSON.read_text(encoding="utf-8"))}


def inventario() -> list[dict]:
    """El inventario de la sesión, ordenado por vencimiento (lo usa el prompt de sistema)."""
    return sorted(_inventario().values(), key=lambda i: (i["vence_en_dias"], i["ingrediente"]))


def _ingredientes(receta: dict) -> set[str]:
    return {i["ingrediente"] for i in receta["ingredientes"]}


@lru_cache(maxsize=1)
def _nombres() -> dict[str, str]:
    """forma normalizada -> nombre canónico (el canónico, sus sinónimos regionales y sus formas)."""
    nombres = {}
    for canonico, (formas, _) in N.LEXICO.items():
        for forma in [canonico, *formas]:
            nombres.setdefault(N.normalizar_texto(forma).strip(), canonico)
    return nombres


def _canonico(nombre: str) -> str | None:
    texto = N.normalizar_texto(str(nombre)).strip()
    nombres = _nombres()
    for candidato in (texto, texto[:-2] if texto.endswith("es") else None, texto[:-1] if texto.endswith("s") else None):
        if candidato and candidato in nombres:
            return nombres[candidato]
    return None


# Palabras que nombran una categoría de dieta, no un ingrediente. Visto en dev-006 y dev-012: «sin carne ni
# pescado» se tradujo a excluye=["carne"], la sugerencia de nombres parecidos confundió al modelo y se rindió.
CATEGORIAS = {"carne": "vegetariana", "carnes": "vegetariana", "gluten": "sin_gluten", "lacteo": "sin_lactosa",
              "lacteos": "sin_lactosa", "lactosa": "sin_lactosa", "origen animal": "vegana",
              "productos de origen animal": "vegana", "animal": "vegana"}


def _error_categoria(nombre: str) -> dict | None:
    dieta = CATEGORIAS.get(N.normalizar_texto(str(nombre)).strip())
    if dieta is None:
        return None
    return {"error": f"«{nombre}» es una categoría de dieta, no un ingrediente. Buscá sin ella y comprobá cada "
                     f"candidata, en orden, con es_apta(receta_id, \"{dieta}\")."}


def _error_nombre(nombre: str) -> dict:
    categoria = _error_categoria(nombre)
    if categoria is not None:
        return categoria
    parecidos = difflib.get_close_matches(N.normalizar_texto(str(nombre)).strip(), list(_nombres()), n=5, cutoff=0.6)
    sugeridos = sorted({_nombres()[p] for p in parecidos})
    texto = f"«{nombre}» no es un ingrediente del corpus."
    return {"error": texto + (f" ¿Quisiste decir: {', '.join(sugeridos)}?" if sugeridos else
                              " Usá nombres simples en singular, por ejemplo: pollo, papa, queso, lenteja.")}


def _receta(receta_id) -> dict | None:
    try:
        return _corpus().get(int(receta_id))
    except (TypeError, ValueError):
        return None


def _redondear(x: float) -> float:
    x = round(x, 2)
    return int(x) if x == int(x) else x


# --- herramientas --------------------------------------------------------------------------------

def buscar_recetas(contiene: list[str], excluye: list[str] | None = None) -> dict:
    con, sin = [], []
    for destino, nombres in ((con, contiene), (sin, excluye or [])):
        for nombre in nombres:
            canonico = _canonico(nombre)
            if canonico is None:
                return _error_nombre(nombre)
            destino.append(canonico)
    hallados = [r for r in _corpus().values()
                if set(con) <= _ingredientes(r) and not set(sin) & _ingredientes(r)]
    hallados.sort(key=lambda r: (r["minutos"], r["id"]))
    return {"total": len(hallados), "contiene": con, "excluye": sin,
            "recetas": [{"posicion": i, "id": r["id"], "nombre": r["nombre"], "minutos": r["minutos"],
                         "comensales": r["comensales"]} for i, r in enumerate(hallados[:MAX_RECETAS], start=1)],
            "nota": "ordenadas por duración: la posición 1 es la más rápida"
                    + (f"; se muestran las {MAX_RECETAS} más rápidas" if len(hallados) > MAX_RECETAS else "")}


def detalle_receta(receta_id: int, porciones: int | None = None) -> dict:
    receta = _receta(receta_id)
    if receta is None:
        return {"error": f"No existe la receta {receta_id}."}
    if porciones is not None and porciones < 1:
        return {"error": "porciones tiene que ser un entero positivo"}
    factor = (porciones or receta["comensales"]) / receta["comensales"]
    return {"id": receta["id"], "nombre": receta["nombre"], "minutos": receta["minutos"],
            "comensales": receta["comensales"], "porciones": porciones or receta["comensales"],
            "ingredientes": [{"ingrediente": i["ingrediente"],
                              "cantidad": None if i["cantidad"] is None else _redondear(i["cantidad"] * factor),
                              "unidad": i["unidad"] if i["cantidad"] is not None else "básico (se supone disponible)",
                              "linea_original": " ".join(i["texto"].split())}
                             for i in receta["ingredientes"]]}


def es_apta(receta_id: int, dieta: str) -> dict:
    receta = _receta(receta_id)
    if receta is None:
        return {"error": f"No existe la receta {receta_id}."}
    if dieta not in N.DIETAS:
        return {"error": f"Dieta desconocida: {dieta}. Las que hay: {', '.join(DIETAS)}"}
    impiden = sorted(c for c in _ingredientes(receta) if N.LEXICO[c][1] & N.DIETAS[dieta])
    return {"id": receta["id"], "nombre": receta["nombre"], "dieta": dieta, "apta": not impiden,
            "ingredientes_que_lo_impiden": impiden}


def faltantes(receta_id: int, porciones: int) -> dict:
    receta = _receta(receta_id)
    if receta is None:
        return {"error": f"No existe la receta {receta_id}."}
    if porciones < 1:
        return {"error": "porciones tiene que ser un entero positivo"}
    factor = porciones / receta["comensales"]
    necesita: dict[str, float] = {}
    unidades: dict[str, str] = {}
    for i in receta["ingredientes"]:
        if i["ingrediente"] in N.BASICOS or i["cantidad"] is None:
            continue
        necesita[i["ingrediente"]] = necesita.get(i["ingrediente"], 0) + i["cantidad"] * factor
        unidades[i["ingrediente"]] = i["unidad"]
    filas = []
    for ing in sorted(necesita):
        en_heladera = ing in _inventario()          # lo que no está en la heladera falta siempre
        hay = _inventario()[ing]["cantidad"] if en_heladera else 0
        por_porcion = necesita[ing] / porciones
        filas.append({"ingrediente": ing, "necesita": _redondear(necesita[ing]), "hay": hay,
                      "unidad": unidades[ing], "alcanza": en_heladera and necesita[ing] <= hay + 1e-9,
                      "falta": _redondear(max(0.0, necesita[ing] - hay)),   # cuánto hay que comprar de este
                      # lo que la heladera ya sabe: cuándo vence y para cuántas porciones alcanza lo que hay
                      "vence_en_dias": _inventario()[ing]["vence_en_dias"] if en_heladera else None,
                      "alcanza_para_porciones": int(hay / por_porcion + 1e-9) if en_heladera and por_porcion > 0
                      else 0})
    faltan = [f["ingrediente"] for f in filas if not f["alcanza"]]
    return {"id": receta["id"], "nombre": receta["nombre"], "porciones": porciones, "ingredientes": filas,
            "faltan": faltan, "cuantos_faltan": len(faltan),
            "nota": "sal, pimienta, aceite, agua, condimentos y hierbas se suponen disponibles"}


# --- esquemas JSON -------------------------------------------------------------------------------

def _ficha(nombre: str, descripcion: str, propiedades: dict, requeridos: tuple = ()) -> dict:
    return {"type": "function", "function": {
        "name": nombre, "description": descripcion,
        "parameters": {"type": "object", "properties": propiedades, "required": list(requeridos),
                       "additionalProperties": False}}}


_LISTA = {"type": "array", "items": {"type": "string"}}
FICHAS_POR_NOMBRE = {
    "buscar_recetas": _ficha(
        "buscar_recetas",
        "Busca recetas del recetario que llevan todos los ingredientes de `contiene` y ninguno de `excluye`. "
        "Devuelve el total y las 10 más rápidas (id, nombre, minutos, comensales), ordenadas por duración. "
        "Los ingredientes van con nombres simples en singular: pollo, papa, queso, lenteja, morron.",
        {"contiene": {**_LISTA, "description": "Ingredientes que la receta tiene que llevar"},
         "excluye": {**_LISTA, "description": "Ingredientes que la receta no puede llevar"}},
        ("contiene",)),
    "detalle_receta": _ficha(
        "detalle_receta",
        "Devuelve los ingredientes de una receta: nombre canónico, cantidad, unidad y la línea original. Con "
        "`porciones`, escala las cantidades a esas porciones.",
        {"receta_id": {"type": "integer", "description": "id de la receta"},
         "porciones": {"type": "integer", "description": "Para cuántas personas escalar las cantidades"}},
        ("receta_id",)),
    "es_apta": _ficha(
        "es_apta",
        "Dice si una receta cumple una dieta, y qué ingredientes lo impiden.",
        {"receta_id": {"type": "integer", "description": "id de la receta"},
         "dieta": {"type": "string", "enum": list(DIETAS),
                   "description": "vegetariana, vegana, sin_gluten o sin_lactosa"}},
        ("receta_id", "dieta")),
    "faltantes": _ficha(
        "faltantes",
        "Compara la receta, escalada a `porciones`, con el inventario de la heladera. Devuelve, por "
        "ingrediente, cuánto necesita, cuánto hay, cuánto falta comprar (`falta`), si alcanza, cuándo vence y "
        "para cuántas porciones alcanza lo que hay; y la lista de ingredientes que faltan.",
        {"receta_id": {"type": "integer", "description": "id de la receta"},
         "porciones": {"type": "integer", "description": "Para cuántas personas"}},
        ("receta_id", "porciones")),
    "terminar": _ficha(
        "terminar",
        "Terminá acá. `respuesta` es tu respuesta final, o null si los datos no alcanzan para "
        "responder la pregunta. `motivo` explica en una frase de dónde sale la respuesta o qué dato falta.",
        {"respuesta": {"type": ["string", "null"],
                       "description": "La respuesta final, o null si no se puede responder con los datos"},
         "motivo": {"type": "string", "description": "Una frase: de dónde sale la respuesta o qué dato falta"}},
        ("respuesta", "motivo")),
}
FICHAS = list(FICHAS_POR_NOMBRE.values())
HERRAMIENTAS = {"buscar_recetas": buscar_recetas, "detalle_receta": detalle_receta, "es_apta": es_apta,
                "faltantes": faltantes}
