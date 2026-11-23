# Registro de decisiones

Cada entrada tiene fecha, qué se decidió, por qué y qué se descartó. Las ediciones del conjunto de
evaluación congelado van acá (ENUNCIADO §8).

## 2026-11-21 · Presupuesto, cómputo y plan

**Tiempo.** Del 21/11 a la entrega del 29/11: 8 días. Calendario por etapas (spec
`docs/superpowers/specs/2026-11-21-proyecto-completo-design.md`, §6):

1. Base y Bloque 1 (22–23/11).
2. Arreglo del Bloque 1 (24/11).
3. Recetas y ajuste con `dev-*` (24–26/11).
4. Mediciones congeladas (26–28/11).
5. Cierre (28–29/11).

**Cómputo.** Varias cuentas gratis de Colab con T4, en paralelo. Ollama 0.40.10 (la del kit) y
`qwen3:8b`. La prueba de factibilidad de la propuesta corrió en CPU local con Ollama 0.40.16; las
mediciones que se reportan corren todas en la T4.

**Presupuesto de llamadas al modelo.**

| Experimento | Llamadas (estimadas) |
|---|---|
| Bloque 1: libro cerrado, 30 tareas | 30 |
| Bloque 1: agente antes y después del arreglo, 30 tareas × ~6 llamadas × 2 | ~360 |
| Bloque 2: desarrollo (`dev-*`, 5 configuraciones, 2 o 3 vueltas) | ~400 |
| Bloque 2: medición congelada (propuesta v3, §8) | ~1.450 |
| **Total** | **~2.240** |

**Qué recortamos primero si no llegamos** (propuesta v3, §8):

1. La corrida conjunta de planificación con verificación.
2. Bajar de 3 a 2 semillas.
3. Quedarnos solo con `vegetariana`/`vegana`.

**Cómo trabajamos.**

- La lógica va en módulos `.py` del repo, con tests sin modelo que corren en local.
- Los notebooks de Colab clonan el repo, explican cada pieza y corren las mediciones.
- Cada traza se copia a Drive (`TPFinal-heladera/corridas/`) cuando termina su tarea. Una corrida cortada se retoma salteando las tareas que ya tienen una traza válida.
- Un `manifiesto.json` por corrida fija el commit con que se corrió, para no mezclar versiones del harness.

**Descartado:**

- Escribir todo dentro de los notebooks: duplica código entre notebooks y no se puede testear.
- Sincronizar a Drive cada N tareas: si se corta la sesión, se pierden hasta N tareas.
- Guardar el modelo en Drive: copiar 5 GB tarda más o menos lo mismo que bajarlo.

**Desarrollo en Windows.** Dos tests del esqueleto del kit (`tests/test_agente.py`) fallan en Windows.
Lanzan el agente con `SYSTEMROOT=""`, y en Windows eso rompe la inicialización de SSL. En Linux
(Colab) pasan. Los reescribimos para que hereden el entorno y solo cambien `OLLAMA_HOST`.

## 2026-11-22 · Diseño del loop (Bloque 1)

Decisiones que no salen del enunciado, cada una con su motivo:

- **Un solo loop para los dos dominios** (`harness/bucle.py`). El Mundial y las recetas cambian solo las herramientas y el prompt (`harness/dominios.py`). Así, lo que arreglemos en el Bloque 1 vale para el Bloque 2.
- **Los errores vuelven al modelo como resultado de herramienta, con la corrección explicada.** Por ejemplo: «"a" tiene que ser integer, y llegó str». Un error genérico no le dice al modelo qué cambiar.
- **Los argumentos se validan contra la ficha JSON antes de ejecutar.** Si no, una herramienta con argumentos de más o de menos levanta un `TypeError` que no le sirve al modelo.
- **A `terminar` se le normaliza la respuesta.** Un número o una lista se pasan a texto, y el texto "null" se toma como `null`. El modelo a veces lo escribe como texto, y eso no es inventar.
- **Si el modelo contesta con texto suelto, se le manda un recordatorio** y se sigue, en lugar de cortar la corrida. Cuesta un paso, que cuenta para el tope.
- **Un `ContextOverflow` no se reintenta.** El mismo prompt no va a entrar la segunda vez.
- **Reintentos con espera exponencial** (2, 4 y 8 s, 3 reintentos). En Colab, Ollama a veces tarda en cargar el modelo después de un corte.
- **La traza agrega campos:** el texto del modelo, `razon_fin`, el contenido que vio el modelo de cada resultado y un evento `sin_llamadas`. Sin el contenido no se puede explicar un arreglo desde la traza.
- **Ids generados `p<paso>-<n>`** cuando Ollama no trae uno o repite uno anterior. El validador exige que sean únicos en toda la traza.

## 2026-11-23 · Agente de recetas (Etapa 3)

- **Herramientas verificadas contra el generador en todo el corpus**, no solo en las tareas. Las comparamos en orden de búsqueda, aptitud, cantidades escaladas y faltantes. Las dos implementaciones comparten solo la capa de datos (`factibilidad/normalizar.py` y `datos/recetas_final.csv`).
- **"No está en la heladera" significa siempre "falta"**, aunque la cantidad necesaria sea 0. Lo encontró la comparación con el generador: una receta pedía "1,2 gramos de calabacín", que la normalización dejó en 0 unidades.
- **`buscar_recetas` acepta sinónimos y plurales del léxico.** Ante un nombre desconocido devuelve los parecidos, porque el modelo escribe "lentejas" o "patata".
- **El detector de dieta y porciones son reglas en código** (`harness/detector.py`), ajustadas solo con las 21 preguntas `dev-*`. Ninguna pregunta congelada pasó por los tests.
- **La verificación (`harness/verificacion.py`) no rechaza los números chicos** (≤ 20) aunque no aparezcan en ningún resultado. Pueden ser cuentas legítimas ("cuántas alcanzan", "cuántos faltan"). Los números grandes sí tienen que aparecer, que es lo que apunta a calorías o precios inventados.
- **Negarse no se verifica**, y la verificación rechaza como máximo una vez (`agente.max_rechazos = 1`). Así no se arma un loop entre el modelo y el chequeo.
- **El plan se registra como `llamada_modelo` del paso 1, más un evento `plan`.** Cuenta para el costo y el tope de tokens. Si el plan sale roto, el agente sigue sin plan, y queda registrado.
- **`max_pasos = 16` para recetas** (14 en el Mundial). Las tareas que comparan candidatas necesitan hasta 9 herramientas, más el plan y una verificación.
- **El libro cerrado de recetas ve la heladera en el prompt**, para que la comparación con el agente sea justa.
- **El camino fijo recorre solo las 10 candidatas visibles** de `buscar_recetas`, igual que el agente.

## 2026-11-23 · Arreglos del Bloque 1 (después de la corrida "antes")

**Corrida "antes"** (`mundial__agente-antes__t0__s1337`, commit `30067f5`): 17/30 aciertos. El libro
cerrado sacó 5/30. Las trazas muestran dos fallas del harness, cada una visible en el **primer** paso
donde la corrida se tuerce:

**Arreglo 1: llamadas escritas como texto** (tarea elegida: **mun-007**). En el paso 2 el modelo ya
tenía la respuesta ("United States"), pero en lugar de mandar un `tool_call` escribió
`{"name": "terminar", "arguments": {...}}` en el contenido. El loop lo trató como texto suelto, mandó
el recordatorio y el modelo repitió lo mismo 12 veces hasta `tope_pasos`. La misma falla aparece con
otras dos formas: `terminar("8", "...")` (mun-008, mun-009) y `terminar{"respuesta": "null", ...}`
(mun-012, una imposible que el modelo quería negar).

- *Cambio:* `rescatar_llamada` en `harness/bucle.py`. Si el texto tiene **una sola** llamada reconocible
  a una herramienta que existe (JSON con `name`/`arguments`, `nombre{...}`, `nombre({...})` o
  `nombre(a, b)` con los argumentos en el orden de la ficha), se atiende como un `tool_call`. Los
  argumentos rescatados pasan por la misma validación que los demás. La traza lo marca con el evento
  `llamada_rescatada`.
- *Por qué en el loop y no en el prompt:* el recordatorio ya le decía que llamara a la herramienta, y
  el modelo repitió el mismo texto 12 veces. El modelo sabía qué hacer; el contrato con Ollama es lo que falló.
- *Descartado:* rescatar cualquier texto que parezca una respuesta (por ejemplo "4" o "13"). Eso sería
  inventarle una llamada a `terminar` al modelo. Esos casos se siguen resolviendo con el recordatorio
  (mun-003 y mun-011 acertaron así).

**Arreglo 2: resultados que no entran y llamadas repetidas** (tareas: **mun-018**, mun-023 y mun-027).
`partidos(2022)` devuelve ~12.000 caracteres y se recorta a 4.000. El modelo no puede contar sobre una
lista cortada y vuelve a pedir **la misma** llamada: cada repetición suma ~1.600 tokens hasta que el
pedido supera `num_ctx` y la tarea cierra con `error`.

- *Cambio en el loop:* una llamada idéntica (mismo nombre y argumentos) a una anterior que pasó la validación
  no se vuelve a ejecutar. Vuelve un error corto que dice en qué paso está el resultado y, si había
  venido recortado, que use los filtros. Las herramientas del Mundial son deterministas: repetir no
  trae nada nuevo y solo llena la ventana. Una llamada rechazada por argumentos inválidos no cuenta como hecha.
- *Cambio en la herramienta* (ENUNCIADO §4.2 permite cambiarlas): `partidos` acepta `seleccion` y
  `eliminatorias`. Con `eliminatorias=true`, 2022 son 16 partidos (~3.000 caracteres); con
  `seleccion="France"`, 1998 son 7. Sin filtros devuelve lo mismo que antes, así que el contrato de
  campos y los verificadores no cambian.
- *Descartado:* subir `tope_resultado_caracteres` o `num_ctx`. Agranda la ventana para un caso y no
  arregla que el modelo repita llamadas; además, el tope tiene que seguir chico para las recetas.
- *Descartado:* un filtro `solo_penales`. Resolvería mun-018 de forma directa, pero sería una
  herramienta hecha para la pregunta. `seleccion` y la fase sirven para cualquier pregunta sobre
  partidos.

**Lo que no arreglamos** porque son errores de razonamiento del modelo y no del harness: mun-009
(cuenta años en vez de torneos), mun-016, mun-025 y mun-030 (cuentas mal hechas sobre datos correctos),
y mun-013 y mun-022 (inventa respuestas en lugar de negarse). Quedan para el análisis del informe.

**Qué se espera en la corrida "después":** mun-007, mun-008 y mun-012 deberían pasar a acertar por el
arreglo 1, y mun-018 y mun-027 por el arreglo 2. mun-009 debería terminar, pero con la respuesta
equivocada. Se compara en la sección 5 del notebook `01`.

## 2026-11-23 · Recetas con cantidades absurdas (D20)

Revisando el corpus aparecieron cantidades imposibles: «400 kilogramos de nueces», «100 pechugas de pollo
por persona», «120 tazas de harina». Buscamos las cantidades normalizadas fuera de rango (más de 3 kg o
3 l, más de 40 unidades, más de 20 dientes): salieron **17 recetas de 3.198**. Las revisamos a mano:

- **10 traen la cantidad absurda en el texto original** y la normalización la convierte tal cual
  (400 kg de nueces, 500 botes de garbanzos, 500 patatas, 100 cebollas...).
- **4 tienen un texto razonable y la conversión falla**: «1 kilo de aceitunas» da 250 unidades,
  «3 tazas de chile de árbol» da 48 unidades.
- **3 son plausibles** y se quedan: 5,6 kg de codillo para 8, 4 l de leche para 5, 25 dientes de ajo para 5.

- *Decisión:* excluir las 14 del dataset final (`EXCLUIDAS` en `factibilidad/preparar_dataset.py`, decisión
  D20 en `datos/normalizacion/decisiones.csv`). Siguen en `lineas.csv` para que se vea qué tenían.
  El dataset pasa de 3.198 a 3.184 recetas.
- *Descartado:* corregir las 14 a mano. Habría que inventar la cantidad buena en 10 de ellas (¿400 g de
  nueces?) y son el 0,4 % del corpus.
- *Descartado por ahora:* arreglar las reglas de aceitunas y chiles. Afectan a esas 4 recetas con
  cantidades grandes; si aparecen más casos, se corrige la regla en `equivalencias.csv`.
- *Efecto en las tareas:* ninguno. Volvimos a correr `factibilidad/borrador_respuestas.py` y las 21
  congeladas, las 21 de desarrollo y el inventario salieron idénticos (ninguna tarea usaba esas recetas
  ni las tiene en sus conteos). Los tests siguen en verde.
- *Pendiente de revisar:* comparando cada ingrediente con su mediana por comensal aparecen 66 recetas con
  más de 15 veces la mediana. La mayoría tiene `comensales = 1` con cantidades de torta o conserva
  (500 g de manteca, 1 kg de azúcar): parece un `comensales` mal cargado, no una cantidad rota. No se tocó.
