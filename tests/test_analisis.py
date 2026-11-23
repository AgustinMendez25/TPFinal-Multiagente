"""El análisis de las mediciones: intervalos, test de signo, pass@k, voto y frontera."""
import pytest

from colab import analisis as A


def _fila(tarea, acierto, obtenido="x", respondible=True, tokens=100, resultado=None):
    return {"tarea": tarea, "acierto": acierto, "obtenido": obtenido, "respondible": respondible,
            "resultado": resultado or ("acierto" if acierto else "error_respuesta"), "llamadas_modelo": 2,
            "tokens_entrada": tokens, "tokens_salida": 0, "costo": float(tokens), "tiempo_s": 1.0}


def test_wilson_valores_conocidos():
    bajo, alto = A.wilson(17, 24)
    assert bajo == pytest.approx(0.508, abs=0.002) and alto == pytest.approx(0.851, abs=0.002)
    assert A.wilson(0, 10)[0] == 0.0 and A.wilson(10, 10)[1] == 1.0


@pytest.mark.parametrize("gana, pierde, p", [(2, 10, 0.0386), (6, 0, 0.03125), (5, 0, 0.0625), (7, 1, 0.0703),
                                             (0, 0, 1.0), (3, 3, 1.0)])
def test_test_de_signo_como_en_la_clase(gana, pierde, p):
    assert A.test_signo(gana, pierde) == pytest.approx(p, abs=0.0005)


def test_comparar_cuenta_solo_las_que_cambian():
    a = [_fila("t1", True), _fila("t2", True), _fila("t3", False), _fila("t4", False)]
    b = [_fila("t1", True), _fila("t2", False), _fila("t3", True), _fila("t4", True)]
    c = A.comparar(a, b)
    assert (c["gana"], c["pierde"], c["ambas"], c["ninguna"]) == (2, 1, 1, 0)
    assert c["tareas_gana"] == ["t3", "t4"] and c["tareas_pierde"] == ["t2"]


def test_juntar_semillas_empareja_tarea_y_semilla():
    a = A.juntar_semillas({"s1": [_fila("t1", True)], "s2": [_fila("t1", False)]})
    b = A.juntar_semillas({"s1": [_fila("t1", True)], "s2": [_fila("t1", True)]})
    c = A.comparar(a, b)
    assert c["pares"] == 2 and c["gana"] == 1 and c["tareas_gana"] == ["t1@s2"]


def test_pass_k():
    corridas = [[_fila("t1", True), _fila("t2", True), _fila("t3", False)],
                [_fila("t1", True), _fila("t2", False), _fila("t3", False)],
                [_fila("t1", True), _fila("t2", True), _fila("t3", False)]]
    r = A.pass_k(corridas)
    assert r["pass_at_k"] == pytest.approx(2 / 3) and r["pass_hat_k"] == pytest.approx(1 / 3)
    assert r["por_intento"] == pytest.approx(5 / 9) and r["mezcladas"] == ["t2"]


def test_voto_mayoria_empate_y_costo():
    corridas = [[_fila("t1", False, "5"), _fila("t2", True, "a"), _fila("t3", False, None, resultado="se_nego")],
                [_fila("t1", True, "4"), _fila("t2", False, "b"), _fila("t3", False, None, resultado="se_nego")],
                [_fila("t1", True, "4"), _fila("t2", False, "c"), _fila("t3", True, "x")]]
    votadas = A.por_tarea(A.voto(corridas))
    assert votadas["t1"]["acierto"] and votadas["t1"]["obtenido"] == "4"       # 2 contra 1
    assert votadas["t2"]["obtenido"] == "a"                                   # empate: la primera corrida
    assert votadas["t3"]["obtenido"] is None and not votadas["t3"]["acierto"]  # abstenerse también se vota
    assert votadas["t1"]["tokens_entrada"] == 300 and votadas["t1"]["llamadas_modelo"] == 6


def test_frontera_de_pareto():
    puntos = {"libro": (100, 0.2), "fijo": (500, 0.3), "base": (5000, 0.5), "voto": (15000, 0.5),
              "plan": (8000, 0.7), "caro_y_malo": (20000, 0.4)}
    assert A.frontera(puntos) == ["libro", "fijo", "base", "plan"]


def test_resumen_y_grupos():
    filas = [_fila("rec-001", True), _fila("rec-013", False, None, respondible=False, resultado="invento")]
    r = A.resumen(filas)
    assert (r["aciertos"], r["imposibles"], r["inventos"], r["tokens_por_tarea"]) == (1, 1, 1, 100)
    borrador = [{"id": "rec-001", "en_esquema": True, "usa_vencimiento": False, "respondible": True},
                {"id": "rec-013", "en_esquema": None, "usa_vencimiento": False, "respondible": False}]
    grupos = A.grupos_de(borrador)
    assert grupos["dentro del esquema"] == {"rec-001"} and grupos["imposibles"] == {"rec-013"}
    assert [f["tarea"] for f in A.filtrar(A.juntar_semillas({"s": filas}), {"rec-013"})] == ["rec-013@s"]
