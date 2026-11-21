"""La traza legible que muestran los notebooks."""
from harness import ver_traza
from trazas.registro import Registro


def _traza(carpeta, respuesta):
    r = Registro(carpeta, "mun-001")
    r.evento("corrida_inicio", modelo="qwen3:8b", config={"modelo": {"num_ctx": 8192}})
    r.evento("llamada_modelo", paso=1, modelo="qwen3:8b", num_ctx=8192, tokens_entrada=900, tokens_salida=40,
             duracion_ms=1200, texto="")
    r.evento("llamada_herramienta", paso=1, id="p1-1", nombre="goleadores", argumentos={"torneo": 1978})
    r.evento("resultado_herramienta", paso=1, id="p1-1", ok=True, truncado=False, caracteres=30, duracion_ms=4,
             contenido='[{"jugador": "Mario Kempes", "goles": 6}]')
    r.evento("corrida_fin", estado="respondida", respuesta=respuesta, pasos=1, motivo="goleadores 1978")
    return r.ruta


def test_resumen_muestra_cada_paso(tmp_path):
    texto = ver_traza.resumen(_traza(tmp_path, "6"))
    assert "modelo · 900 → 40 tokens · 1.2 s" in texto
    assert 'goleadores({"torneo": 1978})' in texto
    assert "Mario Kempes" in texto
    assert "FIN respondida · respuesta: '6' · motivo: goleadores 1978" in texto


def test_comparar_pone_dos_trazas_lado_a_lado(tmp_path):
    texto = ver_traza.comparar(_traza(tmp_path / "a", "5"), _traza(tmp_path / "b", "6"))
    assert "'5'" in texto and "'6'" in texto and " | " in texto
