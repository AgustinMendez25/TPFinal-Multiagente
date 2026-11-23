"""El loop del agente, probado con un LLM con guion: sin Ollama y sin datos."""
import json
import time

import pytest

import llm
from harness.bucle import RECORDATORIO, Dominio, bucle, validar_argumentos
from herramientas.mundial import FICHAS_POR_NOMBRE, _ficha
from tests.llm_falso import LLMFalso, llamada, texto
from trazas import esquema
from trazas.registro import Registro

CONFIG = {
    "modelo": {"nombre": "qwen3:8b", "num_ctx": 8192, "temperatura": 0, "semilla": 1337, "think": False,
               "num_predict": 800, "timeout_s": 300},
    "frenos": {"max_pasos": 6, "max_tokens": 10000, "reintentos": 2, "espera_reintento_s": 0},
    "contexto": {"tope_resultado_caracteres": 200, "herramienta_timeout_s": 0.5},
}
TERMINAR = FICHAS_POR_NOMBRE["terminar"]


def _dominio():
    def sumar(a, b):
        return {"total": a + b}

    def explota():
        raise ValueError("se rompió")

    def lenta():
        time.sleep(2)
        return {"ok": True}

    def larga():
        return {"texto": "x" * 500}

    def vacia():
        return []

    fichas = [_ficha("sumar", "Suma dos enteros.", {"a": {"type": "integer"}, "b": {"type": "integer"}}, ("a", "b")),
              _ficha("explota", "Falla siempre.", {}), _ficha("lenta", "Tarda.", {}),
              _ficha("larga", "Devuelve mucho texto.", {}), _ficha("vacia", "No encuentra nada.", {}), TERMINAR]
    return Dominio("prueba", "Sistema de prueba.", fichas,
                   {"sumar": sumar, "explota": explota, "lenta": lenta, "larga": larga, "vacia": vacia})


def _correr(tmp_path, guion, config=CONFIG):
    registro = Registro(tmp_path, "t-1")
    registro.evento("corrida_inicio", modelo="qwen3:8b", config=config)
    chat = LLMFalso(guion)
    fin = bucle("¿Cuánto es 2 + 3?", config, registro, _dominio(), chat=chat, dormir=lambda s: None)
    registro.evento("corrida_fin", estado=fin.estado, respuesta=fin.respuesta, pasos=fin.pasos, motivo=fin.motivo)
    assert esquema.validar_archivo(registro.ruta) == []
    eventos = [json.loads(l) for l in registro.ruta.read_text(encoding="utf-8").splitlines()]
    return fin, eventos, chat


def _ultimo_resultado(chat):
    return chat.pedidos[-1]["mensajes"][-1]


def test_responde_con_una_herramienta_y_terminar(tmp_path):
    fin, eventos, chat = _correr(tmp_path, [llamada(("sumar", {"a": 2, "b": 3})),
                                            llamada(("terminar", {"respuesta": "5", "motivo": "sumar dio 5"}))])
    assert (fin.estado, fin.respuesta, fin.pasos) == ("respondida", "5", 2)
    assert fin.motivo == "sumar dio 5"
    assert _ultimo_resultado(chat) == {"role": "tool", "content": '{"total": 5}', "tool_name": "sumar"}
    assert chat.pedidos[0]["num_ctx"] == 8192 and chat.pedidos[0]["temperatura"] == 0
    assert [e["evento"] for e in eventos].count("llamada_modelo") == 2


def test_terminar_con_null_es_negada(tmp_path):
    fin, _, _ = _correr(tmp_path, [llamada(("terminar", {"respuesta": None, "motivo": "no hay datos"}))])
    assert (fin.estado, fin.respuesta) == ("negada", None)


@pytest.mark.parametrize("valor, esperado", [(5, "5"), (2.5, "2.5"), (["a", "b"], "a; b"), ("null", None),
                                             ("  ", None)])
def test_terminar_normaliza_la_respuesta(tmp_path, valor, esperado):
    fin, _, _ = _correr(tmp_path, [llamada(("terminar", {"respuesta": valor, "motivo": "m"}))])
    assert fin.respuesta == esperado


def test_json_roto_vuelve_como_error_y_sigue(tmp_path):
    fin, eventos, chat = _correr(tmp_path, [llamada(("sumar", "{a: 2")),
                                            llamada(("terminar", {"respuesta": "5", "motivo": "m"}))])
    assert fin.estado == "respondida"
    assert "JSON" in _ultimo_resultado(chat)["content"]
    resultado = next(e for e in eventos if e["evento"] == "resultado_herramienta")
    assert resultado["ok"] is False
    assert next(e for e in eventos if e["evento"] == "llamada_herramienta")["argumentos"] == "{a: 2"


def test_json_en_texto_valido_se_acepta(tmp_path):
    fin, _, chat = _correr(tmp_path, [llamada(("sumar", '{"a": 2, "b": 3}')),
                                      llamada(("terminar", {"respuesta": "5", "motivo": "m"}))])
    assert '"total": 5' in _ultimo_resultado(chat)["content"]


def test_herramienta_inexistente(tmp_path):
    _, _, chat = _correr(tmp_path, [llamada(("multiplicar", {"a": 2})),
                                    llamada(("terminar", {"respuesta": None, "motivo": "m"}))])
    contenido = _ultimo_resultado(chat)["content"]
    assert "no existe" in contenido and "sumar" in contenido


def test_argumento_de_tipo_equivocado(tmp_path):
    _, _, chat = _correr(tmp_path, [llamada(("sumar", {"a": "2", "b": 3})),
                                    llamada(("terminar", {"respuesta": None, "motivo": "m"}))])
    assert "«a» tiene que ser integer" in _ultimo_resultado(chat)["content"]


def test_argumento_que_falta_o_sobra(tmp_path):
    _, _, chat = _correr(tmp_path, [llamada(("sumar", {"a": 2, "c": 1})),
                                    llamada(("terminar", {"respuesta": None, "motivo": "m"}))])
    assert "faltan argumentos obligatorios: b" in _ultimo_resultado(chat)["content"]


@pytest.mark.parametrize("nombre, fragmento", [("explota", "la herramienta falló: ValueError"),
                                               ("lenta", "tardó más de 0.5 s"),
                                               ("vacia", "no encontró nada")])
def test_herramientas_que_fallan_o_no_encuentran(tmp_path, nombre, fragmento):
    fin, _, chat = _correr(tmp_path, [llamada((nombre, {})),
                                      llamada(("terminar", {"respuesta": None, "motivo": "m"}))])
    assert fin.estado == "negada"
    assert fragmento in _ultimo_resultado(chat)["content"]


def test_resultado_largo_se_recorta(tmp_path):
    _, eventos, chat = _correr(tmp_path, [llamada(("larga", {})),
                                          llamada(("terminar", {"respuesta": None, "motivo": "m"}))])
    resultado = next(e for e in eventos if e["evento"] == "resultado_herramienta")
    assert resultado["truncado"] is True and resultado["caracteres"] > 200
    assert "recortado" in _ultimo_resultado(chat)["content"]


def test_reintenta_ante_error_del_servidor(tmp_path):
    fin, eventos, _ = _correr(tmp_path, [llm.LLMError("caído"),
                                         llamada(("terminar", {"respuesta": "5", "motivo": "m"}))])
    assert fin.estado == "respondida"
    reintento = next(e for e in eventos if e["evento"] == "reintento_modelo")
    assert reintento["intento"] == 1 and "caído" in reintento["motivo"]


def test_se_rinde_despues_de_los_reintentos(tmp_path):
    fin, eventos, _ = _correr(tmp_path, [llm.LLMError("caído")] * 3)
    assert fin.estado == "error" and "reintentos" in fin.motivo
    assert sum(e["evento"] == "reintento_modelo" for e in eventos) == 2


def test_contexto_desbordado_es_error_sin_reintentar(tmp_path):
    fin, eventos, _ = _correr(tmp_path, [llm.ContextOverflow("no entra")])
    assert fin.estado == "error" and "num_ctx" in fin.motivo
    assert not any(e["evento"] == "reintento_modelo" for e in eventos)


def test_tope_de_pasos(tmp_path):
    fin, _, _ = _correr(tmp_path, [llamada(("sumar", {"a": 1, "b": 1}))] * 6)
    assert (fin.estado, fin.respuesta, fin.pasos) == ("tope_pasos", None, 6)


def test_tope_de_tokens(tmp_path):
    config = {**CONFIG, "frenos": {**CONFIG["frenos"], "max_tokens": 150}}
    fin, _, _ = _correr(tmp_path, [llamada(("sumar", {"a": 1, "b": 1}))] * 2, config)
    assert (fin.estado, fin.pasos) == ("tope_tokens", 2)


def test_respuesta_sin_llamadas_recibe_un_recordatorio(tmp_path):
    fin, eventos, chat = _correr(tmp_path, [texto("Son 5."),
                                            llamada(("terminar", {"respuesta": "5", "motivo": "m"}))])
    assert fin.estado == "respondida"
    assert chat.pedidos[1]["mensajes"][-1] == {"role": "user", "content": RECORDATORIO}
    assert any(e["evento"] == "sin_llamadas" and e["texto"] == "Son 5." for e in eventos)


def test_ids_generados_y_respetados(tmp_path):
    _, eventos, _ = _correr(tmp_path, [llamada(("sumar", {"a": 1, "b": 1}), ("sumar", {"a": 2, "b": 2}),
                                               ("sumar", {"a": 3, "b": 3}, "call_x")),
                                       llamada(("terminar", {"respuesta": "x", "motivo": "m"}))])
    ids = [e["id"] for e in eventos if e["evento"] == "llamada_herramienta"]
    assert ids[:3] == ["p1-1", "p1-2", "call_x"] and len(set(ids)) == len(ids)


def test_validar_argumentos():
    ficha = _ficha("f", "", {"n": {"type": "integer"}, "s": {"type": ["string", "null"]}}, ("n",))
    assert validar_argumentos(ficha, {"n": 1, "s": None}) is None
    assert "tiene que ser integer" in validar_argumentos(ficha, {"n": True})
    assert "no existen" in validar_argumentos(ficha, {"n": 1, "x": 2})
    assert "objeto" in validar_argumentos(ficha, [1])


# --- enganches: plan antes del loop y verificación antes de terminar --------------------------------

def _con_enganches(antes_del_loop=None, antes_de_terminar=None):
    dominio = _dominio()
    dominio.antes_del_loop = antes_del_loop
    dominio.antes_de_terminar = antes_de_terminar
    return dominio


def _correr_con(tmp_path, dominio, guion, config=CONFIG):
    registro = Registro(tmp_path, "t-1")
    registro.evento("corrida_inicio", modelo="qwen3:8b", config=config)
    chat = LLMFalso(guion)
    fin = bucle("¿Cuánto es 2 + 3?", config, registro, dominio, chat=chat, dormir=lambda s: None)
    registro.evento("corrida_fin", estado=fin.estado, respuesta=fin.respuesta, pasos=fin.pasos)
    assert esquema.validar_archivo(registro.ruta) == []
    return fin, [json.loads(l) for l in registro.ruta.read_text(encoding="utf-8").splitlines()], chat


def test_el_plan_entra_antes_del_loop_y_suma_tokens(tmp_path):
    def planificar(pregunta, config, registro, chat):
        return [{"role": "user", "content": "PLAN: sumar y terminar"}], 140
    config = {**CONFIG, "frenos": {**CONFIG["frenos"], "max_tokens": 150}}
    fin, _, chat = _correr_con(tmp_path, _con_enganches(antes_del_loop=planificar),
                               [llamada(("sumar", {"a": 2, "b": 3}))], config)
    assert chat.pedidos[0]["mensajes"][-1]["content"] == "PLAN: sumar y terminar"
    assert fin.estado == "tope_tokens"          # 140 del plan + 120 de la llamada pasan el tope de 150


def test_la_verificacion_rechaza_una_vez_y_el_historial_llega(tmp_path):
    vistos = []

    def verificar(pregunta, respuesta, historial):
        vistos.append([h["nombre"] for h in historial])
        return "no usaste sumar" if not historial else None
    guion = [llamada(("terminar", {"respuesta": "5", "motivo": "m"})), llamada(("sumar", {"a": 2, "b": 3})),
             llamada(("terminar", {"respuesta": "5", "motivo": "m"}))]
    fin, eventos, chat = _correr_con(tmp_path, _con_enganches(antes_de_terminar=verificar), guion)
    assert (fin.estado, fin.respuesta, fin.pasos) == ("respondida", "5", 3)
    assert vistos == [[], ["sumar"]]
    assert "no usaste sumar" in chat.pedidos[1]["mensajes"][-1]["content"]
    assert [e["ok"] for e in eventos if e["evento"] == "verificacion"] == [False, True]


def test_la_verificacion_no_rechaza_mas_de_max_rechazos(tmp_path):
    guion = [llamada(("terminar", {"respuesta": "9", "motivo": "m"}))] * 2
    fin, _, _ = _correr_con(tmp_path, _con_enganches(antes_de_terminar=lambda p, r, h: "mal"), guion)
    assert (fin.estado, fin.respuesta, fin.pasos) == ("respondida", "9", 2)


def test_negarse_no_se_verifica(tmp_path):
    fin, _, _ = _correr_con(tmp_path, _con_enganches(antes_de_terminar=lambda p, r, h: "mal"),
                            [llamada(("terminar", {"respuesta": None, "motivo": "m"}))])
    assert fin.estado == "negada" and fin.pasos == 1


# --- arreglo 1 del Bloque 1: llamadas escritas como texto (mun-007, mun-008, mun-009, mun-012) -----

@pytest.mark.parametrize("contenido, respuesta", [
    ('{"name": "terminar", "arguments": {"respuesta": "United States", "motivo": "m"}}', "United States"),
    ('terminar{"respuesta": "null", "motivo": "No hay datos sobre el Mundial de 2026."}', None),
    ('terminar("8", "del resultado de goles de Ronaldo")', "8"),
    ('terminar(null, "falta el dato")', None),
    ('<tool_call>\n{"name": "terminar", "arguments": {"respuesta": 5, "motivo": "m"}}\n</tool_call>', "5"),
    ('```json\n{"name": "terminar", "arguments": {"respuesta": "5", "motivo": "m"}}\n```', "5"),
    # vistas en dev-010 y dev-011 (recetas): la respuesta entre llaves, como un conjunto de Python
    ('terminar({"cerdo;chorizo;morron;queso"}, "Los ingredientes que faltan son esos")', "cerdo;chorizo;morron;queso"),
    ('terminar({"a", "b"}, "m")', "a; b"),
])
def test_terminar_escrito_como_texto_se_rescata(tmp_path, contenido, respuesta):
    fin, eventos, chat = _correr(tmp_path, [texto(contenido)])
    assert fin.respuesta == respuesta and fin.estado == ("respondida" if respuesta else "negada")
    assert fin.pasos == 1 and len(chat.pedidos) == 1
    assert any(e["evento"] == "llamada_rescatada" for e in eventos)
    assert not any(e["evento"] == "sin_llamadas" for e in eventos)


def test_otra_herramienta_escrita_como_texto_se_ejecuta(tmp_path):
    fin, _, chat = _correr(tmp_path, [texto('sumar({"a": 2, "b": 3})'),
                                      llamada(("terminar", {"respuesta": "5", "motivo": "m"}))])
    assert fin.respuesta == "5"
    assert _ultimo_resultado(chat)["content"] == '{"total": 5}'


@pytest.mark.parametrize("contenido", ["Son 5.", "Podría usar sumar o terminar, no sé.",
                                       '{"name": "multiplicar", "arguments": {}}', "terminar(", ""])
def test_texto_sin_una_llamada_clara_recibe_el_recordatorio(tmp_path, contenido):
    fin, eventos, chat = _correr(tmp_path, [texto(contenido),
                                            llamada(("terminar", {"respuesta": "5", "motivo": "m"}))])
    assert chat.pedidos[1]["mensajes"][-1] == {"role": "user", "content": RECORDATORIO}
    assert not any(e["evento"] == "llamada_rescatada" for e in eventos)


def test_argumentos_rescatados_igual_se_validan(tmp_path):
    _, _, chat = _correr(tmp_path, [texto('sumar("2", 3)'),
                                    llamada(("terminar", {"respuesta": None, "motivo": "m"}))])
    assert "«a» tiene que ser integer" in _ultimo_resultado(chat)["content"]


# --- arreglo 2 del Bloque 1: llamadas repetidas (mun-018, mun-023, mun-027) ------------------------

def test_llamada_repetida_no_se_vuelve_a_ejecutar(tmp_path):
    fin, eventos, chat = _correr(tmp_path, [llamada(("larga", {})), llamada(("larga", {})),
                                            llamada(("terminar", {"respuesta": None, "motivo": "m"}))])
    resultados = [e for e in eventos if e["evento"] == "resultado_herramienta"]
    assert resultados[0]["ok"] and resultados[0]["truncado"]
    assert resultados[1]["ok"] is False and resultados[1]["caracteres"] < 400
    contenido = chat.pedidos[2]["mensajes"][-1]["content"]
    assert "ya hiciste esta misma llamada en el paso 1" in contenido and "recortado" in contenido


def test_otros_argumentos_no_cuentan_como_repeticion(tmp_path):
    _, _, chat = _correr(tmp_path, [llamada(("sumar", {"a": 1, "b": 1})), llamada(("sumar", {"b": 2, "a": 1})),
                                    llamada(("sumar", {"a": 1, "b": 1})),
                                    llamada(("terminar", {"respuesta": "3", "motivo": "m"}))])
    contenidos = [p["mensajes"][-1]["content"] for p in chat.pedidos[1:]]
    assert contenidos[0] == '{"total": 2}' and contenidos[1] == '{"total": 3}'
    assert "ya hiciste esta misma llamada" in contenidos[2] and "recortado" not in contenidos[2]


def test_una_llamada_que_fallo_se_puede_reintentar(tmp_path):
    _, _, chat = _correr(tmp_path, [llamada(("sumar", {"a": "1", "b": 1})), llamada(("sumar", {"a": "1", "b": 1})),
                                    llamada(("terminar", {"respuesta": None, "motivo": "m"}))])
    assert "tiene que ser integer" in chat.pedidos[2]["mensajes"][-1]["content"]
