# propuesta.md (v2): Rescatá la heladera, un agente para cocinar con lo que hay

> **Qué cambió respecto de la v1** (respuesta a la devolución):
> 1. Conjunto de evaluación definido: 15 tareas con respuesta cerrada calculada sobre los datos, entre ellas 3 imposibles (§5 y Anexo A). Sacamos las tareas abiertas, así que no hace falta un corrector de restricciones aparte.
> 2. Diez filas reales del dataset y una medición de cuánto se puede parsear (§2 y Anexo B). El dominio sigue siendo viable, pero con alcance acotado.
> 3. Prueba de factibilidad hecha en su versión mínima, a libro cerrado y con resultados pegados (§7).
> 4. Herramientas rediseñadas: son 4 y cada una hace una sola cosa. El inventario es estado de la sesión y el vencimiento lo calcula el harness (§3).
> 5. Agregamos la cota de ruido y rehicimos el presupuesto (§8).

## 1. Problema

Una persona que cocina en casa tiene en la heladera ingredientes con cantidades y fechas de vencimiento, cocina para un número dado de personas y a veces tiene restricciones (vegetariano, sin gluten…). Quiere saber qué receta concreta de un recetario puede hacer, qué le falta comprar y en qué cantidad. Un buscador de recetas no cruza el inventario con las cantidades escaladas a las porciones, y un modelo de 8B a libro cerrado inventa recetas y cantidades (§7). Lo que el agente agrega es una respuesta **verificable contra el corpus**: el id de la receta, los faltantes calculados y un "no se puede" honesto cuando los datos no alcanzan.

No pretendemos reemplazar recomendaciones médicas ni garantizar la ausencia de alérgenos.

## 2. Datos

**RecetasDeLaAbuela** (SomosNLP, hackathon 2024), Hugging Face `somosnlp/RecetasDeLaAbuela`, licencia OpenRAIL. Usamos el archivo `main.csv`, **fijado en el commit `c9879423aeb4b151fb8941f79098e9606d25c782`**, con 20.236 filas y 14 columnas. Se baja con `datos/descargar_recetas.py` y no se versiona en el repositorio.

**Cómo vienen los ingredientes** (diez filas crudas en el Anexo B). Son texto libre, en dos formatos según el sitio de origen:

- **recetasgratis.net (18.187 filas, el 90%):** una lista de Python serializada, con una línea por ingrediente: `['1 kg de solomillo cortado en medallones', '1/2 kg de setas (…)', 'Sal', …]`.
- **Los otros sitios:** un solo string separado por comas, y la coma también aparece dentro de un ingrediente (`½ taza de Queso Fresco mexicano, cortado en cubitos`). Hay además mojibake (`kiÃ³n`), líneas en portugués y recetas con todos los ingredientes en una sola línea.

Las cantidades mezclan números, fracciones unicode (`½`, `⅔`), rangos (`2 o 3`) y unidades heterogéneas: gramos, tazas, "vasos pequeños", "1 pechuga", "1 chorro", "al gusto". `Comensales` está vacío en el 31% de las filas de recetasgratis y `Duracion` también. `Valor nutricional` es una etiqueta cualitativa ("Alto en calorías…") y **no hay calorías numéricas**.

**Decisión: acotamos el corpus en vez de resolver el parseo general.** Medimos un normalizador de borrador (`factibilidad/normalizar.py`), que tiene un léxico de unos 60 ingredientes canónicos con sus sinónimos regionales (papa/patata, poroto/frijol/alubia, manteca/mantequilla), etiquetas para las dietas y una tabla de unidades:

| Medida (recetasgratis con comensales y duración: 12.473 recetas, 106.896 líneas) | Valor |
|---|---|
| Líneas con ingrediente canónico reconocido | 88% |
| Líneas con cantidad numérica | 94% |
| Líneas con unidad comparable (g, ml o unidades sueltas) | 70% |
| Recetas con **todas** sus líneas reconocidas | **5.151 (41%)** |

El **corpus de trabajo** son esas 5.151 recetas: recetasgratis, con comensales, duración y todas las líneas reconocidas. Alcanza para tareas con respuesta única. Sal, pimienta, aceite, agua y condimentos secos se suponen siempre disponibles y no cuentan como faltantes. Las cantidades se comparan solo cuando la unidad coincide (gramos con gramos, mililitros con mililitros, unidades con unidades). Si no se puede comparar, la herramienta lo dice en lugar de adivinar. Las tareas se eligen para que su respuesta no dependa de una conversión dudosa.

El borrador ya mostró fallas concretas que el normalizador definitivo tiene que cubrir y que el verificador de tareas tiene que esquivar. NFKD convertía `½` en `1⁄2` y se leía como 1 (ya está corregido). `4 vasos pequeños de Arroz` no tiene unidad convertible. `Caldo de verduras o pollo` deja indefinido si la receta es vegetariana. `1 litro de caldo de pollo` hacía que una crema de zanahorias apareciera como "receta con pollo" (se corrige dando prioridad a las formas largas del léxico).

El **inventario** no sale del corpus. Lo define cada tarea (ingrediente, cantidad, unidad, días hasta vencer) y el harness lo carga como estado de la sesión.

## 3. Herramientas

El inventario es **estado de la sesión**. El harness lo muestra en el prompt de sistema ordenado por vencimiento y marca como *prioritarios* los productos que vencen en 3 días o menos (eso es código, no una herramienta). Ninguna herramienta recibe el inventario como argumento.

| Herramienta | Qué hace (una sola cosa) |
|---|---|
| `buscar_recetas(contiene: list[str], excluye: list[str] = [])` | Filtra por presencia de ingredientes canónicos. Devuelve el total y las primeras 10 recetas (`id`, `nombre`, `minutos`, `comensales`), ordenadas por duración y, si empatan, por id. Si un nombre no está en el léxico, devuelve un error con los nombres válidos más parecidos. |
| `detalle_receta(receta_id: int, porciones: int \| None)` | Devuelve los ingredientes de una receta: canónico, cantidad, unidad y línea original. Con `porciones`, escala las cantidades. |
| `es_apta(receta_id: int, dieta: "vegetariana" \| "vegana" \| "sin_gluten" \| "sin_lactosa")` | Devuelve `{apta, ingredientes_que_lo_impiden}`, según las etiquetas del léxico. |
| `faltantes(receta_id: int, porciones: int)` | Compara la receta escalada con el inventario de la sesión. Devuelve, por ingrediente, si alcanza, si falta o si no se puede comparar por la unidad. |
| `terminar(respuesta, motivo)` | La del kit. `respuesta = null` cuando los datos no alcanzan. |

**Qué sacamos y por qué:**

- `identificar_proximos_a_vencer` pasa a ser código del harness.
- `escalar_porciones` queda como parámetro de `detalle_receta`.
- `buscar_sustituciones` sale porque no hay una fuente de datos de sustituciones: la tabla la habríamos inventado nosotros.
- `buscar_recetas` pierde `priorizar`, `restricciones` y `limite`: solo filtra. Las restricciones de dieta se comprueban con `es_apta` sobre cada candidata, así que una tarea con dieta necesita **buscar → es_apta (una o más veces) → faltantes o detalle**.

**Encadenamiento:** 7 de las 15 tareas necesitan dos llamadas o más (las 4 medias respondibles y las 3 difíciles, que necesitan tres o más). Ver la columna "cadena" del Anexo A.

## 4. Dos decisiones de agente que vamos a medir

1. **Planificación antes de usar herramientas** (plan-and-execute). Una primera llamada escribe el plan como lista de pasos (qué buscar, qué filtro de dieta, para cuántas porciones). Falla que esperamos arreglar: en la §7, con los resultados delante, el modelo no eligió una receta (devolvió las tres) y no cruzó lo que pedía la pregunta con los datos. En las tareas difíciles esperamos que salte `es_apta` o que use las porciones equivocadas.
2. **Verificación antes de `terminar`.** Un chequeo en código del harness, no del modelo, revisa que la receta citada exista en las trazas de esta corrida, que haya pasado por `es_apta` si la pregunta pedía una dieta y por `faltantes` con las porciones de la pregunta, y que la respuesta no contenga ingredientes o cantidades que no aparecieron en ningún resultado de herramienta. Si algo falla, le devuelve al modelo qué faltó. Falla que esperamos arreglar: respuestas con cantidades inventadas y respuestas a tareas imposibles.

**No es circular.** La métrica compara la respuesta con la esperada del conjunto congelado, que calcula `tareas/verificadores_recetas.py` directo sobre el corpus normalizado, sin llamar a las herramientas ni al verificador del agente. Lo único que comparten es la capa de datos (léxico y parser), y eso lo declaramos.

Cada decisión se mide por separado contra el agente sin ella, con las mismas 15 tareas.

## 5. Conjunto de evaluación

Son 15 tareas en `tareas/recetas.json`, con el formato del kit más un campo `inventario` que carga el harness. Todas usan el mismo inventario fijo:

| Ingrediente | Cantidad | Vence en |
|---|---|---|
| pollo | 500 g | **2 días** |
| tomate | 3 unidades | **3 días** |
| leche | 1000 ml | 5 días |
| zanahoria | 3 unidades | 6 días |
| cebolla | 2 unidades | 10 días |
| huevo | 6 unidades | 12 días |
| papa | 1000 g | 15 días |
| arroz | 1000 g | 60 días |
| harina | 1000 g | 90 días |
| lenteja | 500 g | 90 días |

- **Dificultad:** 6 fáciles (5 respondibles con una llamada y 1 imposible), 6 medias (4 respondibles y 2 imposibles) y 3 difíciles (tres llamadas encadenadas).
- **Imposibles (3), pero verosímiles:** calorías por porción (no están en los datos), una combinación de ingredientes sin ninguna receta en el corpus (verificado: 0) y el costo de los faltantes (no hay precios).
- **Respuestas cerradas:** `numero`, `texto` (el nombre de la receta) o `lista` (los ingredientes canónicos que faltan). Cuando la pregunta pide "la más rápida", el empate se rompe por el id más bajo, que es el orden en que devuelve `buscar_recetas`. Para las respuestas de tipo `lista`, el evaluador compara conjuntos después de normalizar con el mismo léxico, de modo que "lentejas" y "lenteja" cuentan igual.
- **Verificadas con código:** `factibilidad/borrador_respuestas.py` calcula hoy cada respuesta sobre el corpus y es la base de `tareas/verificadores_recetas.py`. El conjunto se congela antes de la primera corrida del agente. Lo redactamos nosotros con ayuda de un asistente de código, y cada respuesta la revisamos a mano contra las líneas crudas de la receta (la nota de cada tarea del Anexo A cita esa línea).

El detalle completo de las tareas está en el Anexo A.

## 6. Líneas de base

- **Libro cerrado:** `qwen3:8b` sin herramientas, con las 15 tareas y su formato de respuesta. En la §7 inventó recetas y cantidades y no dijo de dónde salían. Esperamos que acierte casi nada en las tareas que piden un id o un nombre del corpus, y que conteste las imposibles con valores inventados.
- **Camino fijo:** una sola llamada al modelo con salida restringida a un esquema JSON (`contiene`, `excluye`, `dieta`, `porciones`, `que_pide`) y después un pipeline sin loop: `buscar_recetas` → `es_apta` sobre las candidatas en orden → `faltantes` o `detalle_receta` → una respuesta armada por plantilla. Esperamos que resuelva bien las fáciles y medias bien formadas, y que falle cuando la pregunta no encaja en el esquema (por ejemplo, "el ingrediente que vence primero") y en las imposibles, porque el pipeline siempre devuelve algo.

## 7. Prueba de factibilidad (versión mínima: libro cerrado y resultado pegado)

Todavía no tenemos el loop del Bloque 1, así que hicimos la versión mínima que propuso la devolución. Corrimos las cinco tareas de la v1 con `qwen3:8b` sin herramientas. En las tareas 2 y 3 repetimos la pregunta pegando en el prompt el resultado real de `buscar_recetas` y de `detalle_receta` sobre el corpus, tal como lo devolvería una herramienta. Usamos `factibilidad/libro_cerrado_5.py` con temperatura 0, semilla 1337, `think` apagado, `num_ctx` 8192 y `num_predict` 800. La corrida fue local en CPU, sin GPU, con Ollama 0.40.16. Las trazas están en `factibilidad/trazas/` y las respuestas completas en `factibilidad/respuestas.json`.

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
5. **Lo que no pudimos ver sin el loop:** si el modelo llama a las herramientas por su cuenta y si encadena las tres (`buscar → es_apta → faltantes`). Es lo primero que vamos a probar cuando el loop del Bloque 1 esté andando, con las tareas rec-010 a rec-012.

## 8. Presupuesto, cota de ruido y plan

**Cota de ruido.** Con temperatura 0 la semilla no cambia nada, así que vamos a variar la temperatura y declararlo. Cada configuración se corre con **temperatura 0,7 y 3 semillas** (1337, 1338, 1339). Reportamos la media y el rango de aciertos, y una diferencia entre configuraciones cuenta solo si supera ese rango. Las comparaciones a temperatura 0 se reportan aparte, como corrida de referencia.

**Llamadas por tarea, rehechas con lo que vimos:** la prueba muestra que el modelo necesita ver el detalle de cada candidata para decidir, y que las cadenas difíciles son de 3 a 5 herramientas.

| Configuración | Llamadas por tarea (estimadas) | × 15 tareas × 3 semillas |
|---|---|---|
| Libro cerrado | 1 | 45 |
| Camino fijo | 1 (más herramientas sin modelo) | 45 |
| Agente base | ~5 (3 herramientas, `terminar` y un reintento) | ~225 |
| + planificación | ~6 | ~270 |
| + verificación | ~7 (una vuelta extra cuando el chequeo falla) | ~315 |
| **Total** | | **~900 llamadas**, más unas 150 exploratorias |

Tokens: con los resultados pegados, el prompt de la prueba pasó de unos 80 a unos 1.500–2.000 tokens. Estimamos un promedio de unos 3.000 tokens de entrada por llamada del agente, o sea unos 3 millones de tokens en total. En CPU local cada llamada tardó de 1 a 3 minutos, así que **todas las mediciones de tiempo van en la T4 de Colab** y la máquina local queda para desarrollo.

**Qué recortamos primero, en orden:**

1. La corrida conjunta de planificación con verificación.
2. Bajar de 3 a 2 semillas.
3. `sin_lactosa` y `sin_gluten` (queda solo `vegetariana`/`vegana`).

No se recortan las dos comparaciones principales, las tareas imposibles ni la cota de ruido.

## 9. Afirmación tentativa

Con la verificación en código antes de `terminar`, el agente baja las respuestas inventadas (en las 3 imposibles y en las tareas donde cita cantidades) frente al agente sin verificación, sin perder aciertos en las respondibles. Con la planificación, sube el acierto en las 3 tareas difíciles (las de `buscar → es_apta → faltantes`). Las dos mejoras se miden contra el agente base y las dos líneas de base, y cuentan solo si superan la cota de ruido de las 3 semillas. La afirmación queda refutada si alguna de las dos diferencias no supera esa cota.

---

## Anexo A: las 15 tareas, con su respuesta calculada

Las respuestas las calculó `factibilidad/borrador_respuestas.py` sobre el corpus de trabajo. Inventario: el de la §5.

| id | Pregunta | Respuesta | Tipo | Dif. | Cadena esperada | Nota (de dónde sale) |
|---|---|---|---|---|---|---|
| rec-001 | ¿Cuántas recetas del corpus llevan lentejas y arroz? | 8 | numero | facil | buscar_recetas |  |
| rec-002 | ¿Cuál es la receta más rápida que lleva papa y huevo? | patatas a lo pobre con huevo frito | texto | facil | buscar_recetas | id 18611, 10 min |
| rec-003 | ¿La receta 3814 es apta para veganos? Respondé sí o no. | sí | texto | facil | es_apta | arroz con lentejas arabe |
| rec-004 | ¿Cuántos gramos de arroz lleva la receta 3628 si la hago para 6 personas? | 300 | numero | facil | detalle_receta | arroz thai con verduras y pollo, 2 comensales, línea: 100 gramos de Arroz blanco cocido |
| rec-005 | ¿Cuál es la receta más rápida que lleva zanahoria y el ingrediente de mi inventario que vence primero? | ensaladilla rusa original | texto | facil | buscar_recetas | vence primero: pollo (lo marca el harness en el prompt); id 7383 |
| rec-006 | ¿Cuál es la receta más rápida que lleva pollo y zanahoria y es sin lactosa? | ensaladilla rusa original | texto | media | buscar_recetas → es_apta | id 7383 |
| rec-007 | De las recetas que llevan lentejas y arroz, ¿cuál es la más rápida que sea vegana? | lentejas con arroz y tomate | texto | media | buscar_recetas → es_apta → es_apta | id 9041 |
| rec-008 | Para la receta más rápida que lleva pollo y zanahoria, ¿cuántas pechugas de pollo necesito para 6 personas? | 2 | numero | media | buscar_recetas → detalle_receta | id 7383, 3 comensales, línea: 1 pechuga de pollo fileteada |
| rec-009 | Si hago para 10 personas la receta más rápida que lleva papa y huevo, ¿cuántos huevos me faltan con lo que tengo? | 14 | numero | media | buscar_recetas → faltantes | id 18611, 1 comensales, línea: 2 Huevos |
| rec-010 | Quiero algo vegetariano con arroz y tomate: tomá la receta vegetariana más rápida que los lleve y decime qué me falta comprar para 4 personas. | `["limon", "maiz", "palta", "perejil", "queso", "tomate"]` | lista | dificil | buscar_recetas → es_apta → faltantes | id 7531 ensalada de arroz basmati rapida y ligera |
| rec-011 | De las recetas con pollo, zanahoria y cebolla que no llevan huevo, tomá la más rápida que sea sin gluten: ¿qué me falta comprar para hacerla para 6 personas? | `["ajo", "miel", "morron", "pollo", "zapallo"]` | lista | dificil | buscar_recetas → es_apta → faltantes | id 3628 arroz thai con verduras y pollo |
| rec-012 | No tengo manteca. De las recetas vegetarianas con leche, harina y huevo que no llevan manteca, tomá la más rápida: ¿cuántos ingredientes me faltan comprar para hacerla para 8 personas? | 3 | numero | dificil | buscar_recetas → es_apta → faltantes | id 8124 pancakes de manzana: faltan ['azucar', 'levadura', 'manzana'] |
| rec-013 | ¿Cuántas calorías por porción tiene la receta 9041? | `null` (imposible) | numero | facil | detalle_receta | el corpus no tiene calorías numéricas |
| rec-014 | Tengo lentejas, frutillas y pescado y quiero usar los tres: ¿cuál es la receta más rápida que los lleve? | `null` (imposible) | texto | media | buscar_recetas | 0 recetas los llevan a los tres |
| rec-015 | ¿Cuánto me cuesta comprar lo que me falta para hacer la receta 9041 para 4 personas? | `null` (imposible) | numero | media | faltantes | el corpus no tiene precios |

## Anexo B: diez filas reales

En `factibilidad/diez_filas.md` están las diez filas tal como vienen en el CSV: 6 de recetasgratis.net (el subconjunto que usamos) y 1 de cada uno de los otros sitios grandes (mexicoenmicocina, yanuq y cookpad), sin las columnas `Pasos` ni `Contexto`. Tres ejemplos representativos de la columna `Ingredientes`:

```
Id 8124 (recetasgratis, lista):
['1 manzana', '1 huevo', '1 taza de leche (200 cc)', '1 taza de harina (100 gr)',
 '1 cucharada postre de polvo para hornear', '1 cucharada sopera de azúcar',
 '1 cucharadita de esencia de vainilla']

Id 1 (mexicoenmicocina, texto con comas):
½ taza de cilantro finamente picado, 1 taza de tomate picadito y sin semillas, …,
3 papas rojas de tamaño mediano ~510 gr. *, 24 palillos de madera para sostener los taquitos …

Id 9880 (recetasgratis, todo en una línea):
['4 papas grandes picadas en cuadros para hervirlas 1 lata de maiz 3 huevos hervidos 1lb de
  camarones medianos pelados 1 cebolla en cuadritos …']
```
