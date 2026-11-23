"""Las líneas de base de recetas: el camino fijo (una llamada y un pipeline) y el libro cerrado con inventario."""
import json
from pathlib import Path

import config as configuracion
import evaluar
import libro_cerrado
from harness import dominios
from herramientas import recetas as H
from lineas_de_base import camino_fijo
from tests.llm_falso import LLMFalso, texto
from trazas import esquema

CONFIG = configuracion.cargar(Path(__file__).resolve().parent.parent / "configs" / "recetas_base.toml")


def _correr(tmp_path, campos, tarea_id="dev-x"):
    tarea = {"id": tarea_id, "pregunta": "?", "tipo": "texto"}
    chat = LLMFalso([texto(json.dumps(campos))])
    estado = camino_fijo.responder_tarea(tarea, tmp_path, config=CONFIG, chat=chat)
    ruta = tmp_path / f"{tarea_id}.jsonl"
    assert esquema.validar_archivo(ruta) == []
    fin = [json.loads(l) for l in ruta.read_text(encoding="utf-8").splitlines()][-1]
    return estado, fin["respuesta"], chat


def _campos(**cambios):
    return {"contiene": [], "excluye": [], "dieta": None, "porciones": None, "que_pide": "otro",
            "ingrediente": None, "receta_id": None} | cambios


def test_receta_mas_rapida_con_dieta_recorre_candidatas(tmp_path):
    candidatas = H.buscar_recetas(["papa", "harina"])["recetas"]
    esperada = next(c for c in candidatas if H.es_apta(c["id"], "vegetariana")["apta"])
    _, respuesta, chat = _correr(tmp_path, _campos(contiene=["papa", "harina"], dieta="vegetariana",
                                                   que_pide="receta_mas_rapida"))
    assert respuesta == esperada["nombre"]
    assert chat.pedidos[0]["formato"] == camino_fijo.ESQUEMA


def test_conteo_y_faltan_cuantos(tmp_path):
    _, respuesta, _ = _correr(tmp_path, _campos(contiene=["espinaca"], que_pide="conteo"))
    assert respuesta == str(H.buscar_recetas(["espinaca"])["total"])
    primera = H.buscar_recetas(["huevo", "pan"], ["manteca"])["recetas"][0]
    _, respuesta, _ = _correr(tmp_path, _campos(contiene=["huevo", "pan"], excluye=["manteca"], porciones=8,
                                                que_pide="faltan_cuantos"), "dev-y")
    assert respuesta == str(len(H.faltantes(primera["id"], 8)["faltan"]))


def test_otro_es_null_y_queda_negada(tmp_path):
    estado, respuesta, _ = _correr(tmp_path, _campos(contiene=["pollo"], que_pide="otro"))
    assert (estado, respuesta) == ("negada", None)


def test_evaluar_puntua_el_camino_fijo(tmp_path):
    tareas = [{"id": "dev-z", "pregunta": "?", "tipo": "numero", "tolerancia": 0, "dificultad": "facil",
               "respondible": True, "respuesta": H.buscar_recetas(["espinaca"])["total"]}]
    camino_fijo.responder_tarea(tareas[0], tmp_path, config=CONFIG,
                                chat=LLMFalso([texto(json.dumps(_campos(contiene=["espinaca"], que_pide="conteo")))]))
    _, resumen = evaluar.evaluar(tareas, tmp_path, evaluar.PESOS)
    assert resumen["aciertos"] == 1


def test_libro_cerrado_de_recetas_ve_el_inventario(tmp_path):
    chat = LLMFalso([texto("NO SE")])
    estado = libro_cerrado.responder_tarea({"id": "dev-1", "pregunta": "?", "tipo": "texto"}, tmp_path,
                                           modelo="qwen3:8b", num_ctx=8192, chat=chat,
                                           sistema=dominios.sistema_libro_cerrado_recetas())
    assert estado == "negada"
    assert "pollo: 500 g" in chat.pedidos[0]["mensajes"][0]["content"]
