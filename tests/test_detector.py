"""El detector de dieta y porciones, ajustado solo con las preguntas del conjunto de desarrollo (dev-*).

Las tareas congeladas (rec-*) no se usan acá a propósito: si el detector se ajustara con ellas, quedaría
hecho a su medida. Cuántas detecciones de las congeladas salen bien se mide recién en el análisis.
"""
import json
from pathlib import Path

import pytest

from harness.detector import detectar

DEV = {t["id"]: t["pregunta"] for t in json.loads(
    (Path(__file__).resolve().parent.parent / "tareas" / "recetas_dev.json").read_text(encoding="utf-8"))}

ESPERADO = {  # id -> (dieta, porciones), leído a mano de cada pregunta
    "dev-001": (None, None), "dev-002": (None, None), "dev-003": ("vegana", None), "dev-004": (None, 6),
    "dev-005": (None, None), "dev-006": ("vegetariana", None), "dev-007": ("vegetariana", None),
    "dev-008": (None, 6), "dev-009": (None, 10), "dev-010": ("sin_gluten", 4), "dev-011": ("sin_gluten", 4),
    "dev-012": ("vegetariana", 8), "dev-013": (None, None), "dev-014": (None, None), "dev-015": (None, 2),
    "dev-016": (None, 2), "dev-017": (None, None), "dev-018": (None, 2), "dev-019": (None, None),
    "dev-020": (None, None), "dev-021": (None, 4),
}


def test_cubre_todas_las_de_desarrollo():
    assert set(ESPERADO) == set(DEV)


@pytest.mark.parametrize("tarea", sorted(ESPERADO))
def test_detecta_dieta_y_porciones(tarea):
    dieta, porciones = ESPERADO[tarea]
    assert detectar(DEV[tarea]) == {"dieta": dieta, "porciones": porciones}


@pytest.mark.parametrize("pregunta, esperado", [
    ("Somos 3, ¿qué receta vegana me conviene?", {"dieta": "vegana", "porciones": 3}),
    ("Algo sin lácteos para cuatro personas", {"dieta": "sin_lactosa", "porciones": 4}),
    ("¿Hay algo sin lactosa?", {"dieta": "sin_lactosa", "porciones": None}),
    ("Respondé solo con el número.", {"dieta": None, "porciones": None}),
])
def test_otras_redacciones(pregunta, esperado):
    assert detectar(pregunta) == esperado
