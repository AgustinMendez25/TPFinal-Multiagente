"""Borrador del normalizador: de una línea de texto libre a (ingrediente canónico, cantidad, unidad).

Es la capa de datos que comparten las herramientas y el verificador de respuestas. Es un borrador para
la propuesta: mide cobertura y permite calcular las respuestas esperadas de las tareas.

    python factibilidad/normalizar.py      # imprime la cobertura sobre el corpus de trabajo
"""
import ast
import csv
import re
import unicodedata
from fractions import Fraction
from functools import lru_cache
from pathlib import Path

CSV = Path(__file__).resolve().parent.parent / "datos" / "recetas" / "main.csv"

# canónico -> (formas que lo nombran, etiquetas para dietas). Las formas de varias palabras ganan.
LEXICO = {
    # proteínas animales
    "pollo": (["pollo", "pechuga de pollo", "pechugas de pollo", "muslo de pollo", "muslos de pollo",
               "contramuslo", "alitas de pollo", "gallina"], {"carne"}),
    "carne vacuna": (["carne de res", "carne de vaca", "carne picada", "carne molida", "ternera", "res",
                      "lomo de res", "solomillo de ternera", "bife", "falda"], {"carne"}),
    "cerdo": (["cerdo", "lomo de cerdo", "solomillo de cerdo", "costilla de cerdo", "costillas de cerdo",
               "chuleta de cerdo", "panceta", "tocino", "bacon", "beicon"], {"carne"}),
    "jamon": (["jamon", "jamon serrano", "jamon cocido", "jamon york"], {"carne"}),
    "chorizo": (["chorizo", "salchicha", "salchichas", "morcilla"], {"carne"}),
    "pescado": (["pescado", "merluza", "salmon", "atun", "bacalao", "dorada", "lubina", "sardina",
                 "sardinas", "caballa", "trucha", "corvina", "tilapia"], {"pescado"}),
    "mariscos": (["camaron", "camarones", "langostino", "langostinos", "gamba", "gambas", "mejillon",
                  "mejillones", "calamar", "calamares", "pulpo", "almeja", "almejas"], {"pescado"}),
    "huevo": (["huevo", "huevos", "yema", "yemas", "clara", "claras"], {"huevo"}),
    # lácteos
    "leche": (["leche", "leche entera", "leche desnatada"], {"lacteo"}),
    # leches especiales: no son leche (decisión D19); la de coco no es lácteo
    "leche condensada": (["leche condensada", "leche condensada azucarada"], {"lacteo"}),
    "leche evaporada": (["leche evaporada", "leche ideal"], {"lacteo"}),
    "leche de coco": (["leche de coco", "crema de coco"], set()),
    "manteca": (["mantequilla", "manteca"], {"lacteo"}),
    "queso": (["queso", "queso rallado", "queso parmesano", "queso crema", "mozzarella", "requeson"], {"lacteo"}),
    "crema de leche": (["nata", "crema de leche", "nata liquida", "crema para batir", "crema"], {"lacteo"}),
    "yogur": (["yogur", "yogurt"], {"lacteo"}),
    # harinas y cereales
    "harina": (["harina", "harina de trigo", "harina comun", "harina leudante"], {"gluten"}),
    "pan": (["pan", "pan rallado", "pan de molde", "miga de pan"], {"gluten"}),
    "pasta": (["pasta", "espagueti", "espaguetis", "macarrones", "fideos", "tallarines", "lasana"], {"gluten"}),
    "arroz": (["arroz", "arroz blanco", "arroz integral"], set()),
    "avena": (["avena", "copos de avena"], set()),
    "maiz": (["maiz", "choclo", "elote", "harina de maiz", "maicena"], set()),
    # las tortillas no son maíz ni harina sueltos (decisión D19)
    "tortilla de maiz": (["tortilla de maiz", "tortillas de maiz"], set()),
    "tortilla de harina": (["tortilla de harina", "tortillas de harina", "tortilla de trigo",
                            "tortillas de trigo"], {"gluten"}),
    # legumbres
    "lenteja": (["lenteja", "lentejas"], set()),
    "garbanzo": (["garbanzo", "garbanzos"], set()),
    "poroto": (["poroto", "porotos", "frijol", "frijoles", "alubia", "alubias", "judias blancas"], set()),
    "arveja": (["arveja", "arvejas", "guisante", "guisantes", "chicharo", "chicharos", "alverjas"], set()),
    # verduras
    "papa": (["papa", "papas", "patata", "patatas"], set()),
    "batata": (["batata", "boniato", "camote"], set()),
    "cebolla": (["cebolla", "cebollas", "cebolla morada", "cebolleta"], set()),
    # la de verdeo es otro ingrediente: viene en ramas y no en unidades
    "cebolla de verdeo": (["cebolla de verdeo", "cebollas de verdeo", "cebolla larga", "cebolla verde",
                           "cebollin", "cebollino", "cebolla de rama"], set()),
    "ajo": (["ajo", "ajos", "diente de ajo", "dientes de ajo", "pasta de ajo"], set()),   # "pasta de ajo" no es pasta
    "tomate": (["tomate", "tomates", "jitomate", "jitomates", "tomate cherry"], set()),
    "salsa de tomate": (["salsa de tomate", "tomate frito", "pure de tomate", "pasta de tomate",
                         "tomate triturado", "concentrado de tomate"], set()),
    "zanahoria": (["zanahoria", "zanahorias"], set()),
    "morron": (["pimiento", "pimientos", "morron", "pimiento rojo", "pimiento verde", "aji morron"], set()),
    "zapallo": (["zapallo", "calabaza", "zapallito", "calabacin", "calabacines"], set()),
    "berenjena": (["berenjena", "berenjenas"], set()),
    "espinaca": (["espinaca", "espinacas", "acelga", "acelgas"], set()),
    "lechuga": (["lechuga"], set()),
    "champinon": (["champinon", "champinones", "hongos", "setas", "seta"], set()),
    "brocoli": (["brocoli", "coliflor"], set()),
    "puerro": (["puerro", "puerros"], set()),
    "apio": (["apio"], set()),
    "palta": (["palta", "aguacate"], set()),
    "aji": (["aji", "chile", "chiles", "guindilla", "jalapeno", "pasta de aji"], set()),
    # frutas
    "limon": (["limon", "limones", "lima"], set()),
    "manzana": (["manzana", "manzanas"], set()),
    "banana": (["banana", "bananas", "platano", "platanos"], set()),
    "naranja": (["naranja", "naranjas"], set()),
    "frutilla": (["frutilla", "frutillas", "fresa", "fresas"], set()),
    # despensa
    "azucar": (["azucar", "azucar glas", "azucar moreno", "azucar morena"], set()),
    "chocolate": (["chocolate", "cacao"], {"lacteo_posible"}),
    "levadura": (["levadura", "polvo de hornear", "polvo para hornear", "royal"], set()),
    "caldo": (["caldo", "caldo de pollo", "caldo de verduras", "caldo de carne", "caldo de pescado",
               "cubito", "pastilla de caldo", "consome", "consome de pollo", "consome de carne"], set()),
    "vino": (["vino", "vino blanco", "vino tinto"], set()),
    "mayonesa": (["mayonesa"], {"huevo"}),
    "miel": (["miel"], set()),
    "aceituna": (["aceituna", "aceitunas"], set()),
    "nuez": (["nuez", "nueces", "almendra", "almendras", "mani", "cacahuete", "avellanas"], set()),
    "perejil": (["perejil", "cilantro", "albahaca"], set()),
    # básicos: se suponen siempre disponibles y no cuentan como faltantes
    "sal": (["sal", "sal gruesa", "sal fina"], set()),
    "pimienta": (["pimienta", "pimienta negra", "pimienta blanca"], set()),
    "aceite": (["aceite", "aceite de oliva", "aceite vegetal", "aceite de girasol", "aove"], set()),
    "agua": (["agua"], set()),
    "condimento": (["laurel", "vainilla", "esencia de vainilla", "oregano", "canela", "comino", "tomillo",
                    "pimenton", "curcuma", "clavo", "clavos de olor", "nuez moscada", "romero", "vinagre",
                    "bicarbonato", "mostaza", "salsa de soja", "salsa de soya", "salsa inglesa", "especias",
                    "jengibre", "colorante", "azafran", "hierbabuena", "menta", "eneldo", "paprika"], set()),
    "pepino": (["pepino", "pepinos"], set()),
}
# perejil/cilantro/albahaca se tratan como condimento: vienen en pizcas, ramas y puñados (decisión D05)
BASICOS = {"sal", "pimienta", "aceite", "agua", "condimento", "perejil"}
# dieta -> etiquetas que la violan
DIETAS = {"vegetariana": {"carne", "pescado"}, "vegana": {"carne", "pescado", "huevo", "lacteo"},
          "sin_gluten": {"gluten"}, "sin_lactosa": {"lacteo"}}

# unidades exactas del sistema métrico: se pasan a g o ml sin aproximar
METRICAS = {"g": ("g", 1), "gr": ("g", 1), "grs": ("g", 1), "gramo": ("g", 1), "gramos": ("g", 1),
            "kg": ("g", 1000), "kilo": ("g", 1000), "kilos": ("g", 1000), "kilogramo": ("g", 1000),
            "kilogramos": ("g", 1000), "ml": ("ml", 1), "cc": ("ml", 1), "mililitro": ("ml", 1),
            "mililitros": ("ml", 1), "cl": ("ml", 10), "dl": ("ml", 100), "l": ("ml", 1000),
            "litro": ("ml", 1000), "litros": ("ml", 1000), "centimetros": ("ml", 1), "centímetros": ("ml", 1)}
# medidas caseras y envases: cada una es su propia unidad (se convierten con datos/normalizacion/equivalencias.csv)
MEDIDAS = {"taza": "taza", "tazas": "taza", "tz": "taza", "cucharada": "cucharada", "cucharadas": "cucharada",
           "cda": "cucharada", "cdas": "cucharada", "cucharadita": "cucharadita", "cucharaditas": "cucharadita",
           "cdta": "cucharadita", "vaso": "vaso", "vasos": "vaso", "vasito": "vaso", "copa": "copa", "copas": "copa",
           "cubilete": "cubilete", "cubiletes": "cubilete", "libra": "libra", "libras": "libra", "onza": "onza",
           "onzas": "onza", "pizca": "pizca", "pizcas": "pizca", "pellizco": "pizca", "pellizcos": "pizca",
           "chorro": "chorro", "chorrito": "chorro", "chorritos": "chorro", "puñado": "puñado", "puñados": "puñado",
           "gota": "gota", "gotas": "gota", "rama": "rama", "ramas": "rama", "ramita": "rama", "ramitas": "rama",
           "hoja": "hoja", "hojas": "hoja", "diente": "diente", "dientes": "diente", "lata": "lata", "latas": "lata",
           "sobre": "sobre", "sobres": "sobre", "rebanada": "rebanada", "rebanadas": "rebanada", "trozo": "trozo",
           "trozos": "trozo", "loncha": "loncha", "lonchas": "loncha", "lámina": "lámina", "láminas": "lámina",
           "paquete": "paquete", "paquetes": "paquete", "manojo": "manojo", "manojos": "manojo",
           "tarrina": "envase", "bote": "envase", "botes": "envase", "tarro": "envase", "botella": "envase",
           "envase": "envase", "pote": "envase", "bolsa": "envase", "cubo": "cubo", "cubos": "cubo",
           "rodaja": "rodaja", "rodajas": "rodaja", "pieza": "pieza", "piezas": "pieza", "filete": "filete",
           "filetes": "filete", "cabeza": "cabeza", "tallo": "tallo", "tallos": "tallo", "tableta": "tableta",
           "vaina": "vaina", "vainas": "vaina", "barra": "barra", "pastilla": "pastilla", "pechuga": "pechuga",
           "pechugas": "pechuga", "muslo": "muslo", "muslos": "muslo"}
FRACCIONES = {"½": Fraction(1, 2), "¼": Fraction(1, 4), "¾": Fraction(3, 4), "⅓": Fraction(1, 3),
              "⅔": Fraction(2, 3)}
_NUM = r"(\d+\s*[½¼¾⅓⅔]|\d+\s+\d+/\d+|\d+/\d+|\d+(?:[.,]\d+)?|[½¼¾⅓⅔])"
CANTIDAD = re.compile(r"^\s*" + _NUM + r"(\s*(?:a|o|-|y)\s*" + _NUM + r")?\s*(?:de\s+)?([^\s(,]+)?")
PARENTESIS = re.compile(r"\(\s*(?:unos\s+|aprox\.?\s+)?(\d+(?:[.,]\d+)?)\s*(g|gr|grs|gramos|ml|cc)\b\.?\s*\)")


def normalizar_texto(texto: str) -> str:
    sin = "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", sin.casefold())


@lru_cache(maxsize=1)
def _formas() -> list[tuple[re.Pattern, str]]:
    pares = [(forma, canonico) for canonico, (formas, _) in LEXICO.items() for forma in formas]
    pares.sort(key=lambda p: -len(p[0]))   # las formas largas primero: "caldo de pollo" antes que "pollo"
    return [(re.compile(r"\b" + re.escape(f) + r"\b"), c) for f, c in pares]


def _numero(texto: str) -> float:
    texto = texto.replace(",", ".").strip()
    for simbolo, valor in FRACCIONES.items():
        if simbolo in texto:
            entero = texto.replace(simbolo, "").strip()
            return float((int(entero) if entero else 0) + valor)
    if " " in texto and "/" in texto:
        entero, frac = texto.split()
        return float(int(entero) + Fraction(frac))
    return float(Fraction(texto)) if "/" in texto else float(texto)


def parsear_linea(linea: str) -> dict:
    """De una línea cruda a {ingrediente, cantidad, unidad, rango, parentesis, texto}.

    `unidad` es "g" o "ml" (ya convertidas desde kg, l, cc…), "unidad" para un conteo ("2 huevos",
    "2 unidades de tomate"), una medida casera o envase ("taza", "pizca", "lata"…), o None si la línea no
    trae número ("Sal"). `rango` marca "2 o 3". `parentesis` es una cantidad métrica que la propia receta
    escribe entre paréntesis ("1 taza de harina (100 gr)"): (valor, "g"|"ml") o None.
    """
    texto = normalizar_texto(linea)
    mejor = None
    for patron, canonico in _formas():
        m = patron.search(texto)
        if m and (mejor is None or m.start() < mejor[0]):
            mejor = (m.start(), canonico)
    cantidad, unidad, rango, parentesis = None, None, False, None
    # la cantidad se lee sin NFKD: NFKD convierte "½" en "1⁄2" y se leería como 1
    crudo = re.sub(r"\s+", " ", linea.casefold())
    m = CANTIDAD.match(crudo)
    if m:
        cantidad = _numero(m.group(1))
        rango = m.group(2) is not None
        palabra = (m.group(4) or "").strip(".,")
        if palabra in METRICAS:
            unidad, factor = METRICAS[palabra]
            cantidad *= factor
        elif palabra in ("unidad", "unidades"):
            unidad = "unidad"
        elif palabra in MEDIDAS:
            unidad = MEDIDAS[palabra]
        else:
            unidad = "unidad"   # "2 huevos", "1 cebolla": la palabra que sigue es el ingrediente
    p = PARENTESIS.search(crudo)
    if p:
        parentesis = (float(p.group(1).replace(",", ".")), "g" if p.group(2) in ("g", "gr", "grs", "gramos") else "ml")
    return {"ingrediente": mejor[1] if mejor else None, "cantidad": cantidad, "unidad": unidad, "rango": rango,
            "parentesis": parentesis, "texto": linea.strip()}


@lru_cache(maxsize=1)
def corpus_trabajo() -> list[dict]:
    """recetasgratis.net, con comensales y duración, y al menos 3 líneas de ingredientes."""
    csv.field_size_limit(10**9)
    recetas = []
    with open(CSV, encoding="utf-8-sig", newline="") as archivo:
        for fila in csv.DictReader(archivo):
            if "recetasgratis.net" not in fila["URL"]:
                continue
            try:
                lineas = [l for l in ast.literal_eval(fila["Ingredientes"]) if l.strip()]
            except (ValueError, SyntaxError):
                continue
            comensales = re.match(r"\d+", fila["Comensales"])
            duracion = re.fullmatch(r"(\d+):(\d+)(?::\d+)?", fila["Duracion"])
            if not comensales or not duracion or len(lineas) < 3:
                continue
            recetas.append({"id": int(fila["Id"]), "nombre": fila["Nombre"].strip(), "url": fila["URL"],
                            "categoria": fila["Categoria"], "comensales": int(comensales.group()),
                            "minutos": int(duracion.group(1)) * 60 + int(duracion.group(2)),
                            "ingredientes": [parsear_linea(l) for l in lineas]})
    return recetas


if __name__ == "__main__":
    import collections
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    recetas = corpus_trabajo()
    lineas = [i for r in recetas for i in r["ingredientes"]]
    c = collections.Counter()
    for i in lineas:
        c["con_ingrediente"] += i["ingrediente"] is not None
        c["con_cantidad"] += i["cantidad"] is not None
        c["unidad_g_ml_o_conteo"] += i["unidad"] in ("g", "ml", "unidad")
    print(f"recetas: {len(recetas)}  líneas: {len(lineas)}")
    for k, v in c.items():
        print(f"  {k}: {v} ({v / len(lineas):.0%})")
    completas = sum(all(i["ingrediente"] for i in r["ingredientes"]) for r in recetas)
    print(f"recetas con todas las líneas reconocidas: {completas} ({completas / len(recetas):.0%})")
    sin_reconocer = collections.Counter(normalizar_texto(re.sub(r"^[\d½¼¾⅓⅔/.,\s]+", "", i["texto"]))[:30]
                                        for i in lineas if i["ingrediente"] is None)
    print("más frecuentes sin reconocer:", sin_reconocer.most_common(25))
