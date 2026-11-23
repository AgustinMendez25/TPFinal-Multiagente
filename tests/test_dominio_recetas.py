"""El dominio de recetas: prompt con el inventario, variantes por configuración y planificación."""
import json
from pathlib import Path

import config as configuracion
from harness import dominios, planificacion
from harness.bucle import bucle
from tests.llm_falso import LLMFalso, llamada, texto
from trazas import esquema
from trazas.registro import Registro

CONFIGS = Path(__file__).resolve().parent.parent / "configs"


def _config(variante):
    return configuracion.cargar(CONFIGS / f"recetas_{variante}.toml")


def test_el_sistema_muestra_el_inventario_ordenado_y_los_prioritarios():
    sistema = dominios.sistema_recetas()
    assert sistema.index("- pollo") < sistema.index("- tomate") < sistema.index("- lenteja")
    assert sistema.count("PRIORITARIO") == 2


def test_cada_variante_engancha_lo_suyo():
    for variante, (plan, verif) in {"base": (False, False), "plan": (True, False), "verif": (False, True),
                                     "ambas": (True, True)}.items():
        dominio = dominios.construir("recetas", _config(variante))
        assert (dominio.antes_del_loop is not None, dominio.antes_de_terminar is not None) == (plan, verif), variante


def test_planificar_registra_la_llamada_y_el_plan(tmp_path):
    plan = {"buscar": ["papa"], "excluir": [], "dieta": None, "porciones": None, "candidatas": "la primera",
            "criterio": "la más rápida", "pasos": ["buscar"], "cuando_parar": "al encontrarla", "se_puede_responder": True}
    registro = Registro(tmp_path, "t")
    chat = LLMFalso([texto(json.dumps(plan), entrada=300, salida=60)])
    mensajes, tokens = planificacion.planificar("¿La más rápida con papa?", _config("plan"), registro, chat)
    assert tokens == 360 and "la más rápida" in mensajes[0]["content"]
    assert chat.pedidos[0]["formato"] == planificacion.ESQUEMA
    eventos = [json.loads(l) for l in registro.ruta.read_text(encoding="utf-8").splitlines()]
    assert [e["evento"] for e in eventos] == ["llamada_modelo", "plan"] and eventos[1]["plan"] == plan


def test_plan_roto_no_frena_al_agente(tmp_path):
    registro = Registro(tmp_path, "t")
    mensajes, tokens = planificacion.planificar("?", _config("plan"), registro, LLMFalso([texto("no es json")]))
    assert mensajes == [] and tokens == 120


def test_agente_con_ambas_de_punta_a_punta(tmp_path):
    """Plan, búsqueda, un terminar rechazado por la verificación, y la respuesta corregida."""
    config = _config("ambas")
    plan = {"buscar": ["papa", "huevo"], "excluir": [], "dieta": "vegetariana", "porciones": None,
            "candidatas": "en orden hasta la primera apta", "criterio": "la más rápida apta", "pasos": [],
            "cuando_parar": "primera apta", "se_puede_responder": True}
    from herramientas import recetas as H
    candidatas = H.buscar_recetas(["papa", "huevo"])["recetas"]
    apta = next(c for c in candidatas if H.es_apta(c["id"], "vegetariana")["apta"])
    guion = [texto(json.dumps(plan)),
             llamada(("buscar_recetas", {"contiene": ["papa", "huevo"]})),
             llamada(("terminar", {"respuesta": apta["nombre"], "motivo": "la primera"})),      # sin es_apta: rechazo
             llamada(("es_apta", {"receta_id": apta["id"], "dieta": "vegetariana"})),
             llamada(("terminar", {"respuesta": apta["nombre"], "motivo": "apta y la más rápida"}))]
    registro = Registro(tmp_path, "t")
    registro.evento("corrida_inicio", modelo="qwen3:8b", config=config)
    fin = bucle("¿Cuál es la más rápida que lleva papa y huevo y es vegetariana?", config, registro,
                dominios.construir("recetas", config), chat=LLMFalso(guion), dormir=lambda s: None)
    registro.evento("corrida_fin", estado=fin.estado, respuesta=fin.respuesta, pasos=fin.pasos)
    assert esquema.validar_archivo(registro.ruta) == []
    assert (fin.estado, fin.respuesta) == ("respondida", apta["nombre"])
    eventos = [json.loads(l) for l in registro.ruta.read_text(encoding="utf-8").splitlines()]
    assert [e["rechazada"] for e in eventos if e["evento"] == "verificacion"] == [True, False]
