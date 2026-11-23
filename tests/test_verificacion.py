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


def test_un_numero_dentro_de_un_decimal_no_cuenta_como_visto():
    historial = [_h("detalle_receta", receta_id=7105, porciones=1)]      # trae «"cantidad": 0.25»
    assert "0.25" in str(historial[0]["datos"])
    assert "25" in verificar("¿Cuántos gramos de proteína tiene una porción de la receta 7105?", "25", historial)


def test_una_negativa_escrita_como_frase_tiene_que_ser_null():
    historial = [_h("buscar_recetas", contiene=["arroz", "frutilla", "cerdo"])]
    problema = verificar("¿Cuál es la más rápida con arroz, frutillas y cerdo?",
                         "No hay recetas que incluyan arroz, frutilla y cerdo.", historial)
    assert "null" in problema
    assert verificar("¿La receta lleva queso?", "No", [_h("detalle_receta", receta_id=RECETA["id"])]) is None


# --- vuelta 2: «la más rápida» tiene que ser la primera candidata que no quedó descartada ----------

def test_mas_rapida_sin_filtros_tiene_que_ser_la_primera():
    historial = [_h("buscar_recetas", contiene=["papa", "huevo"])]
    candidatas = historial[0]["datos"]["recetas"]
    pregunta = "¿Cuál es la receta más rápida que lleva papa y huevo?"
    problema = verificar(pregunta, candidatas[1]["nombre"], historial)
    assert problema and candidatas[0]["nombre"] in problema
    assert verificar(pregunta, candidatas[0]["nombre"], historial) is None


def test_mas_rapida_con_dieta_acepta_la_primera_apta_si_las_anteriores_se_descartaron():
    historial = [_h("buscar_recetas", contiene=["papa", "harina"])]
    candidatas = historial[0]["datos"]["recetas"]
    primera_apta = next(i for i, c in enumerate(candidatas) if H.es_apta(c["id"], "vegetariana")["apta"])
    assert primera_apta > 0
    pregunta = "¿Cuál es la más rápida con papa y harina que sea apta para vegetarianos?"
    elegida = candidatas[primera_apta]
    solo_la_elegida = historial + [_h("es_apta", receta_id=elegida["id"], dieta="vegetariana")]
    assert candidatas[0]["nombre"] in verificar(pregunta, elegida["nombre"], solo_la_elegida)
    todas = historial + [_h("es_apta", receta_id=c["id"], dieta="vegetariana") for c in candidatas[:primera_apta + 1]]
    assert verificar(pregunta, elegida["nombre"], todas) is None


def test_mas_rapida_sin_comprar_acepta_si_las_anteriores_tienen_faltantes():
    historial = [_h("buscar_recetas", contiene=["huevo", "leche"])]
    candidatas = historial[0]["datos"]["recetas"]
    i = next(i for i, c in enumerate(candidatas) if not H.faltantes(c["id"], 2)["faltan"])
    assert i > 0
    pregunta = "¿Cuál es la más rápida con huevo y leche que puedo hacer para 2 personas sin comprar nada?"
    con_faltantes = historial + [_h("faltantes", receta_id=c["id"], porciones=2) for c in candidatas[:i + 1]]
    assert verificar(pregunta, candidatas[i]["nombre"], con_faltantes) is None
    assert candidatas[0]["nombre"] in verificar(pregunta, candidatas[i]["nombre"], historial + [con_faltantes[-1]])


def test_si_no_pide_la_mas_rapida_no_se_mira_el_orden():
    historial = [_h("buscar_recetas", contiene=["pollo", "maiz"])]
    segunda = historial[0]["datos"]["recetas"][1]
    historial += [_h("faltantes", receta_id=segunda["id"], porciones=2)]
    assert verificar("De las recetas con pollo y maíz, ¿cuál me deja menos ingredientes por comprar para 2 personas?",
                     segunda["nombre"], historial) is None
