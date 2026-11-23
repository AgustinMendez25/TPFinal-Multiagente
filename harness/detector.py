"""Detecta en el texto de la pregunta si pide una dieta y para cuántas porciones.

Lo usa la verificación antes de `terminar`: si la pregunta pide una dieta, el agente tiene que haber
pasado por `es_apta`; si pide porciones, por `faltantes` o `detalle_receta` con esas porciones.

Son reglas en código, no el modelo, y se ajustaron solo con las preguntas del conjunto de desarrollo
(dev-*), que usan a propósito otras redacciones que las congeladas. Las expresiones se buscan sobre el
texto en minúsculas y sin tildes.
"""
import re
import unicodedata

# dieta -> expresiones que la piden. Se prueban en este orden: la primera que aparece gana.
DIETAS = [
    ("vegana", [r"\bvegan[oa]s?\b", r"sin nada de origen animal"]),
    ("vegetariana", [r"\bvegetarian[oa]s?\b", r"sin carne ni pescado", r"\bno llev[ae]n? carne ni pescado"]),
    ("sin_gluten", [r"\bsin gluten\b", r"\bceliac[oa]s?\b", r"\bno llev[ae]n? gluten\b"]),
    ("sin_lactosa", [r"\blactosa\b", r"\bsin lacteos\b", r"\bno llev[ae]n? lacteos\b"]),
]
NUMEROS = {"un": 1, "una": 1, "uno": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7,
           "ocho": 8, "nueve": 9, "diez": 10, "once": 11, "doce": 12}
_NUMERO = r"(\d+|" + "|".join(NUMEROS) + r")"
PORCIONES = [re.compile(r"\b" + _NUMERO + r"\s+(?:personas|comensales|porciones)\b"),
             re.compile(r"\bsomos\s+" + _NUMERO + r"\b")]


def _normalizar(texto: str) -> str:
    sin_tildes = "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))
    return " ".join(sin_tildes.casefold().split())


def _numero(texto: str) -> int:
    return int(texto) if texto.isdigit() else NUMEROS[texto]


def detectar(pregunta: str) -> dict:
    texto = _normalizar(pregunta)
    dieta = next((nombre for nombre, patrones in DIETAS if any(re.search(p, texto) for p in patrones)), None)
    porciones = None
    for patron in PORCIONES:
        hallado = patron.search(texto)
        if hallado:
            porciones = _numero(hallado.group(1))
            break
    return {"dieta": dieta, "porciones": porciones}
