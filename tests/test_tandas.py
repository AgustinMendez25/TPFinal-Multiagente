"""Las tandas de recetas: configuración por variante y una tanda de punta a punta con un corredor falso."""
import tomllib

import pytest

from colab import tandas
from harness import corridas


def test_config_de_cada_variante():
    assert tandas.config_de("plan", 0.7, 1338)["agente"]["planificacion"] is True
    config = tandas.config_de("camino-fijo", 0, 1337)
    assert config["modelo"]["temperatura"] == 0 and config["agente"]["verificacion"] is False


def test_el_agente_lee_la_config_de_la_tanda(tmp_path):
    config = tandas.config_de("verif", 0.7, 1339)
    tandas.corredor("verif", config, tmp_path)
    escrita = tomllib.loads((tmp_path / "config_tanda.toml").read_text(encoding="utf-8"))
    assert escrita["modelo"]["semilla"] == 1339 and escrita["agente"]["verificacion"] is True


def test_variante_desconocida(tmp_path):
    with pytest.raises(ValueError, match="variante desconocida"):
        tandas.corredor("magia", {}, tmp_path)


def test_conjuntos():
    assert len(tandas.tareas("dev")) == 21 and tandas.tareas("dev")[0]["id"] == "dev-001"


def test_correr_y_puntuar_con_un_corredor_falso(tmp_path, monkeypatch):
    from trazas.registro import Registro

    def falso(variante, config, trabajo):
        def correr(tarea, carpeta):
            r = Registro(carpeta, tarea["id"])
            r.evento("corrida_inicio", modelo="qwen3:8b", config=config)
            r.evento("corrida_fin", estado="negada", respuesta=None, pasos=0)
        return correr
    monkeypatch.setattr(tandas, "corredor", falso)
    rutas = {"trabajo": tmp_path / "local", "corridas": tmp_path / "drive", "resultados": tmp_path / "res"}
    rutas["resultados"].mkdir()
    destino, resumen = tandas.correr("dev", "base", 0, 1337, quien="ana", rutas=rutas,
                                     manifiesto=lambda n, c, cfg, t: {"commit": "x", "corrida": n})
    assert destino.name == corridas.nombre_corrida("dev", "base", 0, 1337) and resumen["completa"]
    filas, resumen = tandas.puntuar("dev", destino, rutas["resultados"])
    assert resumen["imposibles_negadas"] == 3 and (rutas["resultados"] / f"{destino.name}.csv").exists()


def test_etiqueta_de_las_vueltas_de_desarrollo():
    assert tandas.etiqueta_dev(1) == "dev" and tandas.etiqueta_dev(2) == "dev-v2"
