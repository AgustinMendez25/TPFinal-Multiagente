# propuesta.md (v3): Rescatá la heladera, un agente para cocinar con lo que hay

> **Qué cambió respecto de la v2** (consejos de la devolución a la v2, que quedó aprobada):
> 1. **Conjunto de desarrollo separado del congelado** (§5 y Anexo D): 21 tareas `dev-*` que salen del mismo generador, sin repetir ninguna opción ni receta de las congeladas y con otras redacciones de la dieta y las porciones. El harness se ajusta solo mirando esas, y reportamos solo sobre las congeladas. En §4 contamos cómo detecta el harness la dieta y las porciones.
> 2. **6 tareas nuevas** (rec-016 a rec-021, Anexo A), al final para no cambiar los ids anteriores. **5 de las 18 respondibles caen fuera del esquema del camino fijo**: obligan a recorrer y comparar varias candidatas o a responder algo que el esquema no pide. Lo declaramos antes de medir (§6).
> 3. **Vencimientos:** 3 tareas en las que priorizar es parte de la respuesta (rec-005, rec-019, rec-020).
> 4. **Planificación y verificación apuntan ahora a fallas distintas** (§4). Anticipamos que los efectos pueden no sumarse.
> 5. Presupuesto rehecho para 21 tareas (§8).
>
> **Qué cambió de la v1 a la v2** (respuesta a la primera devolución):
> 1. Conjunto de evaluación definido: 15 tareas con respuesta cerrada calculada sobre los datos, entre ellas 3 imposibles (§5 y Anexo A). Sacamos las tareas abiertas, así que no hace falta un corrector de restricciones aparte.
> 2. Diez filas reales del dataset, crudas y procesadas, y la normalización de cantidades y unidades, con cada decisión registrada (§2, Anexos B y C). El dominio es viable con alcance acotado: 3.198 recetas con una unidad por ingrediente.
> 3. Prueba de factibilidad hecha en su versión mínima, a libro cerrado y con resultados pegados (§7).
> 4. Herramientas rediseñadas: son 4 y cada una hace una sola cosa. El inventario es estado de la sesión y el vencimiento lo calcula el harness (§3).
> 5. Agregamos la cota de ruido y rehicimos el presupuesto (§8).

## 1. Problema

Una persona que cocina en casa tiene en la heladera ingredientes con cantidades y fechas de vencimiento, cocina para un número dado de personas y a veces tiene restricciones (vegetariano, sin gluten…). Quiere saber qué receta concreta de un recetario puede hacer, qué le falta comprar y en qué cantidad. Un buscador de recetas no cruza el inventario con las cantidades escaladas a las porciones, y un modelo de 8B a libro cerrado inventa recetas y cantidades (§7). Lo que el agente agrega es una respuesta **verificable contra el corpus**: el id de la receta, los faltantes calculados y un "no se puede" honesto cuando los datos no alcanzan.

No pretendemos reemplazar recomendaciones médicas ni garantizar la ausencia de alérgenos.

## 2. Datos

**RecetasDeLaAbuela** (SomosNLP, hackathon 2024), Hugging Face `somosnlp/RecetasDeLaAbuela`, licencia OpenRAIL. Usamos el archivo `main.csv`, **fijado en el commit `c9879423aeb4b151fb8941f79098e9606d25c782`**, con 20.236 filas y 14 columnas. Un script baja el CSV en ese commit. El dataset que usa el agente es una versión derivada y normalizada, que guardamos versionada junto con el registro de cada decisión.

**Cómo vienen los ingredientes** (diez filas crudas y procesadas en el Anexo B). Son texto libre y el formato depende del sitio de origen:

- **recetasgratis.net** (18.187 filas, el 90%): una lista con una línea por ingrediente, generada con plantillas bastante regulares (`300 gramos de X`, `2 unidades de X`, `1 cucharada sopera de X`). **Es la única fuente que usamos**.
- **cookpad** (718): también viene como lista, pero el 87% de las filas tiene mojibake (`atÃºn`). **yanuq** (832) no tiene comensales ni duración en ninguna fila. **mexicoenmicocina y otros sitios chicos** (499): un string separado por comas, donde la coma también aparece dentro de un ingrediente. Entre todos aportarían unas 250 recetas útiles (+5%), y no justifican el costo.

`Valor nutricional` es una etiqueta cualitativa ("Alto en calorías…"): **no hay calorías numéricas**.

**Leer la cantidad es fácil. Compararla es difícil.** En recetasgratis el 94% de las líneas trae un número y solo 45 tienen rangos ("2 o 3"). El problema es que **el mismo ingrediente viene en unidades distintas según la receta**: la harina viene en gramos o en tazas, la cebolla en unidades o en gramos, el pollo en gramos, pechugas o piezas. Eso es lo que hay que resolver para escalar porciones y calcular faltantes.

**Lo resolvemos normalizando a una sola unidad por ingrediente.** Un script hace la normalización y registra cada decisión, línea por línea y regla por regla, para poder auditarla y rehacerla.

1. **Filtros.** Usamos solo recetasgratis, con comensales y duración, con al menos 3 líneas y con todas sus líneas reconocidas por el léxico. El léxico tiene unos 60 ingredientes canónicos, con sinónimos regionales (papa/patata, poroto/frijol/alubia, manteca/mantequilla) y etiquetas de dieta.
2. **Una unidad por ingrediente:** la más frecuente en el corpus (Anexo C). Por ejemplo, gramos para harina, pollo y arroz; unidades para cebolla, papa, tomate y huevo; mililitros para leche y caldo; dientes para el ajo. **No depende del inventario.**
3. **Conversiones en orden de confianza:**
   - exactas: kg, l y cc pasan a g o ml;
   - la cantidad métrica que la propia receta escribe entre paréntesis ("1 taza de harina (100 gr)");
   - una tabla de **126 equivalencias estándar** (Anexo C): taza = 240 ml, densidad de la harina 0,55 g/ml, una cebolla = 150 g, una pechuga = 200 g, una lata de atún = 120 g, y otras.
4. **Las equivalencias dudosas se revisan a mano.** De las primeras 118, marcamos 39 como `dudosa`: por ejemplo, el vaso de 200 ml, la densidad del queso (rallado o crema) y el peso de un zapallo (zapallito o calabaza). Las revisamos en una planilla con ejemplos reales de cada una y el grupo las aprobó en bloque con su valor sugerido. Después agregamos 8 equivalencias para las tortillas y las leches especiales, y 3 de ellas quedan `dudosa`: el peso de una tortilla de maíz y de una de harina, y el contenido de una lata de leche evaporada. Hasta que se revisen, las 28 recetas que las usan quedan apartadas, no descartadas.
5. **Lo que no es una cantidad se descarta:** pizca, chorro, puñado, gota, rangos y líneas sin número. Sal, pimienta, aceite, agua, condimentos secos y hierbas (perejil, cilantro, albahaca) son **básicos**: se suponen disponibles y no se cuentan.

**Resultado:**

| Paso | Recetas |
|---|---|
| recetasgratis.net | 18.187 |
| con comensales, duración y al menos 3 líneas | 12.473 |
| con todas las líneas reconocidas por el léxico (corpus base) | 5.197 |
| **dataset final** | **3.198** |

| Estado de las 5.197 recetas del corpus base | Recetas |
|---|---|
| Sin ningún problema: todas las cantidades ya venían en la unidad elegida | 772 (15%) |
| Corregidas: al menos una cantidad convertida con una equivalencia `ok` | 2.426 (47%) |
| Dudosas: apartadas hasta revisar 3 equivalencias nuevas | 28 (1%) |
| Descartadas: alguna línea sin cantidad convertible | 1.971 (38%) |

De las líneas no básicas, el 59% no necesitó ningún cambio, el 30% se corrigió y el 10% se descartó. Antes de aprobar las 39 dudosas, el dataset final tenía 2.195 recetas. La aprobación sumó 1.019, que dependían de alguna de ellas: el vaso de 200 ml sola destrababa 116; la densidad del maíz, 73; la del queso, 67; el peso del zapallo, 64.

**Qué significa esto para el agente.** Dentro del dataset final, todas las cantidades de un ingrediente están en la misma unidad, así que escalar porciones y comparar con el inventario es siempre posible. Pero **el 30% de las líneas es una aproximación** ("una cebolla ≈ 150 g"), y algunas de las aprobadas en bloque son gruesas: un vaso puede tener de 150 a 250 ml y "un zapallo" puede ser un zapallito o una calabaza. Las respuestas esperadas son exactas respecto de la tabla de equivalencias, no de la cocina real, y lo declaramos como limitación. Para no depender de eso, el conjunto de evaluación usa solo cantidades sin conversión en las respuestas numéricas, y exige que cada faltante se mantenga aunque una equivalencia se equivoque en ±30% (§5).

**Fallas encontradas y corregidas en el camino:**

- NFKD convertía `½` en `1⁄2`, que se leía como 1.
- "pasta de ajo" se leía como pasta (182 líneas).
- "consomé de pollo" convertía en "receta con pollo" a recetas que no lo llevan.
- La cebolla de verdeo se mezclaba con la cebolla.
- El parser leía "1 pizca", "1 rama" o "1 pechuga" como unidades sueltas.
- Las tortillas se leían como maíz o harina: "9 tortillas de maíz" daba 9 choclos de 200 g. Ahora la tortilla de maíz y la de harina son ingredientes propios.
- La leche condensada, la evaporada y la de coco se leían como leche, así que la leche de coco figuraba como lácteo. Ahora son tres ingredientes propios, y la de coco no es lácteo.

**Fallas conocidas que quedan:** "crema pastelera" se lee como crema de leche, y "mantequilla vegetal" como manteca, con la etiqueta de lácteo: `es_apta` puede negar por error que una receta sea vegana. Algunas equivalencias aprobadas en bloque son gruesas: "1 vaso pequeño" cuenta como 200 ml (54 recetas) y "2 piezas de calabaza" como dos zapallitos de 250 g (18 recetas). El script que genera las tareas no usa recetas con esas líneas. La muestra al azar del Anexo B mostró dos errores más del léxico: "3 cucharadas de Harina maíz" (sin "de") se lee como harina común, y "Edulcorante sin azúcar" se lee como azúcar. Ampliar el léxico unos 150 nombres llevaría el corpus base a unas 7.700 recetas; queda como alternativa, porque requiere revisión manual.

El **inventario** no sale del corpus. Es fijo para todas las tareas, se expresa en la unidad elegida para cada ingrediente y el harness lo carga como estado de la sesión.

## 3. Herramientas

El inventario es **estado de la sesión**. El harness lo muestra en el prompt de sistema ordenado por vencimiento y marca como *prioritarios* los productos que vencen en 3 días o menos (eso es código, no una herramienta). Ninguna herramienta recibe el inventario como argumento.

| Herramienta | Qué hace (una sola cosa) |
|---|---|
| `buscar_recetas(contiene: list[str], excluye: list[str] = [])` | Filtra por presencia de ingredientes canónicos. Devuelve el total y las primeras 10 recetas (`id`, `nombre`, `minutos`, `comensales`), ordenadas por duración y, si empatan, por id. Si un nombre no está en el léxico, devuelve un error con los nombres válidos más parecidos. |
| `detalle_receta(receta_id: int, porciones: int \| None)` | Devuelve los ingredientes de una receta: canónico, cantidad normalizada, unidad y línea original. Con `porciones`, escala las cantidades. |
| `es_apta(receta_id: int, dieta: "vegetariana" \| "vegana" \| "sin_gluten" \| "sin_lactosa")` | Devuelve `{apta, ingredientes_que_lo_impiden}`, según las etiquetas del léxico. |
| `faltantes(receta_id: int, porciones: int)` | Compara la receta escalada con el inventario de la sesión, en la unidad de cada ingrediente. Devuelve, por ingrediente, cuánto hace falta, cuánto hay y si alcanza. |
| `terminar(respuesta, motivo)` | La del kit. `respuesta = null` cuando los datos no alcanzan. |

**Qué sacamos y por qué:**

- `identificar_proximos_a_vencer` pasa a ser código del harness.
- `escalar_porciones` queda como parámetro de `detalle_receta`.
- `buscar_sustituciones` sale porque no hay una fuente de datos de sustituciones: la tabla la habríamos inventado nosotros.
- `buscar_recetas` pierde `priorizar`, `restricciones` y `limite`: solo filtra. Las restricciones de dieta se comprueban con `es_apta` sobre cada candidata, así que una tarea con dieta necesita **buscar → es_apta (una o más veces) → faltantes o detalle**.

**Encadenamiento:** 11 de las 21 tareas necesitan dos llamadas o más: 5 medias respondibles y las 6 difíciles. Las difíciles van de cuatro llamadas (buscar, `es_apta` dos veces y `faltantes`) a nueve (buscar y `faltantes` sobre ocho candidatas). En las tareas con dieta, la primera receta de la búsqueda nunca cumple la dieta: saltear `es_apta` da una respuesta equivocada. En las tareas que comparan candidatas (rec-016, rec-018 y rec-021), la respuesta nunca es la primera de la búsqueda. Ver la columna "cadena" del Anexo A.

## 4. Dos decisiones de agente que vamos a medir

Las dos decisiones apuntan a fallas distintas, para que cada una tenga dónde mostrarse. En la v2 las dos atacaban "saltear `es_apta`" (el plan porque lo incluye y la verificación porque lo exige). Además, lo que mostró la §7 (no cruzar con el inventario) ya lo resuelve `faltantes` en código, no la planificación.

1. **Planificación antes de usar herramientas** (plan-and-execute). Una primera llamada escribe el plan como lista de pasos: qué candidatas hay que recorrer, con qué criterio se comparan (menos faltantes, sin comprar nada, cuántas alcanzan, qué vence primero) y cuándo se puede parar. **Falla que esperamos arreglar: quedarse con la primera candidata de la búsqueda cuando la pregunta exige comparar varias.** En la §7, con tres recetas delante, el modelo no supo elegir una. Las 5 tareas fuera del esquema (rec-016, 017, 018, 020 y 021) están hechas para que esa falla dé una respuesta equivocada: en las de comparar, la respuesta nunca es la primera de la búsqueda. **Dónde lo medimos:** el acierto en esas 5 tareas y en las 3 difíciles con dieta.
2. **Verificación antes de `terminar`.** Un chequeo en código del harness, no del modelo, revisa:
   - que la receta citada exista en las trazas de esta corrida;
   - que haya pasado por `es_apta` si la pregunta pedía una dieta, y por `faltantes` o `detalle_receta` con las porciones de la pregunta;
   - que la respuesta no contenga ingredientes o cantidades que no aparecieron en ningún resultado de herramienta.

   Si algo falla, le devuelve al modelo qué faltó. **Fallas que esperamos arreglar:** saltear un filtro que la pregunta pedía (la dieta o las porciones), respuestas con cantidades inventadas y respuestas a tareas imposibles. **Dónde lo medimos:** el acierto en las tareas con dieta o porciones, y las respuestas inventadas en las 3 imposibles.

**Cómo detecta el harness la dieta y las porciones.** La verificación tiene que saber, leyendo la pregunta, si pide una dieta y para cuántas porciones. Lo hacemos con reglas en código, no con el modelo:

- **Dieta:** un diccionario de expresiones por dieta. Por ejemplo, para `vegetariana`: "vegetariana", "para vegetarianos", "sin carne ni pescado", "no lleva carne"; para `sin_gluten`: "sin gluten", "celíacos", "no lleva gluten"; para `sin_lactosa`: "sin lactosa", "sin lácteos", "intolerantes a la lactosa".
- **Porciones:** una expresión regular que busca un número, en cifras o en letras de dos a diez, delante de "personas", "comensales" o "porciones".

Las reglas se ajustan **solo con el conjunto de desarrollo**, que usa a propósito otras redacciones que las congeladas (Anexo D). Las congeladas dicen siempre "para N personas" y "es vegetariana / sin gluten / sin lactosa". Las de desarrollo dicen "para 6 comensales", "para diez personas", "apta para celíacos", "no lleva lácteos". En el informe vamos a publicar la lista final de expresiones y cuántas detecciones de las congeladas salieron bien. Si el detector falla en una congelada, lo reportamos y no lo corregimos.

**Los efectos pueden no sumarse.** Las dos decisiones siguen compartiendo una parte: un plan que incluye `es_apta` también evita saltearlo. Y la corrida conjunta es lo primero que recortamos (§8), que es justo donde se vería el solapamiento. Por eso no vamos a afirmar que planificación más verificación mejore lo que mejora cada una por separado. Si la corrida conjunta entra en el presupuesto, la reportamos tal como salga.

**No es circular.** La métrica compara la respuesta con la esperada del conjunto congelado, que un script de verificación calcula directo sobre el corpus normalizado, sin llamar a las herramientas ni al verificador del agente. Lo único que comparten es la capa de datos (léxico, parser y tabla de equivalencias), y eso lo declaramos.

Cada decisión se mide por separado contra el agente sin ella, con las mismas 21 tareas congeladas.

## 5. Conjunto de evaluación

Son 21 tareas congeladas con exactamente el formato de las tareas públicas del Mundial del kit: las 15 de la v2 (rec-001 a rec-015, sin cambios) y 6 agregadas después de la devolución (rec-016 a rec-021). Todas usan el mismo inventario fijo, expresado en la unidad elegida para cada ingrediente, que el harness carga como estado de la sesión:

| Ingrediente | Cantidad | Vence en |
|---|---|---|
| pollo | 500 g | **2 días** |
| tomate | 3 unidades | **3 días** |
| leche | 1000 ml | 5 días |
| zanahoria | 3 unidades | 6 días |
| cebolla | 2 unidades | 10 días |
| huevo | 6 unidades | 12 días |
| papa | 5 unidades | 15 días |
| arroz | 1000 g | 60 días |
| harina | 1000 g | 90 días |
| lenteja | 500 g | 90 días |

- **Dificultad:** 7 fáciles (6 respondibles y 1 imposible), 8 medias (6 respondibles y 2 imposibles) y 6 difíciles (de 4 a 9 llamadas encadenadas).
- **Fuera del esquema del camino fijo (5 de 18 respondibles):** rec-016 (la que deja menos por comprar entre 6 candidatas), rec-017 (para cuántas personas alcanzan los huevos), rec-018 (la más rápida que se hace sin comprar nada), rec-020 (qué ingrediente de la receta vence primero) y rec-021 (cuántas candidatas se hacen con el pollo que hay). El criterio está en §6.
- **Vencimientos (3 tareas):** en rec-005 y rec-019 hay que traducir "lo que vence primero" o "los dos que vencen antes" en ingredientes concretos (pollo y tomate), y en rec-020 la respuesta es justamente cuál vence primero. En rec-021 el vencimiento aparece en la pregunta pero no hace falta para responder, así que no la contamos.
- **Conjunto de desarrollo (Anexo D):** 21 tareas `dev-*` del mismo generador, con las mismas plantillas y la misma mezcla (18 respondibles, 5 fuera del esquema, 3 con vencimientos). El generador comprueba que no repitan ninguna combinación de plantilla e ingredientes ni ninguna receta de respuesta de las congeladas. Sobre ellas ajustamos los prompts, el detector de dieta y porciones y el verificador. Las congeladas las corremos recién para medir.
- **Imposibles (3), pero verosímiles:** calorías por porción (no están en los datos), una combinación de ingredientes sin ninguna receta en el corpus (verificado: 0) y el costo de los faltantes (no hay precios).
- **Respuestas cerradas:** `numero`, `texto` (el nombre de la receta) o `lista` (los ingredientes canónicos que faltan). Cuando la pregunta pide "la más rápida", la receta correcta es única por construcción: el script que genera las tareas comprueba que no empate en duración con otra que cumpla lo pedido, así que la respuesta no depende del desempate. Para las respuestas de tipo `lista`, el evaluador compara conjuntos después de normalizar con el mismo léxico, de modo que "lentejas" y "lenteja" cuentan igual.
- **Robustas a las aproximaciones:** las respuestas numéricas salen de líneas sin conversión. Cuando un faltante depende de una cantidad convertida, el generador exige que la conclusión se mantenga aunque la equivalencia se equivoque en ±30%. Por ejemplo, una versión anterior de una tarea pedía "pizza keto de pollo para 6 personas", y que faltara pollo dependía de que una pechuga pesara 200 g. El generador la rechazó.

El detalle completo de las tareas está en el Anexo A.

## 6. Líneas de base

- **Libro cerrado:** `qwen3:8b` sin herramientas, con las 21 tareas y su formato de respuesta. En la §7 inventó recetas y cantidades y no dijo de dónde salían. Esperamos que acierte casi nada en las tareas que piden un id o un nombre del corpus, y que conteste las imposibles con valores inventados.
- **Camino fijo:** una sola llamada al modelo con salida restringida a un esquema JSON (`contiene`, `excluye`, `dieta`, `porciones`, `que_pide`) y después un pipeline sin loop: `buscar_recetas` → `es_apta` sobre las candidatas en orden → `faltantes` o `detalle_receta` → una respuesta armada por plantilla. Esperamos que resuelva bien las fáciles y medias bien formadas, y que falle cuando la pregunta no encaja en el esquema y en las imposibles, porque el pipeline siempre devuelve algo.

  **Probablemente gane en las tareas que entran en el esquema**, y lo vamos a reportar así: un pipeline que recorre las candidatas con `es_apta` en un bucle resuelve las plantillas "la más rápida que lleva X e Y y es Z" sin necesidad de un agente. Por eso declaramos **antes de medir** qué tareas caen fuera:
  - **Criterio:** una tarea está dentro del esquema si se resuelve con `buscar_recetas(contiene, excluye)` → la primera candidata apta para la dieta → `detalle_receta` o `faltantes` con las porciones → un dato de ese resultado.
  - **Dentro (13):** rec-001 a rec-012 y rec-019. En rec-005 y rec-019 suponemos que el modelo del esquema, que ve el inventario, traduce "lo que vence primero" en el ingrediente.
  - **Fuera (5):** rec-016, rec-017, rec-018, rec-020 y rec-021.
  - **Imposibles (3):** se cuentan aparte.

  Reportamos el acierto de cada configuración por separado en los dos grupos. La pregunta interesante es si el agente gana fuera del esquema sin perder dentro.

## 7. Prueba de factibilidad (versión mínima: libro cerrado y resultado pegado)

Todavía no tenemos el loop del Bloque 1, así que hicimos la versión mínima que propuso la devolución. Corrimos las cinco tareas de la v1 con `qwen3:8b` sin herramientas. En las tareas 2 y 3 repetimos la pregunta pegando en el prompt el resultado real de `buscar_recetas` y de `detalle_receta` sobre el corpus, tal como lo devolvería una herramienta. Usamos temperatura 0, semilla 1337, `think` apagado, `num_ctx` 8192 y `num_predict` 800. La corrida fue local en CPU, sin GPU, con Ollama 0.40.16. Guardamos las trazas con el esquema del kit y las respuestas completas.

| Tarea | Variante | ¿Herramientas o memoria? | Herramientas y llamadas | ¿La resolvió? | Error o rareza observada |
|---|---|---|---|---|---|
| 1. Huevos, cebolla, papa, 2 personas | Libro cerrado | Memoria | Ninguna; 1 llamada (74 + 393 tokens, 76 s) | No es verificable | Inventa la receta "huevos fritos con papas y cebolla", con cantidades propias y sin fuente. La pregunta no tiene respuesta cerrada, por eso la sacamos del conjunto. |
| 2. Arroz, tomate, lentejas: qué falta | Libro cerrado | Memoria | Ninguna; 1 llamada (82 + 463) | No | Inventa la receta. Como "faltantes" lista sal y aceite (básicos) y opcionales ("perejil, opcional"): no hay un criterio de qué cuenta como faltante. |
| 2. (ídem) | Resultado pegado | Usa los datos pegados | `buscar_recetas` + 3 × `detalle_receta` pegados; 1 llamada (699 + 312) | A medias | Cita los ids y copia bien las líneas de los ingredientes. **No elige una receta** (pedimos "una" y devuelve las tres). En la receta 9131 dice que **falta tomate, que el usuario sí tiene**: no cruzó la línea "3 unidades de tomate" con el inventario. |
| 3. Pollo que vence, 4 personas, ajustar cantidades | Libro cerrado | Memoria | Ninguna; 1 llamada (111 + **800**, cortada por `num_predict`) | No | Respuesta muy larga, cortada por el tope de salida: Ollama informa `done_reason = "length"` con exactamente 800 tokens (= `num_predict`). La última línea queda sin punto final. Pide "1 pollo entero (1,5 kg)" sin saber cuánto pollo hay. Malinterpreta el vencimiento ("si el pollo se cocina en 2 días…"). |
| 3. (ídem) | Resultado pegado | Usa los datos pegados | `buscar_recetas` + 3 × `detalle_receta` pegados; 1 llamada (734 + 210) | Sí, de casualidad | Elige 7507, "ensaladilla rusa con pollo", la única de las tres que de verdad lleva pollo como ingrediente. Descarta bien la 17750, que entró a la búsqueda por "caldo de pollo". Pero la receta ya era para 4 comensales y copió las cantidades sin escalar, así que el escalado **no quedó probado**. No dice qué le falta (mayonesa, arvejas, morrón, ajo). |
| 4. Sin manteca, sustitución | Libro cerrado | Memoria | Ninguna; 1 llamada (87 + 632) | No | Propone una "tarta de huevo" inventada. Entre las sustituciones de la manteca sugiere "mantequilla sin grasa", que es lo mismo que manteca. Es una de las razones por las que sacamos `buscar_sustituciones`. |
| 5. Vegetariana, sin huevo, 3 personas, priorizar vencimientos | Libro cerrado | Memoria | Ninguna; 1 llamada (101 + 764) | No | Inventa una "sopa de arroz con tomate y cebolla". La pregunta no da fechas de vencimiento y el modelo **no lo dice**: contesta "usá la que esté más próxima a vencer". Esto debería haber sido un "los datos no alcanzan". |

**Lo que más nos llamó la atención:**

1. **A libro cerrado, el modelo nunca dice "no sé".** Las 5 respuestas son recetas plausibles e inventadas, sin ids ni fuente, y la tarea 5 contesta sobre vencimientos que no le dimos. Esto confirma la apuesta por las tareas imposibles y por la verificación antes de `terminar`.
2. **Con los datos delante, los usa: cita ids y copia bien las líneas, pero no razona sobre ellos.** Elige bien entre candidatas cuando la diferencia está en el nombre de la receta (tarea 3). Falla cuando tiene que cruzar con el inventario: dijo que faltaba el tomate que el usuario tenía. Por eso `faltantes` calcula el cruce en código y el modelo solo lo lee.
3. **La búsqueda por subcadena trae falsos positivos que el modelo no siempre ve.** "Caldo de pollo" convertía una crema de zanahorias en "receta con pollo". Esta vez el modelo la descartó, pero no lo queremos dejar librado a eso: se corrige en el léxico, dando prioridad a las formas largas.
4. **Las respuestas a libro cerrado son largas** (400–800 tokens; la de la tarea 3 llegó al tope de 800 y el servidor la cortó). Con `terminar` y un formato de respuesta cerrado, esto cambia. Para el presupuesto lo que pesa es el contexto: con resultados pegados el prompt pasa de unos 80 a unos 700 tokens con solo 3 recetas, así que los resultados de las herramientas tienen que ser compactos (máximo 10 filas y solo los campos necesarios).
5. **Lo que no pudimos ver sin el loop:** si el modelo llama a las herramientas por su cuenta y si encadena las tres (`buscar → es_apta → faltantes`). Es lo primero que vamos a probar cuando el loop del Bloque 1 esté andando, con las difíciles del conjunto de desarrollo (dev-010 a dev-012, dev-016, dev-018 y dev-021), no con las congeladas.

## 8. Presupuesto, cota de ruido y plan

**Cota de ruido.** Con temperatura 0 la semilla no cambia nada, así que vamos a variar la temperatura y declararlo. Cada configuración se corre con **temperatura 0,7 y 3 semillas** (1337, 1338, 1339). Reportamos la media y el rango de aciertos, y una diferencia entre configuraciones cuenta solo si supera ese rango. Las comparaciones a temperatura 0 se reportan aparte, como corrida de referencia.

**Llamadas por tarea, rehechas con lo que vimos:** la prueba muestra que el modelo necesita ver el detalle de cada candidata para decidir, y que las cadenas difíciles son de 3 a 5 herramientas.

Las tareas que comparan candidatas (rec-016, rec-018 y rec-021) llevan de 7 a 9 herramientas, y suben el promedio.

| Configuración | Llamadas por tarea (estimadas) | × 21 tareas × 3 semillas |
|---|---|---|
| Libro cerrado | 1 | 63 |
| Camino fijo | 1 (más herramientas sin modelo) | 63 |
| Agente base | ~6 (3 a 9 herramientas, `terminar` y un reintento) | ~380 |
| + planificación | ~7 | ~440 |
| + verificación | ~8 (una vuelta extra cuando el chequeo falla) | ~505 |
| **Total congelado** | | **~1.450 llamadas** |
| Desarrollo (21 tareas `dev-*`, una semilla, varias vueltas de ajuste) | | ~400 |

Tokens: con los resultados pegados, el prompt de la prueba pasó de unos 80 a unos 1.500–2.000 tokens. Estimamos un promedio de unos 3.000 tokens de entrada por llamada del agente, o sea unos 5,5 millones de tokens en total, contando el desarrollo. En CPU local cada llamada tardó de 1 a 3 minutos, así que **todas las mediciones de tiempo van en la T4 de Colab** y la máquina local queda para desarrollo.

**Qué recortamos primero, en orden:**

1. La corrida conjunta de planificación con verificación. Si se recorta, no podemos decir nada sobre si los efectos se suman (§4) y lo decimos así en el informe.
2. Bajar de 3 a 2 semillas.
3. `sin_lactosa` y `sin_gluten` (queda solo `vegetariana`/`vegana`).

No se recortan las dos comparaciones principales, las tareas imposibles, las 5 tareas fuera del esquema ni la cota de ruido. El conjunto de desarrollo tampoco se corre contra las congeladas para ahorrar.

## 9. Afirmación tentativa

Con la verificación en código antes de `terminar`, el agente baja las respuestas inventadas (en las 3 imposibles y en las tareas donde cita cantidades) y los filtros salteados (dieta o porciones) frente al agente sin verificación, sin perder aciertos en las respondibles. Con la planificación, sube el acierto en las 5 tareas fuera del esquema, las que obligan a recorrer y comparar candidatas.

Esperamos que el camino fijo empate o gane al agente en las 13 tareas dentro del esquema. Lo que el agente tiene que mostrar es una ventaja en las 5 de afuera. Las dos mejoras se miden contra el agente base y las dos líneas de base, solo sobre las 21 tareas congeladas, y cuentan solo si superan la cota de ruido de las 3 semillas. La afirmación queda refutada si alguna de las dos diferencias no supera esa cota. No afirmamos nada sobre la combinación de las dos (§4).

---

## Anexo A: las 21 tareas congeladas, con su respuesta calculada

Respuestas calculadas con código sobre el dataset final. Inventario: el de la §5. La nota dice de qué receta, y cuando hace falta de qué línea, sale cada respuesta. Fuera del esquema del camino fijo (§6): rec-016, 017, 018, 020 y 021. Usan el vencimiento: rec-005, 019 y 020.

| id | Pregunta | Respuesta | Tipo | Dif. | Cadena esperada | Nota (de dónde sale) |
|---|---|---|---|---|---|---|
| rec-001 | ¿Cuántas recetas del corpus llevan lentejas? | 33 | numero | facil | buscar_recetas |  |
| rec-002 | ¿Cuál es la receta más rápida que lleva papa y huevo? | patatas a lo pobre con huevo frito | texto | facil | buscar_recetas | id 18611, 10 min |
| rec-003 | ¿La receta 7533 es apta para veganos? Respondé sí o no. | sí | texto | facil | es_apta | ensalada de lentejas con pimientos: ['aceite', 'ajo', 'cebolla', 'condimento', 'lenteja', 'morron', 'sal'] |
| rec-004 | ¿Cuántos gramos de arroz lleva la receta 3628 si la hago para 6 personas? | 300 | numero | facil | detalle_receta | arroz thai con verduras y pollo, 2 comensales, línea: 100 gramos de Arroz blanco cocido |
| rec-005 | ¿Cuál es la receta más rápida que lleva leche y el ingrediente de mi inventario que vence primero? | salchichas con crema de queso | texto | facil | buscar_recetas | vence primero: pollo (lo marca el harness en el prompt); id 6029 |
| rec-006 | ¿Cuál es la receta más rápida que lleva huevo y pasta y es sin lactosa? | sopa de fideos con huevo | texto | media | buscar_recetas → es_apta → es_apta → es_apta → es_apta → es_apta → es_apta | id 17022; posición 6 en la búsqueda; la primera (10857 spaghetti carbonara con nata) no es sin lactosa |
| rec-007 | ¿Cuál es la receta más rápida que lleva papa y harina y es vegetariana? | gofres de patata | texto | media | buscar_recetas → es_apta → es_apta | id 8142; posición 2 en la búsqueda; la primera (2319 croquetas de patata y jamon) no es vegetariana |
| rec-008 | Para la receta más rápida que lleva pollo y morrón y no lleva cebolla, ¿cuántos gramos de pollo necesito para 6 personas? | 150 | numero | media | buscar_recetas → detalle_receta | id 4052, 4 comensales, línea: 100 gramos de Pechuga de pollo |
| rec-009 | Si hago para 10 personas la receta más rápida que lleva papa y huevo, ¿cuántos huevos me faltan con lo que tengo? | 14 | numero | media | buscar_recetas → faltantes | id 18611, 1 comensales, línea: 2 Huevos; necesita 20 |
| rec-010 | De las recetas con arroz y tomate, tomá la más rápida que sea vegetariana: ¿qué me falta comprar para hacerla para 4 personas? | `["ajo", "banana", "cebolla", "tomate"]` | lista | dificil | buscar_recetas → es_apta → es_apta → faltantes | id 4281 arroz a la cubana con platano; posición 2 en la búsqueda |
| rec-011 | De las recetas con tomate y queso, tomá la más rápida que sea vegetariana: ¿qué me falta comprar para hacerla para 4 personas? | `["espinaca", "queso"]` | lista | dificil | buscar_recetas → es_apta → es_apta → faltantes | id 8826 revuelto de espinacas con tomate y queso; posición 2 en la búsqueda |
| rec-012 | No tengo manteca. De las recetas vegetarianas con zanahoria y queso que no llevan manteca, tomá la más rápida: ¿cuántos ingredientes me faltan comprar para hacerla para 8 personas? | 5 | numero | dificil | buscar_recetas → es_apta → es_apta → faltantes | id 10788 espaguetis integrales con zanahoria: faltan ['arveja', 'maiz', 'pasta', 'queso', 'zanahoria'] |
| rec-013 | ¿Cuántas calorías por porción tiene la receta 7533? | `null` (imposible) | numero | facil | detalle_receta | el corpus no tiene calorías numéricas |
| rec-014 | Tengo lentejas, frutillas y pescado y quiero usar los tres: ¿cuál es la receta más rápida que los lleve? | `null` (imposible) | texto | media | buscar_recetas | 0 recetas los llevan a los tres |
| rec-015 | ¿Cuánto me cuesta comprar lo que me falta para hacer la receta 7533 para 4 personas? | `null` (imposible) | numero | media | faltantes | el corpus no tiene precios |
| rec-016 | De las recetas con pollo y vino, ¿cuál me deja menos ingredientes por comprar para hacerla para 4 personas? | arroz con pollo y champinones en arrocera | texto | dificil | buscar_recetas → faltantes ×6 | id 4053; posición 5 de 6; faltan ['champinon', 'vino']; cantidad de faltantes por candidata: [3, 3, 5, 5, 2, 3] |
| rec-017 | ¿Para cuántas personas como máximo me alcanzan los huevos que tengo si hago la receta 8185? | 6 | numero | media | detalle_receta | tortilla de harina y huevo, 4 comensales, línea: 4 Huevos; hay 6 huevos |
| rec-018 | De las recetas con papa y huevo, ¿cuál es la más rápida que puedo hacer para 2 personas sin comprar nada? | revuelto de patatas con thermomix | texto | dificil | buscar_recetas → faltantes ×8 | id 8441; posición 8 en la búsqueda; las anteriores necesitan comprar algo |
| rec-019 | Quiero usar los dos ingredientes de mi heladera que vencen antes, junto con pasta. ¿Cuál es la receta más rápida que lleva los tres? | espaguetis con pollo y brocoli | texto | facil | buscar_recetas | vencen antes: ['pollo', 'tomate'] (lo marca el harness en el prompt); id 11650 |
| rec-020 | Para la receta más rápida que lleva lentejas y zanahoria: de los ingredientes que usa y tengo en la heladera, ¿cuál vence primero? | tomate | texto | media | buscar_recetas → detalle_receta | id 7604 ensalada de lentejas con langostinos; del inventario usa [('tomate', 3), ('zanahoria', 6), ('cebolla', 10), ('lenteja', 90)] |
| rec-021 | El pollo me vence en 2 días y no quiero comprar más. De las recetas con pollo y palta, ¿cuántas puedo hacer para 8 personas con el pollo que tengo? | 2 | numero | dificil | buscar_recetas → faltantes ×7 | 7 candidatas; alcanzan [1586, 7633]; gramos de pollo por candidata: [2400, 1000, 288, 800, 200, 1012, 800] (hay 500) |

## Anexo B: diez filas reales, crudas y procesadas

### B.1. Diez filas crudas de recetasgratis.net

Tal como vienen en el CSV (columnas `Id`, `Nombre`, `Comensales`, `Duracion` e `Ingredientes`; se omiten `URL`, `Pasos`, `Contexto` y el resto). Elegidas al azar, con semilla fija, entre las recetas del dataset final: las 4 primeras no necesitaron ningún cambio y las 6 siguientes se corrigieron.

| Id | Nombre | Comensales | Duracion | Ingredientes |
|---|---|---|---|---|
| 5627 | lomo estofado al vino | `3 comensales` | `00:30` | `['½ kilogramo de Lomo de cerdo', '1 kilogramo de Champiñones', '½ litro de Vino tinto', '100 gramos de Mantequilla', '¼ litro de Aceite', '1 diente de Ajo', '1 pizca de Sal', 'Pimienta al gusto']` |
| 12585 | nuggets de atun | `2 comensales` | `00:15` | `['150 gramos de Atún de lata', '100 gramos de Pan rallado', '120 gramos de Queso crema', '5 unidades de Huevo']` |
| 16643 | mayonesa casera | `1 comensal` | `00:10` | `['1 Huevo', '200 mililitros de Aceite de girasol', '1 chorro de Vinagre o Zumo de limón', '1 pizca de Sal']` |
| 16755 | salsa raita | `1 comensal` | `00:15` | `['¼ unidad de Cebolla', '½ unidad de Pepino', '1 unidad de Tomate', '1 pizca de Comino en polvo', '1 pizca de Chat masala o Sal negra', '1 pizca de Sal', '150 gramos de Yogur natural']` |
| 14137 | crema pastelera basica | `2 comensales` | `00:45` | `['4 unidades de Yemas de huevo', '100 gramos de Azúcar                                                                    (½ taza)', '50 gramos de Harina', '2 cucharadas soperas de Maicena', '½ litro de Leche', '1 rama de Canela']` |
| 18019 | pimiento relleno de carne molida | `4 comensales` | `00:45` | `['4 piezas de Pimiento morrón', '400 gramos de Carne molida de res', '2 Zanahorias', '200 gramos de Chícharos', '1 Papa grande', '¼ Cebolla', '1 diente de Ajo', '1 pizca de Sal', '1 pizca de Pimienta', '2 cucharadas soperas de Aceite']` |
| 19278 | tortilla de acelgas vegana | `2 comensales` | `00:15` | `['200 gramos de Hojas acelga', '4 cucharadas soperas de Harina trigo', '3 cucharadas soperas de Harina maíz', '½ sobre de Levadura', '1 vaso de Agua', '1 chorro de Vinagre de vino', '1 chorro de Aceite de oliva', '1 pizca de Sal', '1 pizca de Pimienta negra']` |
| 3591 | porridge de avena y platano | `1 comensal` | `00:10` | `['4 cucharadas soperas de avena', '½ taza de agua                                                                    (120 mililitros)', '4 cucharadas soperas de leche descremada o bebida vegetal', '1 plátano chico', '1 pizca de canela']` |
| 18184 | pastel de patata con bacon y queso | `2 comensales` | `01:00` | `['500 gramos de Patata', '100 gramos de Bacon ahumado', '200 mililitros de Nata', '1 unidad de Huevo', '1 pizca de Sal', '120 gramos de Queso en lonchas', '80 gramos de Queso rallado']` |
| 6970 | batido de manzanas y frutillas bajo en calorias | `1 comensal` | `00:10` | `['1 litro de Leche sin lactosa', '500 gramos de Fresa o Frutilla', '2 Manzanas verdes', '1 cucharadita de Edulcorante sin azúcar']` |

### B.2. Las mismas diez filas después de la normalización

Cada ingrediente queda con su nombre canónico, su cantidad y la unidad elegida para ese ingrediente. Los básicos (sal, pimienta, aceite, agua, condimentos, hierbas) quedan sin cantidad. Las cantidades marcadas con * son conversiones; la última columna dice de qué línea salen y con qué equivalencia.

| Id | Comensales | Minutos | Ingredientes normalizados | Conversiones aplicadas | Estado |
|---|---|---|---|---|---|
| 5627 | 3 | 30 | cerdo 500 g · champinon 1000 g · vino 500 ml · manteca 100 g · aceite (básico) · ajo 1 diente · sal (básico) · pimienta (básico) | — | sin cambios |
| 12585 | 2 | 15 | pescado 150 g · pan 100 g · queso 120 g · huevo 5 unidad | — | sin cambios |
| 16643 | 1 | 10 | huevo 1 unidad · aceite (básico) · condimento (básico) · sal (básico) | — | sin cambios |
| 16755 | 1 | 15 | cebolla 0,25 unidad · pepino 0,5 unidad · tomate 1 unidad · condimento (básico) · sal (básico) · sal (básico) · yogur 150 g | — | sin cambios |
| 14137 | 2 | 45 | huevo 4 unidad · azucar 100 g · harina 50 g · maiz 21 g* · leche 500 ml · condimento (básico) | «2 cucharadas soperas de Maicena» → 21 g (1 cucharada = 15 ml; maiz: 0,7 g por ml) | corregida |
| 18019 | 4 | 45 | morron 4 unidad* · carne vacuna 400 g · zanahoria 2 unidad · arveja 200 g · papa 1 unidad · cebolla 0,25 unidad · ajo 1 diente · sal (básico) · pimienta (básico) · aceite (básico) | «4 piezas de Pimiento morrón» → 4 unidad (1 pieza = 1 unidad) | corregida |
| 19278 | 2 | 15 | espinaca 200 g · harina 33 g* · harina 24,75 g* · levadura 3,89 ml* · agua (básico) · condimento (básico) · aceite (básico) · sal (básico) · pimienta (básico) | «4 cucharadas soperas de Harina trigo» → 33 g (1 cucharada = 15 ml; harina: 0,55 g por ml)<br>«3 cucharadas soperas de Harina maíz» → 24,75 g (1 cucharada = 15 ml; harina: 0,55 g por ml)<br>«½ sobre de Levadura» → 3,89 ml (levadura: 1 sobre = 7 g; levadura: 0,9 g por ml) | corregida |
| 3591 | 1 | 10 | avena 60 ml* · agua (básico) · leche 60 ml* · banana 1 unidad · condimento (básico) | «4 cucharadas soperas de avena» → 60 ml (1 cucharada = 15 ml)<br>«4 cucharadas soperas de leche descremada o bebida vegetal» → 60 ml (1 cucharada = 15 ml) | corregida |
| 18184 | 2 | 60 | papa 2,5 unidad* · cerdo 100 g · crema de leche 200 ml · huevo 1 unidad · sal (básico) · queso 120 g · queso 80 g | «500 gramos de Patata» → 2,5 unidad (papa: 1 unidad = 200 g) | corregida |
| 6970 | 1 | 10 | leche 1000 ml · frutilla 500 g · manzana 2 unidad · azucar 4,25 g* | «1 cucharadita de Edulcorante sin azúcar» → 4,25 g (1 cucharadita = 5 ml; azucar: 0,85 g por ml) | corregida |

Los nombres canónicos van sin tildes (`champinon`, `azucar`). Dos errores del léxico se ven en esta muestra: en la 19278, «3 cucharadas soperas de Harina maíz» quedó como harina de trigo, y en la 6970, «Edulcorante sin azúcar» quedó como azúcar. Están entre las fallas conocidas de la §2.

## Anexo C: unidades y equivalencias

**Unidad elegida para los ingredientes del inventario** (la más frecuente en el corpus). La última columna dice qué parte de sus líneas ya venía en esa unidad o se lleva a ella con una conversión fija:

| Ingrediente | Unidad | Líneas | En esa unidad |
|---|---|---|---|
| pollo | g | 240 | 65% |
| tomate | unidad | 966 | 78% |
| leche | ml | 1082 | 88% |
| zanahoria | unidad | 455 | 84% |
| cebolla | unidad | 2043 | 85% |
| huevo | unidad | 2013 | 99% |
| papa | unidad | 700 | 70% |
| arroz | g | 289 | 58% |
| harina | g | 1371 | 70% |
| lenteja | g | 69 | 78% |

**Las 126 equivalencias**: 9 universales (valen para cualquier ingrediente), 48 densidades (gramos por mililitro), 30 pesos por unidad y 39 unidades propias de un ingrediente. Todas son valores estándar de cocina, aproximados. Las universales y una muestra del resto:

| Tipo | Equivalencia | Estado |
|---|---|---|
| universal | 1 taza = 240 ml | ok |
| universal | 1 cucharada = 15 ml | ok |
| universal | 1 cucharadita = 5 ml | ok |
| universal | 1 vaso = 200 ml | revisada: aprobada |
| universal | 1 copa = 150 ml | revisada: aprobada |
| universal | 1 cubilete = 100 ml | revisada: aprobada |
| universal | 1 libra = 453,6 g | ok |
| universal | 1 onza = 28,35 g | ok |
| universal | 1 pieza = 1 unidad | ok |
| densidad | harina: 0,55 g por ml | ok |
| densidad | azucar: 0,85 g por ml | ok |
| densidad | queso: 0,45 g por ml | revisada: aprobada |
| densidad | leche: 1,03 g por ml | ok |
| densidad | arroz: 0,85 g por ml | ok |
| peso por unidad | cebolla: 1 unidad = 150 g | ok |
| peso por unidad | papa: 1 unidad = 200 g | ok |
| peso por unidad | tomate: 1 unidad = 120 g | ok |
| peso por unidad | zanahoria: 1 unidad = 80 g | ok |
| peso por unidad | zapallo: 1 unidad = 250 g | revisada: aprobada |
| peso por unidad | huevo: 1 unidad = 55 g | ok |
| especial | pollo: 1 pechuga = 200 g | ok |
| especial | pescado: 1 lata = 120 g | ok |
| especial | caldo: 1 pastilla = 500 ml | ok |
| especial | pasta: 1 paquete = 500 g | ok |
| especial | limón: 1 limón rinde 30 ml de jugo | ok |
| especial | leche condensada: 1 lata = 397 g | ok |

**Pendientes de revisión (3):** tortilla de maiz: 1 unidad = 30 g (tortilla de maíz mediana ≈ 30 g; las de taco son más chicas); tortilla de harina: 1 unidad = 45 g (tortilla de harina mediana ≈ 45 g; las de burrito, más); leche evaporada: 1 lata = 410 ml (latas de 315 a 410 g según la marca).

## Anexo D: conjunto de desarrollo

Lo genera el mismo script que las congeladas (`factibilidad/borrador_respuestas.py`) y está en `tareas/recetas_dev.json`. Sirve para ajustar los prompts, el detector de dieta y porciones y el verificador. **No se reporta.**

- **Disjunto del congelado.** Cada tarea congelada registra su plantilla, los ingredientes con que se armó y la receta de la respuesta. Las de desarrollo no pueden repetir ninguna de esas combinaciones ni ninguna de esas recetas, y el script falla si pasa. Las opciones extra que necesita el desarrollo se prueban solo ahí y van después de las originales, así que agregarlas no cambia las congeladas.
- **Otras redacciones.** Para la dieta y las porciones rotamos formas equivalentes de decir lo mismo:
  - porciones: "para N comensales", "para N porciones", "para seis personas" (el número en letras);
  - dietas: "no lleva carne ni pescado", "apta para vegetarianos", "apta para celíacos", "no lleva gluten", "no lleva lácteos", "apta para intolerantes a la lactosa".

  La respuesta esperada no cambia, porque solo cambia la forma de la pregunta.
- **Otras respuestas en las fáciles:** dev-003 se responde "no" (rec-003 se responde "sí") y las tres imposibles son distintas (proteínas, arroz con frutillas y cerdo, en qué supermercado comprar).

| id | Pregunta | Respuesta | Dif. | ¿En el esquema? | Vencimiento |
|---|---|---|---|---|---|
| dev-001 | ¿Cuántas recetas del corpus llevan espinaca? | 88 | facil | sí |  |
| dev-002 | ¿Cuál es la receta más rápida que lleva huevo y maíz? | crema pastelera al microondas | facil | sí |  |
| dev-003 | ¿La receta 2176 es apta para veganos? Respondé sí o no. | no | facil | sí |  |
| dev-004 | ¿Cuántos gramos de arroz lleva la receta 4057 si la hago para 6 comensales? | 480 | facil | sí |  |
| dev-005 | ¿Cuál es la receta más rápida que lleva huevo y el ingrediente de mi inventario que vence primero? | pizza keto de pollo | facil | sí | sí |
| dev-006 | ¿Cuál es la receta más rápida que lleva queso y morrón y no lleva carne ni pescado? | ensalada de pimientos con queso | media | sí |  |
| dev-007 | ¿Cuál es la receta más rápida que lleva huevo y vino y es apta para vegetarianos? | empanada de verduras facil | media | sí |  |
| dev-008 | Para la receta más rápida que lleva pollo y limón y no lleva queso, ¿cuántos gramos de pollo necesito para 6 porciones? | 1200 | media | sí |  |
| dev-009 | Si hago para diez personas la receta más rápida que lleva vino y huevo, ¿cuántos huevos me faltan con lo que tengo? | 4 | media | sí |  |
| dev-010 | De las recetas con queso y morrón que no llevan huevo, tomá la más rápida que sea apta para celíacos: ¿qué me falta comprar para hacerla para 4 personas? | `["cerdo", "chorizo", "morron", "queso"]` | dificil | sí |  |
| dev-011 | De las recetas con tomate y leche que no llevan huevo, tomá la más rápida que no lleve gluten: ¿qué me falta comprar para hacerla para 4 comensales? | `["caldo", "crema de leche", "tomate", "vino"]` | dificil | sí |  |
| dev-012 | No tengo manteca. De las recetas sin carne ni pescado con huevo y pan que no llevan manteca, tomá la más rápida: ¿cuántos ingredientes me faltan comprar para hacerla para 8 porciones? | 2 | dificil | sí |  |
| dev-013 | ¿Cuántos gramos de proteína tiene una porción de la receta 7105? | `null` (imposible) | facil | — |  |
| dev-014 | Quiero una receta que lleve arroz, frutillas y cerdo a la vez: ¿cuál es la más rápida? | `null` (imposible) | media | — |  |
| dev-015 | ¿En qué supermercado me conviene comprar lo que me falta para la receta 7105 para dos personas? | `null` (imposible) | media | — |  |
| dev-016 | De las recetas con pollo y maíz, ¿cuál me deja menos ingredientes por comprar para hacerla para 2 personas? | empanadas de pollo colombianas | dificil | **no** |  |
| dev-017 | ¿Para cuántas personas como máximo me alcanzan los huevos que tengo si hago la receta 8630? | 12 | media | **no** |  |
| dev-018 | De las recetas con huevo y leche, ¿cuál es la más rápida que puedo hacer para 2 comensales sin comprar nada? | huevos fritos esponjosos | dificil | **no** |  |
| dev-019 | Quiero usar los dos ingredientes de mi heladera que vencen antes, junto con caldo. ¿Cuál es la receta más rápida que lleva los tres? | enchiladas mexicanas de pollo | facil | sí | sí |
| dev-020 | Para la receta más rápida que lleva huevo y lentejas: de los ingredientes que usa y tengo en la heladera, ¿cuál vence primero? | zanahoria | media | **no** | sí |
| dev-021 | El pollo me vence en 2 días y no quiero comprar más. De las recetas con pollo y limón, ¿cuántas puedo hacer para 4 porciones con el pollo que tengo? | 2 | dificil | **no** |  |
