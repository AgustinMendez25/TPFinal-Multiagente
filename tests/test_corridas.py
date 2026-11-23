"""Corridas en Drive: copia atómica, retomar, commit fijado y tandas tomadas."""
import json

import pytest

from harness import corridas
from trazas.registro import Registro

TAREAS = [{"id": "t-1"}, {"id": "t-2"}, {"id": "t-3"}]
MANIFIESTO = {"commit": "aaaa1111", "corrida": "x"}


def _corredor(fallar_en=None, llamadas=None):
    """Un corredor falso que escribe una traza válida (o la deja abierta en `fallar_en`)."""
    def correr(tarea, trabajo):
        if llamadas is not None:
            llamadas.append(tarea["id"])
        registro = Registro(trabajo, tarea["id"])
        registro.evento("corrida_inicio", modelo="qwen3:8b", config={"num_ctx": 8192})
        if tarea["id"] == fallar_en:
            raise KeyboardInterrupt("se cortó la sesión")
        registro.evento("corrida_fin", estado="respondida", respuesta="1", pasos=1)
    return correr


def test_nombre_corrida():
    assert corridas.nombre_corrida("mundial", "agente-antes", 0, 1337) == "mundial__agente-antes__t0__s1337"
    assert corridas.nombre_corrida("congelado", "plan", 0.7, 1338) == "congelado__plan__t0.7__s1338"


def test_corre_todo_y_suelta_la_tanda(tmp_path):
    destino = tmp_path / "drive" / "c"
    resumen = corridas.correr_tanda(TAREAS, destino, tmp_path / "local", _corredor(), manifiesto=MANIFIESTO,
                                    quien="ana", al_avanzar=lambda m: None)
    assert resumen == {"tareas": 3, "en_drive": 3, "corridas_ahora": 3, "completa": True}
    assert sorted(p.name for p in destino.glob("*.jsonl")) == ["t-1.jsonl", "t-2.jsonl", "t-3.jsonl"]
    assert not (destino / "tomada.json").exists()
    assert not list(destino.glob("*.tmp"))
    assert json.loads((destino / "manifiesto.json").read_text(encoding="utf-8"))["commit"] == "aaaa1111"


def test_un_corte_deja_solo_trazas_completas_y_se_retoma(tmp_path):
    destino, local = tmp_path / "drive" / "c", tmp_path / "local"
    with pytest.raises(KeyboardInterrupt):
        corridas.correr_tanda(TAREAS, destino, local, _corredor(fallar_en="t-2"), manifiesto=MANIFIESTO,
                              quien="ana", al_avanzar=lambda m: None)
    assert [p.name for p in destino.glob("*.jsonl")] == ["t-1.jsonl"]
    llamadas = []
    resumen = corridas.correr_tanda(TAREAS, destino, local, _corredor(llamadas=llamadas), manifiesto=MANIFIESTO,
                                    quien="ana", al_avanzar=lambda m: None)
    assert llamadas == ["t-2", "t-3"] and resumen["completa"] and resumen["corridas_ahora"] == 2


def test_una_traza_invalida_en_drive_se_vuelve_a_correr(tmp_path):
    destino = tmp_path / "drive" / "c"
    destino.mkdir(parents=True)
    (destino / "t-1.jsonl").write_text('{"evento": "corrida_inicio"}\n', encoding="utf-8")
    assert not corridas.hecha(destino, "t-1")
    llamadas = []
    corridas.correr_tanda(TAREAS[:1], destino, tmp_path / "local", _corredor(llamadas=llamadas),
                          manifiesto=MANIFIESTO, quien="ana", al_avanzar=lambda m: None)
    assert llamadas == ["t-1"] and corridas.hecha(destino, "t-1")


def test_no_mezcla_commits(tmp_path):
    destino = tmp_path / "c"
    corridas.preparar(destino, MANIFIESTO)
    with pytest.raises(corridas.CommitDistinto, match="aaaa1111"):
        corridas.preparar(destino, {**MANIFIESTO, "commit": "bbbb2222"})



def test_una_tanda_completa_no_mira_el_commit(tmp_path):
    destino = tmp_path / "drive" / "c"
    corridas.correr_tanda(TAREAS, destino, tmp_path / "local", _corredor(), manifiesto=MANIFIESTO, quien="ana",
                          al_avanzar=lambda m: None)
    llamadas = []
    resumen = corridas.correr_tanda(TAREAS, destino, tmp_path / "local", _corredor(llamadas=llamadas),
                                    manifiesto={**MANIFIESTO, "commit": "bbbb2222"}, quien="beto",
                                    al_avanzar=lambda m: None)
    assert resumen == {"tareas": 3, "en_drive": 3, "corridas_ahora": 0, "completa": True}
    assert llamadas == [] and not (destino / "tomada.json").exists()


def test_una_tanda_incompleta_si_mira_el_commit(tmp_path):
    destino = tmp_path / "drive" / "c"
    corridas.correr_tanda(TAREAS[:2], destino, tmp_path / "local", _corredor(), manifiesto=MANIFIESTO, quien="ana",
                          al_avanzar=lambda m: None)
    with pytest.raises(corridas.CommitDistinto):
        corridas.correr_tanda(TAREAS, destino, tmp_path / "local", _corredor(),
                              manifiesto={**MANIFIESTO, "commit": "bbbb2222"}, quien="ana", al_avanzar=lambda m: None)

def test_tanda_tomada_por_otro(tmp_path):
    corridas.tomar(tmp_path, "ana", ahora=1000)
    with pytest.raises(corridas.TandaTomada, match="ana"):
        corridas.tomar(tmp_path, "beto", ahora=1000 + 3600)
    corridas.tomar(tmp_path, "ana", ahora=1000 + 3600)              # la misma persona puede retomar
    corridas.latido(tmp_path, "ana", ahora=5000)
    with pytest.raises(corridas.TandaTomada):
        corridas.tomar(tmp_path, "beto", ahora=5000 + 3600)
    corridas.tomar(tmp_path, "beto", ahora=5000 + 2 * 3600 + 1)     # pasaron 2 horas sin latido: abandonada


def test_estado(tmp_path):
    destino = tmp_path / "c"
    assert corridas.estado(destino, TAREAS)["en_drive"] == 0
    corridas.correr_tanda(TAREAS[:1], destino, tmp_path / "l", _corredor(), manifiesto=MANIFIESTO, quien="ana",
                          al_avanzar=lambda m: None)
    corridas.tomar(destino, "ana", ahora=100)
    info = corridas.estado(destino, TAREAS, ahora=100 + 600)
    assert (info["en_drive"], info["total"], info["tomada_por"], info["hace_min"]) == (1, 3, "ana", 10)


def test_config_con_y_a_toml(tmp_path):
    import tomllib
    base = {"modelo": {"nombre": "qwen3:8b", "temperatura": 0, "semilla": 1337, "think": False},
            "frenos": {"max_pasos": 14, "espera_reintento_s": 2.0}, "contexto": {"tope_resultado_caracteres": 4000}}
    cambiada = corridas.config_con(base, temperatura=0.7, semilla=1338)
    assert base["modelo"]["temperatura"] == 0
    assert tomllib.loads(corridas.a_toml(cambiada)) == cambiada
