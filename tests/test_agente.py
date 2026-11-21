"""agente.py de punta a punta sin servidor: reintenta, cierra la traza con error y no inventa nada."""
import json
import os
import subprocess
import sys
from pathlib import Path

import correr_todas
import evaluar
from tests.ayudas import leer
from trazas import esquema
from trazas.registro import SinRegistro

RAIZ = Path(__file__).resolve().parent.parent


def _config_rapida(tmp_path) -> Path:
    texto = (RAIZ / "config.toml").read_text(encoding="utf-8").replace("espera_reintento_s = 2.0",
                                                                       "espera_reintento_s = 0")
    ruta = tmp_path / "rapida.toml"
    ruta.write_text(texto, encoding="utf-8")
    return ruta


def _correr(*argumentos):
    # Se hereda el entorno (en Windows, sin SYSTEMROOT no arranca SSL) y se apunta a un puerto cerrado.
    return subprocess.run([sys.executable, str(RAIZ / "agente.py"), *argumentos], capture_output=True,
                          text=True, cwd=RAIZ, timeout=60, env=os.environ | {"OLLAMA_HOST": "127.0.0.1:1"})


def test_sin_servidor_reintenta_y_cierra_con_error(tmp_path):
    proceso = _correr("-p", "¿Cuántos?", "--tarea", "mun-001", "--log", str(tmp_path / "c"),
                      "--config", str(_config_rapida(tmp_path)))
    assert proceso.returncode == 0
    ruta = tmp_path / "c" / "mun-001.jsonl"
    assert esquema.validar_archivo(ruta) == []
    eventos = leer(ruta)
    assert [e["evento"] for e in eventos].count("reintento_modelo") == 3
    assert eventos[-1]["estado"] == "error" and eventos[-1]["respuesta"] is None
    assert "reintentos" in eventos[-1]["motivo"]


def test_la_traza_registra_la_configuracion_y_el_dominio(tmp_path):
    _correr("-p", "?", "--tarea", "t", "--log", str(tmp_path / "c"), "--config", str(_config_rapida(tmp_path)))
    inicio = leer(tmp_path / "c" / "t.jsonl")[0]
    assert inicio["modelo"] == "qwen3:8b"
    assert inicio["config"]["modelo"]["num_ctx"] == 8192
    assert inicio["config"]["dominio"] == "mundial"
    assert inicio["config"]["ollama_version"] is None and inicio["config"]["modelo_digest"] is None


def test_sin_log_no_escribe_trazas(tmp_path):
    proceso = _correr("-p", "?", "--config", str(_config_rapida(tmp_path)))
    assert proceso.returncode == 0
    assert [p.name for p in tmp_path.iterdir()] == ["rapida.toml"]


def test_una_config_invalida_falla_antes_de_correr(tmp_path):
    roto = tmp_path / "roto.toml"
    roto.write_text("[modelo]\nnombre = 'qwen3:8b'\n", encoding="utf-8")
    proceso = _correr("-p", "?", "--config", str(roto))
    assert proceso.returncode != 0 and "falta" in proceso.stderr


def test_dominio_desconocido_falla(tmp_path):
    proceso = _correr("-p", "?", "--dominio", "ajedrez")
    assert proceso.returncode != 0 and "ajedrez" in proceso.stderr


def test_correr_todas_y_evaluar_de_punta_a_punta_sin_servidor(tmp_path, monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "127.0.0.1:1")   # correr_tarea hereda el entorno
    tareas = json.loads(evaluar.TAREAS.read_text(encoding="utf-8"))[:2]
    carpeta = tmp_path / "corrida"
    config = _config_rapida(tmp_path)
    for tarea in tareas:
        resultado = correr_todas.correr_tarea(tarea, carpeta, RAIZ / "agente.py", sys.executable, 60, config,
                                              dominio="mundial")
        assert resultado["estado"] == "ok"
    filas, resumen = evaluar.evaluar(tareas, carpeta, evaluar.PESOS)
    assert resumen["aciertos"] == 0
    assert {f["resultado"] for f in filas} == {"sin_respuesta"}


def test_sin_registro_acepta_eventos_y_no_escribe():
    assert SinRegistro().evento("corrida_inicio", modelo="x")["evento"] == "corrida_inicio"
