"""La verificación antes de terminar: casos que pasan y casos que la rechazan."""
from harness.verificacion import verificar
from herramientas import recetas as H

RECETA = H.buscar_recetas(["papa", "huevo"])["recetas"][0]          # la más rápida con papa y huevo


def _h(nombre, **argumentos):
    return {"nombre": nombre, "argumentos": argumentos, "datos": H.HERRAMIENTAS[nombre](**argumentos), "ok": True}


def test_sin_herramientas_no_puede_responder():
    assert "sin consultar" in verificar("¿Cuál es la receta más rápida con papa?", "tortilla", [])


def test_negarse_no_pasa_por_aca_pero_una_receta_vista_si_pasa():
    historial = [_h("buscar_recetas", contiene=["papa", "huevo"])]
    assert verificar("¿Cuál es la receta más rápida que lleva papa y huevo?", RECETA["nombre"], historial) is None


def test_receta_inventada_se_rechaza():
    otra = H.buscar_recetas(["lenteja"])["recetas"][0]["nombre"]
    historial = [_h("buscar_recetas", contiene=["papa", "huevo"])]
    assert "no apareció" in verificar("¿Cuál es la más rápida con papa y huevo?", otra, historial)


def test_dieta_pedida_sin_es_apta():
    historial = [_h("buscar_recetas", contiene=["papa", "huevo"])]
    problema = verificar("¿Cuál es la más rápida con papa y huevo y es apta para celíacos?", RECETA["nombre"], historial)
    assert "es_apta" in problema and "sin_gluten" in problema


def test_dieta_comprobada_sobre_la_receta_respondida():
    historial = [_h("buscar_recetas", contiene=["papa", "huevo"]), _h("es_apta", receta_id=RECETA["id"], dieta="sin_gluten")]
    pregunta = "¿Cuál es la más rápida con papa y huevo y es apta para celíacos?"
    esperado = None if historial[1]["datos"]["apta"] else "no es sin_gluten"
    resultado = verificar(pregunta, RECETA["nombre"], historial)
    assert resultado == esperado or (esperado and esperado in resultado)


def test_porciones_pedidas_sin_usarlas():
    historial = [_h("buscar_recetas", contiene=["papa", "huevo"]), _h("faltantes", receta_id=RECETA["id"], porciones=2)]
    problema = verificar("¿Cuántos huevos me faltan para 10 comensales?", "3", historial)
    assert "porciones=10" in problema


def test_numero_grande_inventado_y_numero_chico_permitido():
    historial = [_h("detalle_receta", receta_id=RECETA["id"])]
    assert "350" in verificar(f"¿Cuántas calorías tiene la receta {RECETA['id']}?", "350", historial)
    assert verificar(f"¿Cuántos ingredientes tiene la receta {RECETA['id']}?", "4", historial) is None


def test_lista_con_un_elemento_que_no_aparecio():
    historial = [_h("faltantes", receta_id=RECETA["id"], porciones=4)]
    faltan = historial[0]["datos"]["faltan"]
    pregunta = "¿Qué me falta para 4 personas?"
    assert verificar(pregunta, "; ".join(faltan + ["azafran"]), historial) is not None
    if len(faltan) > 1:
        assert verificar(pregunta, "; ".join(faltan), historial) is None
