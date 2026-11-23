"""Las herramientas de recetas reproducen, sobre todo el corpus, lo que calcula el generador de respuestas.

El generador (`factibilidad/borrador_respuestas.py`) calcula las respuestas esperadas directo sobre los
datos, sin pasar por las herramientas. Lo único que comparten es la capa de datos (léxico, básicos,
dietas y el CSV normalizado). Si las dos implementaciones coinciden en todas las recetas, las tareas
que se arman encadenando herramientas tienen la respuesta que dice el generador.
"""
import json
import sys
from pathlib import Path

import pytest

from herramientas import recetas as H

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "factibilidad"))
import borrador_respuestas as G  # noqa: E402


def test_buscar_ordena_como_el_generador():
    for con, sin in [(["papa", "huevo"], []), (["pollo"], ["cebolla"]), (["arroz", "tomate"], []),
                     (["lenteja"], []), (["queso", "morron"], ["huevo"])]:
        esperado = G.buscar(con, sin)
        obtenido = H.buscar_recetas(con, sin)
        assert obtenido["total"] == len(esperado)
        assert [r["id"] for r in obtenido["recetas"]] == [r["id"] for r in esperado[:10]]
        assert set(obtenido["recetas"][0]) == {"posicion", "id", "nombre", "minutos", "comensales"}


def test_buscar_acepta_sinonimos_y_plurales():
    assert H.buscar_recetas(["lentejas"])["total"] == H.buscar_recetas(["lenteja"])["total"]
    assert H.buscar_recetas(["patata"])["total"] == H.buscar_recetas(["papa"])["total"]
    assert H.buscar_recetas(["Morrón"])["total"] == H.buscar_recetas(["morron"])["total"]


def test_buscar_con_nombre_desconocido_sugiere():
    resultado = H.buscar_recetas(["pollito"])
    assert "error" in resultado and "pollo" in resultado["error"]


def test_es_apta_coincide_en_todo_el_corpus():
    for r in G.CORPUS:
        for dieta in ("vegetariana", "vegana", "sin_gluten", "sin_lactosa"):
            resultado = H.es_apta(r["id"], dieta)
            assert resultado["apta"] == G.apta(r, dieta), (r["id"], dieta)
            assert bool(resultado["ingredientes_que_lo_impiden"]) == (not resultado["apta"])


def test_detalle_escala_como_el_generador():
    for r in G.CORPUS[::7]:
        detalle = H.detalle_receta(r["id"], 6)
        por_ingrediente = {}
        for i in detalle["ingredientes"]:
            if i["cantidad"] is not None:
                por_ingrediente[i["ingrediente"]] = por_ingrediente.get(i["ingrediente"], 0) + i["cantidad"]
        for ing, cantidad in por_ingrediente.items():
            assert cantidad == pytest.approx(G.necesario(r, ing, 6), abs=0.01), (r["id"], ing)


def test_faltantes_coincide_con_el_generador():
    comparadas = 0
    for r in G.CORPUS[::3]:
        for porciones in (2, 4, 8):
            try:
                esperado = G.faltantes(r, porciones)
            except AssertionError:      # el generador descarta las que dependen de una aproximación
                continue
            assert H.faltantes(r["id"], porciones)["faltan"] == esperado, (r["id"], porciones)
            comparadas += 1
    assert comparadas > 1000


def test_errores_de_argumentos():
    assert "error" in H.detalle_receta(999999)
    assert "error" in H.es_apta(G.CORPUS[0]["id"], "keto")
    assert "error" in H.faltantes(G.CORPUS[0]["id"], 0)


def test_respuestas_de_desarrollo_encadenando_herramientas():
    """Algunas tareas dev-* resueltas con las herramientas, como las encadenaría el agente."""
    tareas = {t["id"]: t for t in json.loads((RAIZ / "factibilidad" / "borrador_tareas.json")
                                              .read_text(encoding="utf-8"))["desarrollo"]}
    # dev-001: conteo
    assert H.buscar_recetas(["espinaca"])["total"] == tareas["dev-001"]["respuesta"]
    # dev-003: aptitud
    receta = tareas["dev-003"]["receta_id"]
    assert ("sí" if H.es_apta(receta, "vegana")["apta"] else "no") == tareas["dev-003"]["respuesta"]
    # dev-012: cuántos faltan
    receta = tareas["dev-012"]["receta_id"]
    assert len(H.faltantes(receta, 8)["faltan"]) == tareas["dev-012"]["respuesta"]
    # dev-016: la que deja menos por comprar entre las candidatas con pollo y maíz, para 2
    candidatas = H.buscar_recetas(["pollo", "maiz"])["recetas"]
    mejor = min(candidatas, key=lambda c: len(H.faltantes(c["id"], 2)["faltan"]))
    assert mejor["nombre"] == tareas["dev-016"]["respuesta"]


def test_inventario_ordenado_por_vencimiento():
    inv = H.inventario()
    assert [i["ingrediente"] for i in inv][:2] == ["pollo", "tomate"]
    assert all(a["vence_en_dias"] <= b["vence_en_dias"] for a, b in zip(inv, inv[1:]))


@pytest.mark.parametrize("nombre, dieta", [("carne", "vegetariana"), ("carnes", "vegetariana"),
                                           ("gluten", "sin_gluten"), ("lácteos", "sin_lactosa"),
                                           ("productos de origen animal", "vegana")])
def test_una_categoria_de_dieta_explica_que_hay_que_usar_es_apta(nombre, dieta):
    """Visto en dev-006 y dev-012: «sin carne ni pescado» se tradujo a excluye=["carne"] y el modelo se rindió."""
    error = H.buscar_recetas(["queso"], [nombre])["error"]
    assert "es_apta" in error and dieta in error


def test_pescado_sigue_siendo_un_ingrediente():
    assert "error" not in H.buscar_recetas(["queso"], ["pescado"])


def test_faltantes_trae_vencimiento_porciones_y_cuenta():
    """Vuelta 2: dev-020 (qué vence primero), dev-017 (para cuántas personas alcanza) y dev-012 (cuántos faltan)."""
    # una receta con huevo (está en la heladera) y con algo que no está en la heladera
    r = next(r for r in G.CORPUS if "huevo" in G.ingredientes(r)
             and G.ingredientes(r) - set(H._inventario()) - G.N.BASICOS)
    datos = H.faltantes(r["id"], 4)
    assert datos["cuantos_faltan"] == len(datos["faltan"])
    for fila in datos["ingredientes"]:
        if fila["ingrediente"] in H._inventario():
            inventario = H._inventario()[fila["ingrediente"]]
            assert fila["vence_en_dias"] == inventario["vence_en_dias"]
            por_porcion = fila["necesita"] / 4
            if por_porcion > 0:
                assert fila["alcanza_para_porciones"] == int(inventario["cantidad"] / por_porcion + 1e-9)
        else:
            assert fila["vence_en_dias"] is None and fila["alcanza_para_porciones"] == 0


def test_alcanza_para_porciones_caso_conocido():
    receta = next(r for r in G.CORPUS if r["comensales"] == 2
                  and [i["cantidad"] for i in G.lineas_de(r, "huevo")] == [1.0])     # 1 huevo para 2 personas
    fila = next(f for f in H.faltantes(receta["id"], 2)["ingredientes"] if f["ingrediente"] == "huevo")
    assert fila["alcanza_para_porciones"] == 12                                    # 6 huevos alcanzan para 12


def test_buscar_numera_las_candidatas():
    recetas = H.buscar_recetas(["papa", "cebolla"])["recetas"]
    assert [r["posicion"] for r in recetas] == list(range(1, len(recetas) + 1))


def test_faltantes_dice_cuanto_falta_comprar_de_cada_ingrediente():
    for receta in list(H._corpus().values())[:200]:
        for fila in H.faltantes(receta["id"], 10)["ingredientes"]:
            assert fila["falta"] == H._redondear(max(0.0, fila["necesita"] - fila["hay"])) or                 abs(fila["falta"] - max(0.0, fila["necesita"] - fila["hay"])) < 0.02
            assert (fila["falta"] == 0) == fila["alcanza"] or fila["hay"] == 0
