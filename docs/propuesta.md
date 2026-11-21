# propuesta.md — Rescatá la heladera: agente para cocinar con lo que hay

## 1. Problema

Las personas que cocinan en casa suelen tener ingredientes disponibles en la heladera y la despensa, algunos próximos a vencer, y necesitan decidir qué preparar sin comprar demasiado ni desperdiciar comida. Una búsqueda tradicional de recetas no resuelve bien el problema, ya que no combina inventario, cantidades, fechas de vencimiento, restricciones alimentarias y sustituciones, ni verifica si una receta es realmente viable con lo disponible.

Proponemos un agente que reciba los ingredientes disponibles, sus cantidades y fechas de vencimiento, la cantidad de comensales y las restricciones indicadas. Su objetivo será recomendar recetas posibles, priorizando el uso de ingredientes próximos a vencer y señalando claramente qué faltaría comprar. También podrá sugerir sustituciones cuando falte algún ingrediente.

El agente buscará ayudar a aprovechar mejor los alimentos disponibles y reducir el desperdicio. No pretende reemplazar recomendaciones médicas ni garantizar la ausencia de alérgenos.

## 2. Datos

Usaremos **RecetasDeLaAbuela, de SomosNLP**, un corpus público de recetas de países hispanoamericanos, creado durante el Hackathon SomosNLP de marzo de 2024. Contiene aproximadamente 20.447 recetas en formato CSV, con 14 atributos por registro, entre ellos nombre, ingredientes, pasos de preparación, país de origen, duración, categoría, comensales, dificultad y valoración.

El dataset está disponible en Hugging Face: https://huggingface.co/datasets/somosnlp/RecetasDeLaAbuela

Su licencia declarada es **OpenRAIL**. Revisaremos sus condiciones de uso y redistribución antes de incluir los datos en el repositorio. Fijaremos una versión o commit específico y conservaremos una copia local para que los experimentos sean reproducibles, respetando las condiciones de la licencia.

Al estar en español, no será necesaria una traducción de ingredientes. Sin embargo, construiremos un mecanismo de normalización para unificar nombres equivalentes o regionales (por ejemplo, "porotos"/"frijoles"), facilitando la comparación entre el inventario y las recetas. También procesaremos los ingredientes y sus cantidades para permitir comparaciones con el inventario disponible.

Las fechas de vencimiento y cantidades del inventario no provendrán del corpus: serán datos de entrada proporcionados por el usuario. Cada producto podrá incluir ingrediente, cantidad, unidad y días restantes hasta su vencimiento. Esto permitirá identificar qué alimentos conviene priorizar sin necesitar un segundo dataset.

## 3. Herramientas

El agente tendrá, como mínimo, estas herramientas:

- `identificar_proximos_a_vencer(inventario: list[Producto], dias_umbral: int) -> list[Producto]`: identifica los productos cuyo vencimiento se encuentra dentro del umbral indicado.
- `buscar_recetas(ingredientes: list[str], excluir: list[str], priorizar: list[str], restricciones: list[str], limite: int) -> list[RecetaResumen]`: busca recetas compatibles con los ingredientes disponibles, excluye los indicados, contempla las restricciones y prioriza aquellas que aprovechan ingredientes próximos a vencer.
- `detalle_receta(receta_id: str) -> Receta`: devuelve ingredientes, cantidades, pasos y tiempos de una receta.
- `escalar_porciones(receta_id: str, porciones: int) -> RecetaEscalada`: ajusta las cantidades a la cantidad de comensales.
- `evaluar_faltantes(receta_id: str, ingredientes_disponibles: list[str]) -> InformeFaltantes`: identifica ingredientes disponibles, faltantes y cantidades aproximadas.
- `buscar_sustituciones(ingrediente: str, contexto: str) -> list[Sustitucion]`: consulta una tabla local y acotada de sustituciones posibles.

El inventario incluirá ingredientes, cantidades y vencimientos. La herramienta de búsqueda podrá utilizar los ingredientes próximos a vencer como criterio de prioridad, sin dejar de respetar las restricciones y la compatibilidad de las recetas.

Las restricciones alimentarias se representarán mediante ingredientes excluidos y condiciones adicionales que puedan verificarse a partir de los ingredientes de cada receta. No se garantizará la detección de trazas ni de alérgenos no declarados.

Al menos un tercio de las tareas de evaluación requerirá encadenar dos o más herramientas; las tareas difíciles requerirán tres o más. Por ejemplo: identificar productos próximos a vencer, buscar recetas que los aprovechen, consultar su detalle y calcular faltantes para una cantidad determinada de personas.

## 4. Dos decisiones de agente que vamos a medir

1. **Planificación antes de usar herramientas:** compararemos el agente que arma un plan breve (analizar inventario, identificar vencimientos, buscar, revisar, escalar y comprobar) con otro que decide cada llamada directamente. Esperamos reducir recomendaciones incompletas o que no respetan todos los requisitos, especialmente cuando hay varios ingredientes prioritarios y restricciones simultáneas.

2. **Verificación antes de responder:** compararemos el agente que revisa al final que la receta respete los ingredientes excluidos, las restricciones declaradas, las cantidades y los faltantes informados, y que efectivamente aproveche los ingredientes prioritarios cuando existe una receta compatible, con otro que responde directamente después de buscar. Esperamos reducir errores y afirmaciones no respaldadas por los datos.

Mediremos ambas decisiones por separado, comparando cada variante con el agente sin esa decisión.

## 5. Líneas de base

- **Libro cerrado:** `qwen3:8b` recibe la pregunta y responde sin herramientas ni acceso al corpus. Esperamos que pueda sugerir platos conocidos, pero que invente cantidades o recetas y no pueda verificar si existen en los datos ni considerar correctamente el inventario y los vencimientos.

- **Camino fijo:** un pipeline determinístico ejecuta siempre la misma secuencia de identificación de productos próximos a vencer, búsqueda, detalle y cálculo de faltantes, sin que el modelo decida el próximo paso. Esperamos que sea consistente en casos simples, pero menos flexible cuando cambian las restricciones, se necesita una sustitución o hay que adaptar la búsqueda a distintos inventarios.

## 6. Prueba de factibilidad

Probaremos manualmente cinco tareas con `qwen3:8b` y registraremos las llamadas, herramientas utilizadas, resultado y errores. Las pruebas iniciales serán:

1. "Tengo huevos, cebolla y papa. ¿Qué puedo cocinar para dos personas?"
2. "Tengo arroz, tomate y lentejas. Buscá una receta que use esos ingredientes y decime qué me falta."
3. "Tengo zanahoria, cebolla, papa y pollo. El pollo vence en dos días y el resto en una semana. Quiero cocinar para cuatro personas: encontrá una receta que priorice el pollo y ajustá las cantidades."
4. "Tengo harina, leche y huevos, pero no tengo manteca. Buscá una receta posible y evaluá si hay una sustitución disponible."
5. "Quiero una receta vegetariana para tres personas, sin huevo, usando lo que tengo: arroz, tomate y cebolla. Además, quiero priorizar los ingredientes que estén próximos a vencer."

**Resultados observados:** se completará esta tabla después de ejecutar las cinco pruebas con el modelo indicado. No se consideran resultados válidos las respuestas estimadas o generadas sin ejecutar el experimento.

| Tarea | ¿La resolvió? | Herramientas y llamadas | Error o limitación observada |
|---|---|---|---|
| 1 | Pendiente | Pendiente | Pendiente |
| 2 | Pendiente | Pendiente | Pendiente |
| 3 | Pendiente | Pendiente | Pendiente |
| 4 | Pendiente | Pendiente | Pendiente |
| 5 | Pendiente | Pendiente | Pendiente |

## 7. Presupuesto y plan

Usaremos `qwen3:8b` con Ollama, sin APIs pagas. Para las 15 tareas del conjunto de evaluación estimamos:

- Libro cerrado: 15 llamadas al modelo.
- Camino fijo: hasta 15 llamadas para interpretar la consulta, más las ejecuciones determinísticas.
- Agente: aproximadamente 2–4 llamadas por tarea, según la cantidad de herramientas y la necesidad de verificación.
- Experimentos de las dos decisiones: cuatro configuraciones (con/sin planificación y con/sin verificación), aproximadamente 45 llamadas por configuración si el promedio es de tres llamadas por tarea.

Estimación inicial: alrededor de 210 llamadas al modelo para las cuatro configuraciones y las dos líneas de base, más las pruebas exploratorias. Ajustaremos el cálculo con las trazas reales.

Si falta tiempo o cómputo, recortaremos primero las sustituciones avanzadas y la optimización de cantidades; mantendremos las dos comparaciones principales, la identificación de productos próximos a vencer y las tareas imposibles.

## 8. Afirmación tentativa

Esperamos demostrar que combinar planificación y verificación permite aumentar la proporción de recomendaciones de recetas que respetan los ingredientes disponibles y las restricciones declaradas, y que aprovechan los productos próximos a vencer cuando existen recetas compatibles en el corpus, frente a un pipeline fijo y a un agente sin esas decisiones, sin aumentar desproporcionadamente las llamadas al modelo.

Evaluaremos, entre otras métricas, la proporción de recomendaciones compatibles con el inventario y las restricciones, la cantidad de ingredientes faltantes correctamente identificados y el aprovechamiento de ingredientes próximos a vencer. Esta última métrica considerará si la recomendación utiliza ingredientes prioritarios cuando existe una receta compatible en el corpus.

La afirmación se considerará refutada si las mediciones no muestran una mejora reproducible.