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

**Corrida "antes"** (`mundial__agente-antes__t0__s1337`, commit `30067f5`): 16/30 aciertos. El libro
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

**Lo que no arreglamos** porque son errores de razonamiento del modelo y no del harness: mun-009
(cuenta años en vez de torneos), mun-016, mun-025 y mun-030 (cuentas mal hechas sobre datos correctos),
y mun-013 y mun-022 (inventa respuestas en lugar de negarse). Quedan para el análisis del informe.

**Qué se espera en la corrida "después":** mun-007, mun-008 y mun-012 deberían pasar a acertar por el
arreglo 1, y mun-018 y mun-027 por el arreglo 2. mun-009 debería terminar, pero con la respuesta
equivocada. Se compara en la sección 5 del notebook `01`.

**Resultado de la corrida "después"** (`mundial__agente-despues__t0__s1337`, commit `ef58d97`, misma
configuración: temperatura 0, semilla 1337):

| | Antes | Después |
|---|---|---|
| Aciertos | 16/30 | **21/30** |
| Llamadas al modelo | 169 | 112 |
| Tokens de entrada | 355.110 | 185.715 |
| Tiempo total | 288 s | 190 s |
| Tareas que terminan en `tope_pasos` o `error` | 8 | 0 |

- *Lo que se predijo y pasó:* mun-007 y mun-008 (arreglo 1) y mun-018 (arreglo 2) pasan a acertar.
  En mun-007, la llamada rescatada termina en el paso 2 en lugar de dar 12 vueltas. mun-009 termina,
  pero con la respuesta equivocada (18).
- *Lo que mejoró sin estar predicho:* mun-010 acierta (antes llegaba al tope de pasos). mun-022 y
  mun-023 se niegan bien: sin las llamadas repetidas, el modelo llega a `terminar(null)`.
- *Lo que se predijo y no pasó:* mun-027 usa los filtros nuevos, pero cuenta solo las eliminatorias
  (6 en vez de 15). mun-012 se rescata, pero esta vez el modelo escribe `terminar("Argentina", ...)`
  con un motivo que admite que no hay datos de 2026: el rescate es fiel a lo que escribió el modelo,
  y el modelo inventó.
- *Lo que empeoró:* **mun-004** ("¿cuántos partidos se jugaron en 1986?") pasa de 52 a 32. El modelo
  filtra por `eliminatorias=true` sin que la pregunta lo pida. Es un costo del arreglo 2: la ficha de
  `partidos` ahora dice "filtrá cuando puedas", y eso empuja a filtrar también cuando no hace falta.
  mun-024 sigue mal, con otro error (usa a Messi en lugar del goleador de 1978).
- *Cuidado al leer la tabla:* cambiar la ficha de `partidos` cambia el prompt de todas las tareas, así
  que a temperatura 0 algunas diferencias son ruido de la generación y no efecto del arreglo (mun-012
  y mun-024 lo muestran). Con una sola corrida por lado no se puede separar una cosa de la otra.
- *Lo que no hacemos:* volver a ajustar la ficha mirando mun-004. Sería ajustar el harness a las
  tareas públicas, que son las que puntúan.

**Corridas completas y commit.** Volver a correr la sección 2 del notebook después de un push trababa
el libro cerrado con `CommitDistinto`, aunque la tanda estaba completa y no se iba a correr nada.
`correr_tanda` ahora devuelve el resumen sin revisar el commit cuando todas las tareas ya están en
Drive. Si falta alguna, el chequeo sigue igual.

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

## 2026-11-23 · Desarrollo, vuelta 1 → vuelta 2 (solo tareas `dev-*`)

**Vuelta 1** (commit `7048ef9`, temperatura 0, semilla 1337; corridas `dev__<variante>__t0__s1337`):

| Variante | Aciertos | Imposibles inventadas |
|---|---|---|
| libro-cerrado | 4/21 | 0 |
| camino-fijo | 4/21 | 2 |
| base | 11/21 | 2 |
| plan | 9/21 | 1 |
| verif | 13/21 | 0 |
| ambas | 9/21 | 1 |

**Qué falló primero, según las trazas, y qué cambiamos:**

- **El modelo tenía la respuesta y la escribió como texto** (`dev-010` en base y verif, `dev-011` en plan y ambas). La forma fue `terminar({"cerdo;chorizo;morron;queso"}, "...")`, repetida hasta el tope de 16 pasos. El rescate del Bloque 1 no la reconocía, porque esperaba un objeto JSON después de `terminar(`. Ahora lee las llaves como un conjunto de Python y sigue con la lectura posicional.
- **"carne" en `excluye`** (`dev-006`, `dev-012`). «Sin carne ni pescado» se tradujo a `excluye=["carne"]`. La herramienta sugirió nombres parecidos (condimento, crema de leche…) y el modelo se rindió. Ahora `buscar_recetas` reconoce las categorías de dieta (carne, gluten, lácteos, origen animal) y explica que hay que usar `es_apta`.
- **Reglas nuevas en el prompt del agente**, que valen para las cuatro variantes:
  - «la más rápida» es la primera de la lista que cumple, sin usar `faltantes` para elegirla (`dev-005`);
  - las cantidades de `detalle_receta`/`faltantes` ya vienen escaladas, así que no hay que volver a multiplicar (`dev-008`: 750 → 1125);
  - una receta nombrada por número se usa directo;
  - si ninguna receta cumple, se responde `null` y no un texto (`dev-006`);
  - lo que vence antes se mira en la lista de la heladera (`dev-020`).
- **Plan.** El esquema no tenía `receta_id` (`dev-004` buscó arroz en vez de usar la receta 4057), inventaba porciones y mandaba a revisar todas las candidatas aunque la pregunta pidiera la más rápida. Agregamos `receta_id` y la regla de cuándo comparar varias candidatas.
- **Camino fijo.** La llamada de traducción le ponía una dieta a preguntas que no la piden (`dev-001` → vegetariana) y dejaba `contiene` vacío. Le agregamos instrucciones más precisas y dos ejemplos que no son tareas de ningún conjunto. Una línea de base floja haría parecer mejor al agente sin que lo sea.
- **Verificación.** El mensaje para un número que no aparece ahora explica que las cantidades ya vienen escaladas (`dev-008` reintentó el mismo número).

**Lo que no tocamos, a propósito:**

- `dev-017` («¿para cuántas personas alcanzan los huevos?»): el modelo no hace la división. Agregar una herramienta de cálculo cambiaría el diseño de la propuesta.
- `dev-021` («cuántas alcanzan»): en la base, el modelo excluyó el limón en lugar de incluirlo.

Estas dos quedan como fallas del modelo, para comparar las variantes.

**Un cambio más antes de la vuelta 2: repetir una llamada que falló.** Cuando el modelo repetía exactamente una llamada que había devuelto error, el freno de repeticiones del Bloque 1 le contestaba «el resultado no cambia, está más arriba» y le sugería terminar. Para una llamada fallida ese consejo es malo: no le recuerda qué falló ni que lo que tiene que cambiar son los argumentos. Ahora el bucle guarda el error de cada llamada hecha y, si se repite, lo vuelve a mostrar y pide cambiar los argumentos, probar otra herramienta o terminar. Las llamadas con argumentos inválidos se siguen pudiendo reintentar como antes. No cambia nada cuando la llamada anterior salió bien. El Bloque 1 ya está medido con el commit anterior, así que no lo afecta.

**Lo que dejamos como estaba:** no le agregamos a `faltantes` ni el vencimiento ni «para cuántas porciones alcanza» por ingrediente. Eso resolvería `dev-017` y `dev-020` con la herramienta en lugar del modelo, y contradice lo que decidimos arriba.

## Desarrollo, vuelta 2 (parcial) → cambios para la vuelta 3

**Vuelta 2** (commit `69e6fc3`; corridas `dev-v2__<variante>__t0__s1337`). Cuando escribimos esto habían terminado dos variantes: camino-fijo pasó de 4/21 a 6/21 y verif de 13/21 a 11/21. Ambas iba por la tarea 13 y base, plan y libro-cerrado todavía no se habían corrido.

**Ojo con leer la diferencia de verif.** Con 21 tareas, ±2 aciertos está dentro de lo que cambia el modelo cuando se toca el prompt: en verif se arreglaron 3 tareas (`dev-006`, `dev-010`, `dev-017`) y se rompieron 5. Mirando las trazas, de esas 5 hay 2 que son ruido del modelo y no las tocamos: `dev-016` buscó con `excluye=["maíz"]` cuando la pregunta pide maíz, y `dev-019` eligió la segunda de la lista aunque la regla dice que la más rápida es la primera. (`dev-012` sigue mal, ahora respondiendo «1» con un motivo que dice que faltan 2.) Las otras tres eran fallas de la verificación, que dejó pasar respuestas que tendría que haber frenado:

- **Un número dentro de un decimal contaba como visto** (`dev-013`). «¿Cuántos gramos de proteína tiene…?»: el modelo respondió «25». La regla 5 buscaba el texto «25» en los resultados y lo encontró adentro de `"cantidad": 0.25`. Ahora se comparan números enteros contra los números que aparecen en los resultados y en la pregunta.
- **Negarse con una frase** (`dev-014`, `dev-015`). El modelo escribió «No hay recetas que incluyan arroz, frutilla y cerdo» como respuesta de `terminar` en vez de `null`, y la evaluación lo cuenta como respuesta inventada. Regla nueva (7): si la respuesta es una frase que empieza diciendo que no hay, no existe o no se puede, se rechaza y se le pide `null` con el motivo. Un «No» suelto (las preguntas de sí o no) sigue pasando.

Las dos reglas son de la verificación, así que solo afectan a verif y a ambas. Ambas de la vuelta 2 se está corriendo con el commit anterior, por eso la vuelta 3 tiene que volver a correr al menos verif y ambas.

## 2026-11-23 · Desarrollo, vuelta 2 → vuelta 3 (solo tareas `dev-*`)

**Vuelta 2** (commit `69e6fc3`; corridas `dev-v2__<variante>__t0__s1337`):

| Variante | Vuelta 1 | Vuelta 2 | Imposibles inventadas (v2) |
|---|---|---|---|
| libro-cerrado | 4/21 | 4/21 | 0 |
| camino-fijo | 4/21 | 6/21 | 1 |
| base | 11/21 | 11/21 | 3 |
| plan | 9/21 | 16/21 | 1 |
| verif | 13/21 | 11/21 | 3 |
| ambas | 9/21 | 16/21 | 1 |

**Lectura.**

- **El plan subió de 9 a 16** con el ajuste del esquema.
- **La verificación casi no actuó:** rechazó una sola vez en 21 tareas, y verif dio exactamente lo mismo que base.
  - Dos agujeros ya los cerró el commit `640179a`: un número que aparece dentro de un decimal se daba por visto, y las negativas escritas como frase pasaban.
  - Lo que sigue explica el resto.

**Qué falló primero en las trazas, y qué cambiamos:**

1. **No se respeta el orden de la búsqueda.** En `dev-008` y `dev-019` (base) eligió una receta del medio de la lista.
   - La verificación ahora exige que, si la pregunta pide «la más rápida», cada candidata anterior a la respondida haya quedado descartada: con `es_apta` en falso para la dieta pedida, o con faltantes si pide no comprar.
   - Es el «no saltearse filtros» que le asignamos en la propuesta, y le da algo concreto que medir.
   - `buscar_recetas` ahora numera las candidatas (`posicion`) y dice que la 1 es la más rápida.
2. **«Con X» terminaba en `excluye`** (`dev-016`, `dev-021`). Agregamos una regla en el prompt: lo que la receta lleva va en `contiene`.
3. **Vencimientos** (`dev-005` y `dev-020` fallaban en todas las variantes).
   - El harness ahora escribe cuál vence primero y cuáles dos vencen antes.
   - `faltantes` trae `vence_en_dias` de cada ingrediente de la heladera.
   - Las líneas de base ven la misma tabla de la heladera.
4. **Cuentas** (`dev-012`: «faltan 2 huevos» pero respondió `1`; `dev-017`: 6 huevos «alcanzan para 6» cuando son 12). `faltantes` ahora trae `cuantos_faltan` y, por ingrediente de la heladera, `alcanza_para_porciones`. El modelo lee el número en lugar de calcularlo.
5. **Frases de dieta.** El plan puso `sin_gluten` para «sin carne ni pescado» (`dev-006`). Agregamos la misma tabla de frases → dieta en el prompt, en el plan y en el camino fijo.
6. **Camino fijo.**
   - La traducción perdía el segundo ingrediente («huevo y maíz» → `[huevo]`, en 6 tareas). La instrucción ahora pide todos los ingredientes.
   - Si en `excluye` aparece una categoría («carne», «gluten»), el pipeline la pasa a `dieta`. Es una regla fija del pipeline, no del modelo.

**Vuelta 3:** las 6 variantes, en `dev-v3__<variante>__t0__s1337`. Después de esta vuelta congelamos con el tag `medicion-v1`.

## 2026-11-23 · Desarrollo, vuelta 3 → vuelta 4 (solo tareas `dev-*`)

**Vuelta 3** (commit `375c6a5`; corridas `dev-v3__<variante>__t0__s1337`):

| Variante | Vuelta 2 | Vuelta 3 | Inventadas (v3) |
|---|---|---|---|
| libro-cerrado | 4/21 | 4/21 | 0 |
| camino-fijo | 6/21 | 12/21 | 1 |
| base | 11/21 | 14/21 | 2 |
| plan | 16/21 | 15/21 | 2 |
| verif | 11/21 | 15/21 | 1 |
| ambas | 16/21 | 15/21 | 2 |

**Fallas que se repiten en las variantes del agente, según las trazas, y qué cambiamos:**

- **La cuenta de cuánto falta comprar** (`dev-009`, en las 4 variantes). El motivo dice «se necesitan 10 huevos, hay 6» y la respuesta es 5. Ahora `faltantes` devuelve también `falta` por ingrediente (lo que hay que comprar: necesita − hay), igual que ya devuelve el vencimiento y las porciones que alcanzan. Vale para todas las variantes que usan la herramienta.
- **Preguntas por datos que el recetario no tiene** (`dev-013` proteínas en las 4; `dev-015` supermercado en base, plan y ambas). El «20» de proteínas pasaba la verificación por ser un número chico. Le agregamos al detector qué datos no tiene el recetario (información nutricional, precios, comercios), con expresiones ajustadas solo con `dev-*`. Si la pregunta pide uno de esos, la verificación solo acepta `null` (regla 8).
- **Negarse con una frase que no empieza con «No…»** (`dev-015`: «El recetario no tiene información sobre supermercados»). La regla 7 ahora busca la negativa en cualquier parte de la respuesta («no tiene», «no incluye», «sin datos»…), siempre que la respuesta no sea el nombre de una receta.
- **La más rápida con respuesta numérica** (`dev-008`, en base y verif). Respondió los gramos de la segunda receta de la lista. La regla del orden de la vuelta 2 solo miraba respuestas que fueran el nombre de una receta. Ahora también mira la última receta consultada con `faltantes` o `detalle_receta`, pero solo cuando la pregunta no pide dieta ni «sin comprar». Con esos filtros, el modelo descarta candidatas sin pasar siempre por `es_apta`: en `dev-011` y `dev-012` lo hizo y acertó, y la regla completa los habría rechazado.

**Cómo lo comprobamos sin correr el modelo.** Pasamos la verificación nueva sobre la respuesta final de cada tarea de la vuelta 3, en base, plan, verif y ambas, rehaciendo las llamadas a herramientas de la traza. No rechaza ninguna respuesta que fue acierto. Rechaza `dev-008` (750), `dev-013` (20 y 22), `dev-015` (las frases) y `dev-005` en base, que eran todas fallas. Lo que el modelo haga después del rechazo se ve recién en la vuelta 4.

**Lo que no tocamos, a propósito:**

- `dev-020` («de los ingredientes que usa, ¿cuál vence primero?»): responde pollo o huevo, que no están en la receta, aunque `faltantes` trae `vence_en_dias`.
- `dev-021` («¿cuántas puedo hacer?»): tiene que contar en cuántas de las 6 recetas alcanza el pollo, y confunde `alcanza_para_porciones` con esa cuenta.
- `dev-018` en plan y ambas: el plan le pide recorrer las candidatas y no para al encontrar la primera que alcanza, hasta el tope de 16 pasos.
- `dev-006` en camino-fijo: la traducción pidió «morro» en lugar de «morrón». Es una falla de esa línea de base.

**Organización.** La vuelta 4 se guarda en `dev-v4__<variante>__t0__s1337` y se corren las 6 variantes: el cambio de `faltantes` afecta a todas menos libro-cerrado, y lo corremos igual para tener la tanda completa con el mismo commit.

## 2026-11-23 · Desarrollo, vuelta 4 → vuelta 5 (solo tareas `dev-*`)

**Vuelta 4** (commit `7175e6d`; corridas `dev-v4__<variante>__t0__s1337`):

| Variante | Vuelta 3 | Vuelta 4 | Inventadas (v4) |
|---|---|---|---|
| libro-cerrado | 4/21 | 4/21 | 0 |
| camino-fijo | 12/21 | 12/21 | 1 |
| base | 14/21 | 13/21 | 2 |
| plan | 15/21 | 17/21 | 3 |
| verif | 15/21 | 15/21 | 0 |
| ambas | 15/21 | 20/21 | 0 |

**Lo que se ve en las trazas:**

- `dev-009` lo aciertan las cuatro variantes del agente: con `falta`, el modelo ya no tiene que restar.
- En verif y ambas, la verificación rechazó el «20» de proteínas (`dev-013`) y la frase del supermercado (`dev-015`). En el segundo intento, el modelo respondió `null` y quedaron 0 inventadas.
- `dev-008` en verif: la verificación lo rechazó y el modelo cambió de receta, pero respondió 1125 sin consultarla. Como ya había usado el único rechazo (`max_rechazos = 1`), la respuesta pasó. Es el diseño: un solo rechazo por tarea.
- `dev-021` en ambas acierta («2»), pero el motivo habla de una sola receta. Lo contamos como acierto porque así puntúa la evaluación, pero no lo presentamos como un razonamiento correcto.

**Qué cambiamos: la salida de `faltantes` desbordaba el contexto.** `dev-011` terminó en `error` en base y en verif: «request (8724 tokens) exceeds the available context size (8192 tokens)». El modelo recorre 10 recetas con `faltantes`, y el campo `falta` de la vuelta 4 empujó la conversación por encima del límite. Ahora los ingredientes que no están en la heladera traen solo `ingrediente`, `necesita`, `unidad`, `alcanza` y `falta`. Ya no traen `hay: 0`, `vence_en_dias: null` ni `alcanza_para_porciones: 0`, que no aportan nada. Con las 9 recetas que consultó `dev-011`, los resultados pasan de 13.660 a 11.180 caracteres (−18%), menos que en la vuelta 3, antes de `falta`. La línea de base de camino fijo ahora usa `falta` en lugar de calcular `necesita − hay`, que da lo mismo.

No subimos `num_ctx`: 8192 es el valor fijado para todas las corridas y cambiarlo ahora movería todas las variantes.

**Organización.** La vuelta 5 se guarda en `dev-v5__<variante>__t0__s1337`, con las 6 variantes. El cambio de `faltantes` afecta a todas menos libro-cerrado.

## 2026-11-23 · Plan de la medición congelada (escrito antes de correr ninguna tarea `rec-*`)

**Qué se corre** (notebook 04, `colab/tandas.py`). Hay 25 tandas sobre las 21 tareas congeladas, en orden de prioridad:

1. base, plan y verif a temperatura 0,7 con las semillas 1337, 1338 y 1339;
2. libro cerrado y camino fijo a 0,7, con las mismas semillas;
3. la referencia a temperatura 0 (semilla 1337) de esas cinco variantes;
4. ambas, a 0,7 con las 3 semillas y a temperatura 0;
5. la repetición de la referencia de base a temperatura 0 (`congelado-bis`), para medir el no determinismo.

Todo corre con el código del tag `medicion-v1`, que el notebook 04 fija antes de importar nada. Si hay que recortar, se recorta desde el final de la lista.

**Comparaciones declaradas.** Cada una se hace de a pares, por tarea y semilla (63 pares), con el test de signo exacto (dos colas, p < 0,05). Al lado va el criterio de la propuesta: la diferencia de medias tiene que superar el rango de las semillas.

| Comparación | Pregunta |
|---|---|
| base → plan | decisión 1: ¿el plan mejora al agente? |
| base → verif | decisión 2: ¿la verificación mejora al agente? |
| base → ambas | las dos juntas |
| plan → ambas | ¿la verificación suma sobre el plan? |
| verif → ambas | ¿el plan suma sobre la verificación? |
| camino fijo → base | ¿el agente le gana al camino fijo? |
| libro cerrado → base | ¿las herramientas le ganan a la memoria? |

**Por grupo**, solo para mirar, porque quedan muy pocas tareas en cada grupo:

- base → plan en las 5 tareas fuera del esquema;
- base → verif en las 3 imposibles (inventos);
- camino fijo → base en las 13 tareas dentro del esquema;
- base → plan en las 3 de vencimiento.

**Lo que sumamos de la Clase 12 (Notebook B, §2).** Todo sale de las mismas tandas, sin llamadas extra al modelo, salvo la repetición a temperatura 0:

- **Intervalo de Wilson** del 95% para cada variante.
- **Frontera acierto/costo**, con tokens por tarea.
- **pass@3 y pass^3** con las 3 semillas.
- **Control «mismo gasto».** Es el voto de mayoría de las 3 corridas de base, comparado contra plan, verif y ambas: las tres gastan más llamadas que base, así que ganarle a base no alcanza.
- **No determinismo a temperatura 0**, con la repetición de base.

**Lo que sabemos de antemano sobre la potencia.** Con 21 tareas, una mejora moderada puede no distinguirse del azar. Si el resultado es «no se distingue», en el informe lo decimos así, sin afirmar que no hay efecto. Emparejar por semilla da 63 pares, pero no son independientes: las tres semillas de una misma tarea tienden a acertar o fallar juntas. Lo declaramos como limitación.

**Límite conocido de la verificación.** Igual que el verificador de la clase, chequea la coherencia con lo que devolvieron las herramientas, no la verdad. Una receta equivocada con números que salen de `faltantes` pasa. El chequeo del orden de las candidatas cubre una parte de eso.

## 2026-11-23 · Cierre del desarrollo (vuelta 5) y ajustes antes del tag `medicion-v1`

**Vuelta 5** (commit `1709bd1`; corridas `dev-v5__<variante>__t0__s1337`, las 6 con el mismo commit):

| Variante | Vuelta 4 | Vuelta 5 | Inventadas (v5) | Tokens (21 tareas) |
|---|---|---|---|---|
| libro-cerrado | 4/21 | 4/21 | 0 | 7.457 |
| camino-fijo | 12/21 | 12/21 | 1 | 20.174 |
| base | 13/21 | 15/21 | 2 | 273.906 |
| plan | 17/21 | 17/21 | 3 | 287.935 |
| verif | 15/21 | 17/21 | 0 | 287.690 |
| ambas | 20/21 | 20/21 | 0 | 298.420 |

- El cambio de `faltantes` cumplió: `dev-011` ya no desborda `num_ctx` y lo aciertan las cuatro variantes del agente.
  Ninguna tarea terminó en `error` por contexto.
- Las dos decisiones arreglan fallas distintas, como esperábamos. El **plan** resuelve las que piden comparar
  candidatas (`dev-005`, `dev-008`, `dev-021`), que base y verif fallan. La **verificación** resuelve los
  inventos en las imposibles (`dev-013`, `dev-014`), que base y plan inventan. Ambas junta las dos cosas.
- `dev-020` (el ingrediente que vence primero, respuesta «zanahoria») lo fallan las seis variantes. No lo
  seguimos ajustando: queda como falla conocida.

**Decisión: el desarrollo termina acá.** Cinco vueltas sobre las mismas 21 tareas `dev-*` ya ajustan el
harness a ellas; otra vuelta para `dev-020` sería ajustar a una tarea. Lo que vale es lo que salga en las
tareas congeladas. En el informe va como limitación que el `dev` quedó sobreajustado (20/21 en ambas).

## 2026-11-24 · Medición congelada y cierre

**La medición.** Corrieron las 25 tandas del plan, sin recortar nada: también `ambas` y la repetición de
base a temperatura 0. Todas con el commit del tag `medicion-v1` (`da315dc`), y cada sesión que tocó una
tanda dejó registrado que corrió en una Tesla T4 con el modelo 100% en GPU. No quedaron tandas duplicadas. 
Las tablas están en `resultados/analisis/` y la lectura, en el informe.

**Lo que salió distinto de lo que afirmamos** (propuesta §9):

- La verificación bajó las respuestas inventadas de 8 a 0 (de 9 imposibles), como esperábamos. En
  aciertos totales subió de 14,0 a 16,3, pero el test de signo no lo distingue del azar (p = 0,065), y
  dentro del esquema bajó de 33 a 31 de 39.
- La planificación mejoró al agente (p = 0,031), pero **no donde la apuntamos**: en las 5 tareas fuera del
  esquema pasó de 8 a 11 de 15, que no se distingue (p = 0,375). La mejora se reparte entre las de adentro
  y las imposibles (inventó 4 en lugar de 8).
- El agente base no le gana al camino fijo (14,0 contra 15,0). Esperábamos que el camino fijo ganara
  adentro (ganó 36 a 33 de 39), pero también que el agente compensara afuera, y base solo lo hace con las
  decisiones agregadas.
- Temperatura 0 no es determinista: base corrida dos veces igual cambió 5 de 21 respuestas (15 y 13
  aciertos). La «referencia a temperatura 0» se reporta con esa advertencia.

**Lo que agregamos al análisis después de escribir la propuesta** (todo declarado antes de medir, en la
entrada «Plan de la medición congelada»): el test de signo por pares, el intervalo de Wilson, pass@3 y
pass^3, la frontera acierto/costo, el control «mismo gasto» (voto de mayoría de 3 corridas de base) y la
repetición a temperatura 0. Vienen de la Clase 12, que fue después de la propuesta.

**Siete comparaciones al 0,05.** No corregimos por comparaciones múltiples porque no lo declaramos antes.
Con Bonferroni (0,05 / 7) solo sobreviviría libro cerrado → base. Va como limitación en el informe.

**Presupuesto: estimado contra real** (llamadas al modelo, de los CSV de `resultados/`):

| Experimento | Estimado | Real |
|---|---|---|
| Bloque 1 (libro cerrado, antes y después) | ~390 | 311 |
| Desarrollo (`dev-*`) | ~400 | 2.569 |
| Medición congelada | ~1.450 | 2.343 |
| **Total** | **~2.240** | **5.223** |

Gastamos 2,3 veces lo estimado, unos 13,7 millones de tokens contra 5,5 estimados. El desvío grande es el
desarrollo: hicimos 5 vueltas con las 6 variantes en lugar de 2 o 3 con 5, y las tareas que comparan
candidatas llevan más pasos que los ~6 por tarea que estimamos. Se pudo pagar porque las tandas se
repartieron entre varias cuentas de Colab en paralelo, y el calendario terminó adelantado: las mediciones
cerraron el 24/11 en lugar del 28/11.

**Cierre del repositorio.**

- Las trazas y los CSV de las 58 corridas reportadas (Mundial, las 5 vueltas de desarrollo y la medición
  congelada) están en `trazas/` y `resultados/`. Se dejaron afuera `tomada.json` y las copias duplicadas de
  Drive de `dev-v2__base`.
- La propuesta aprobada (v3) pasó a `propuesta.md` en la raíz, como pide el enunciado; la v1 y la v2
  quedan en `docs/`.
- Notebook `06_demo` para la presentación: una tarea del conjunto y una pregunta nueva con `ambas`, y la
  misma tarea con `base` al lado.
