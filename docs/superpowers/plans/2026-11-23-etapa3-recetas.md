# Etapa 3 (agente de recetas): plan de implementación

> Plan corto. El código vive en los commits de cada tarea y en sus tests; acá van el orden, las interfaces y
> los criterios de terminado. Spec: `docs/superpowers/specs/2026-11-21-proyecto-completo-design.md` (§3–§5).

**Objetivo:** el agente de recetas con sus 4 variantes (base, + plan, + verificación, + ambas), las dos
líneas de base (libro cerrado y camino fijo) y los notebooks 02 y 03, listos para el desarrollo con
`dev-*`.

**Restricciones:** las de la Etapa 1. Además:
- No se corre ninguna tarea `rec-*` con modelo antes de la etapa 4.
- El detector se ajusta solo con `dev-*`.
- Las herramientas comparten con el generador de respuestas únicamente la capa de datos (`factibilidad/normalizar.py`: léxico, básicos y dietas) y `datos/recetas_final.csv`.

## Tareas

1. **Herramientas** (`herramientas/recetas.py`).
   - **Funciones:**
     - `buscar_recetas(contiene, excluye=[]) -> {total, recetas[≤10]}`;
     - `detalle_receta(receta_id, porciones=None)`;
     - `es_apta(receta_id, dieta) -> {apta, ingredientes_que_lo_impiden}`;
     - `faltantes(receta_id, porciones) -> {ingredientes[{ingrediente, necesita, hay, unidad, alcanza}], faltan}`.
   - **Inventario** desde `tareas/recetas_inventario.json`.
   - **Exportan** `FICHAS` y `HERRAMIENTAS`.
   - **Un nombre desconocido** devuelve un error con los nombres válidos más parecidos. Acepta sinónimos y plurales del léxico.
   - **Terminado cuando:** sobre todo el corpus, el orden de búsqueda, la aptitud, las cantidades escaladas y los faltantes coinciden con las funciones del generador. Además, varias respuestas de `dev-*` salen de encadenar las herramientas.
2. **Dominio recetas, detector y verificación.**
   - **`harness/dominios.py`:** `construir("recetas", config)` arma el prompt de sistema, con el inventario ordenado por vencimiento y los prioritarios marcados.
   - **`harness/detector.py`:** `detectar(pregunta) -> {dieta, porciones}`.
   - **`harness/verificacion.py`:** `verificar(pregunta, respuesta, historial) -> str | None`.
   - **`bucle`** suma dos enganches opcionales en `Dominio` (`antes_del_loop` y `antes_de_terminar`) y un historial de herramientas ejecutadas. Cuántas veces se rechaza como máximo lo fija `agente.max_rechazos`.
   - **Terminado cuando:** el detector acierta en las 21 preguntas `dev-*`, la verificación tiene casos que pasan y casos que fallan, y los tests del loop siguen en verde.
3. **Planificación y configuraciones.**
   - **`harness/planificacion.py`:** una llamada con un esquema JSON (`candidatas`, `criterio`, `pasos`, `cuando_parar`). Se registra en la traza como `llamada_modelo` de paso 1, más un evento `plan`.
   - **`configs/recetas_{base,plan,verif,ambas}.toml`:** sección `[agente]` con `planificacion`, `verificacion` y `max_rechazos`.
4. **Líneas de base.**
   - **`lineas_de_base/camino_fijo.py`:** una llamada con salida JSON restringida (contiene, excluye, dieta, porciones, que_pide, ingrediente, receta_id), un pipeline sin loop y una respuesta por plantilla. Escribe trazas válidas.
   - **`libro_cerrado.responder_tarea`:** acepta `sistema=`. Para recetas, el sistema incluye el inventario.
   - **`harness/corridas`:** suma `corredor_camino_fijo` y `corredor_libro_cerrado(config, sistema)`.
5. **Notebooks.**
   - **`02_herramientas_recetas`** (sin GPU): el corpus, el inventario, cada herramienta y pytest.
   - **`03_desarrollo`:** el detector sobre `dev-*`. Cada persona elige una variante (base, plan, verif, ambas, camino-fijo o libro-cerrado) y la corre sobre `dev-*` a temperatura 0 con la semilla 1337, con evaluación y resumen de fallas. Así 4 personas corren en paralelo.
