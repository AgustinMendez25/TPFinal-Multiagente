# Diseño: proyecto completo en notebooks de Colab

Fecha: 2026-11-21 · Entrega: domingo 29/11/2026 · Base: `propuesta.md` (aprobada en su v2) y `ENUNCIADO.md`.

## 1. Objetivo y alcance

Construir y medir todo el proyecto final: el loop del Bloque 1 sobre el Mundial y el agente de recetas
"Rescatá la heladera" del Bloque 2, con sus dos líneas de base y sus dos decisiones medidas
(planificación y verificación). Toda la ejecución con modelo pasa en Colab (T4, cuentas gratis), desde
notebooks que se explican solos. Los resultados intermedios quedan en Google Drive y una corrida cortada
se retoma desde ahí.

**Quién hace qué.**

| Pieza | Responsable |
|---|---|
| Código `.py`, tests, notebooks, `decision_log.md`, `README.md` | el asistente (Claude Code) |
| Correr los notebooks en Colab | el grupo |
| `informe_final.md` y `registros_desarrollo/` | el grupo |

**Fuera de alcance.** Correr notebooks o el modelo en la máquina local. Redactar el informe.

**Lo que sí corre local.** Los tests sin modelo (`uv run pytest`), que no usan GPU ni Ollama.

## 2. Decisiones tomadas

| Tema | Decisión |
|---|---|
| Dónde vive el código | Módulos `.py` en el repo; los notebooks los corren y los explican |
| Plan de Colab | Varias cuentas gratis en paralelo; la cantidad se define después |
| Cómo vuelven los resultados | Drive para escritorio en la PC local: se leen las trazas directo desde la carpeta compartida |
| Cómo llega el código a Colab | `git clone` del repo privado con un token de solo lectura que se pide al correr y no se guarda |
| Organización de las corridas | Enfoque A: notebooks por etapa; cada traza se copia a Drive al cerrar su tarea; retomar = saltear las tareas con traza válida |
| Recortes | Los de la §8 de la propuesta, en orden: corrida conjunta → 3 a 2 semillas → solo vegetariana/vegana |
| Escritura | El asistente redacta `decision_log.md` y `README.md`; el informe lo escribe el grupo |
| Demo de la oral | Notebook `06_demo` con pregunta libre al agente de recetas, además de la del Mundial en `01` |
| Ollama | 0.40.10, la del kit. Se declara que la prueba de factibilidad corrió con la 0.40.16 local |

## 3. Código

**Un solo loop para los dos dominios.** Lo que cambia entre el Mundial y las recetas son:

- las herramientas y sus fichas;
- el prompt de sistema;
- dos enganches opcionales: `antes_del_loop` (el plan) y `antes_de_terminar` (la verificación).

| Archivo | Responsabilidad |
|---|---|
| `harness/bucle.py` | El loop con los 8 requisitos del enunciado (§4). Devuelve `(estado, respuesta, pasos)` y escribe las trazas con el esquema del kit |
| `harness/dominios.py` | `mundial` y `recetas`: herramientas, fichas y prompt de sistema. El de recetas muestra el inventario ordenado por vencimiento y marca como prioritario lo que vence en 3 días o menos |
| `harness/planificacion.py` | Una llamada con salida JSON restringida que devuelve el plan: candidatas a recorrer, criterio de comparación, cuándo parar y filtros. El plan entra como mensaje antes del loop. Su costo cuenta en las trazas |
| `harness/detector.py` | `detectar(pregunta) -> {dieta, porciones}` con reglas en código: un diccionario de expresiones por dieta y una expresión regular para los números (en cifras o en letras de dos a diez) delante de personas, comensales o porciones. Se ajusta solo con `dev-*` |
| `harness/verificacion.py` | Antes de `terminar`, comprueba tres cosas. Si alguna falla, no termina: le devuelve al modelo qué faltó, una vez por pregunta como máximo |
| `herramientas/recetas.py` | `buscar_recetas`, `detalle_receta`, `es_apta`, `faltantes` y sus fichas JSON (§3 de la propuesta). El inventario sale de `tareas/recetas_inventario.json` y es estado de la sesión |
| `lineas_de_base/camino_fijo.py` | Una llamada con salida JSON restringida, un pipeline sin loop y una respuesta armada por plantilla. Escribe trazas con el mismo esquema. Las imposibles: el pipeline siempre devuelve algo, como predice la propuesta |
| `agente.py` | La entrada del kit con `--dominio {mundial,recetas}`. `bucle` delega en `harness/bucle.py` |
| `libro_cerrado.py`, `correr_todas.py` | Se les agrega `--dominio` (y `libro_cerrado` también `--tareas`). Para recetas, el prompt de sistema del libro cerrado incluye el inventario, para que la comparación sea justa |
| `harness/corridas.py` | Correr una tanda contra una carpeta de Drive: corre en local, copia al cerrar, retoma, escribe el manifiesto y maneja `tomada.json` (§4) |
| `configs/` | `mundial.toml`, `recetas_base.toml`, `recetas_plan.toml`, `recetas_verif.toml` y `recetas_ambas.toml`. Cada tanda pisa la temperatura y la semilla |
| `tests/` | Ver la §7 |

**Las tres comprobaciones de la verificación:**

1. La receta de la respuesta (por nombre o por id) salió en algún resultado de herramienta de esta corrida.
2. Si el detector encontró una dieta, hubo un `es_apta` con esa dieta sobre la receta respondida. Si encontró porciones, hubo un `faltantes` o un `detalle_receta` con esas porciones.
3. Los números de la respuesta aparecen en algún resultado de herramienta, o salen de contar elementos de un resultado.

**Valores de `que_pide` en el camino fijo:**

| Valor | Qué devuelve |
|---|---|
| `conteo` | el total de la búsqueda |
| `receta_mas_rapida` | el nombre de la primera candidata apta |
| `apta_si_no` | sí o no |
| `cantidad_ingrediente` | la cantidad de `detalle_receta` con las porciones |
| `faltan_lista` | los ingredientes que faltan |
| `faltan_cuantos` | cuántos ingredientes faltan |
| `faltan_cantidad_ingrediente` | cuánto falta de un ingrediente |
| `otro` | sin plantilla: responde `null` |

Para que el pipeline sepa qué ingrediente o qué receta usar, el esquema agrega dos campos: `ingrediente` y `receta_id`.

## 4. Drive, retomar y reparto entre cuentas

```
TPFinal-heladera/                (carpeta compartida; cada integrante la agrega a Mi unidad)
├── corridas/<corrida>/
│   ├── manifiesto.json          commit, config completa, conjunto, tareas, Ollama, digest, fecha
│   ├── tomada.json              etiqueta de quién corre, inicio y último latido
│   ├── <tarea>.jsonl            aparece solo cuando la tarea terminó
│   └── <tarea>.salida.txt
├── resultados/                  CSV de evaluar.py y del análisis
└── registros/                   salida de pytest y log de Ollama por sesión
```

- **Nombre de la corrida:** `<conjunto>__<config>__t<temp>__s<semilla>`. Por ejemplo `congelado__plan__t0.7__s1338`, `dev__base__t0__s1337` o `mundial__agente-antes__t0__s1337`.
- **Escritura sin trazas a medias.** Cada tarea corre en `/content/trabajo/<corrida>/`. Al cerrar, la traza se copia a Drive como `<tarea>.jsonl.tmp` y se renombra a `.jsonl`.
- **Retomar.** Se saltean las tareas que tienen en Drive un `.jsonl` que pasa `trazas/esquema.py`.
- **Commit fijado.** Si el commit actual no es el del manifiesto, la corrida no sigue. El notebook ofrece dos opciones: `git checkout <commit del manifiesto>` o una corrida nueva.
- **Tandas congeladas.** Son 6 configuraciones por 4 condiciones, 24 tandas de 21 tareas.
  - Configuraciones: libro cerrado, camino fijo, base, plan, verificación y ambas.
  - Condiciones: temperatura 0,7 con las semillas 1337, 1338 y 1339, y la referencia a temperatura 0 con la semilla 1337.
- **Orden de prioridad de las tandas:**
  1. base, plan y verificación a 0,7;
  2. las líneas de base a 0,7;
  3. las referencias a temperatura 0;
  4. "ambas".
- **Reparto.** `04_mediciones` muestra el estado de cada tanda: pendiente, tomada (por quién y hace cuánto), parcial n/21 o completa. Cada persona elige una tanda de un desplegable y el notebook escribe `tomada.json`.
  - Si el último latido tiene menos de 2 horas, avisa y no arranca.
  - El latido se actualiza después de cada tarea.
- **Modelo.** `ollama pull` en cada sesión. No se guarda en Drive.

## 5. Notebooks (`colab/`)

**Estructura común:**

1. Ficha inicial: qué hace, qué necesita, cuánto tarda y qué deja en Drive.
2. Celda de entorno, la misma en todos: monta Drive, clona el repo, instala Ollama 0.40.10, baja el modelo y hace los chequeos de GPU al 100%, versión y commit.
3. Para cada paso, una explicación del concepto y el código real con `inspect.getsource`.
4. Celdas cortas que se pueden volver a correr y que imprimen el avance.
5. Cierre: qué quedó en Drive y qué sigue.

| Notebook | GPU | Contenido |
|---|---|---|
| `00_entorno` | — | No se corre solo: es la celda común. Se guarda como `colab/entorno.py` y cada notebook la ejecuta |
| `01_bloque1_mundial` | sí | Qué es el loop y dónde está cada requisito; libro cerrado y agente sobre las 30 tareas; evaluación; comparación de las trazas antes y después del arreglo; una tarea negada; celda de pregunta suelta |
| `02_herramientas_recetas` | no | El corpus y el inventario; cada herramienta con un ejemplo; comprobación contra el generador en las 42 tareas |
| `03_desarrollo` | sí | El detector sobre `dev-*`; las 4 variantes del agente y el camino fijo sobre `dev-*` (temperatura 0, semilla 1337); resumen de fallas. No carga las tareas congeladas |
| `04_mediciones` | sí | La tabla de tandas, la elección de una, la corrida retomable y `evaluar.py` de la tanda |
| `05_analisis` | no | Ver el detalle abajo |
| `06_demo` | sí | Pregunta libre al agente de recetas con la configuración elegida y la traza mostrada paso a paso |

**Qué hace `05_analisis`:**

- aciertos por configuración, separados dentro del esquema (13), fuera del esquema (5) y en las imposibles (3);
- media y rango sobre las 3 semillas, y si cada diferencia supera la cota de ruido;
- la referencia a temperatura 0 aparte;
- tokens, llamadas y tiempo;
- cuántas detecciones del detector salieron bien en las congeladas;
- gráficos y CSV en `resultados/`;
- la copia de las corridas reportadas al repo.

## 6. Etapas y fechas

| Etapa | Asistente | Grupo | Objetivo |
|---|---|---|---|
| 1. Base y Bloque 1 | `decision_log.md` con el presupuesto inicial; `harness/bucle.py`; dominio `mundial`; LLM falso y tests; `entorno.py`; `01` | `01`: corridas "antes" | dom 22 – lun 23 |
| 2. Arreglo del Bloque 1 | Analizar trazas, elegir una tarea que falla, arreglar y registrar | `01`: corrida "después" | mar 24 |
| 3. Recetas | Herramientas, detector, plan, verificación, camino fijo, configs, tests contra el generador; `02` y `03` | `02`, y `03` en 2 o 3 vueltas de ajuste | mar 24 – jue 26 |
| 4. Congelado y mediciones | Tag `medicion-v1`; `04` y `05` | `04`: las 24 tandas | jue 26 – sáb 28 |
| 5. Cierre | `05`, copia de las corridas al repo, README, cierre del decision log, `06_demo` | `05`, el informe | sáb 28 – dom 29 |

**Reglas para que la medición valga:**

- **Después del tag `medicion-v1` no se cambia el código del agente.** Si aparece un bug: entrada en el decision log, tag nuevo y se rehacen las tandas afectadas.
- **Antes de la etapa 4 no se corre ninguna tarea `rec-*`.**
- **Plazo para "ambas".** Si el viernes 27 a la noche faltan más de 8 tandas, "ambas" se saca y se registra.

## 7. Errores y pruebas

**Errores en ejecución:**

- **Ollama no responde.** El loop reintenta con espera creciente, hasta un tope de la configuración. Si sigue caído, la tarea cierra con `estado: error`. La celda de corrida comprueba el servidor antes de cada tarea y lo vuelve a levantar si hace falta.
- **Colab corta la sesión.** Se vuelve a correr la celda de entorno y después la de corrida.
- **Una traza inválida.** No suma, como pide el enunciado, y `05` la lista aparte.

**Tests sin modelo (`uv run pytest`, local y en `02`):**

- El loop con un LLM falso con guion: JSON roto, una herramienta inexistente, argumentos del tipo equivocado, una herramienta que levanta una excepción, un resultado largo que se recorta, error del servidor y reintento, topes de pasos y de tokens, `terminar` con `null`. Además, que la traza valide con `trazas/esquema.py`.
- Las herramientas de recetas reproducen la respuesta esperada de las 36 tareas respondibles (18 congeladas y 18 `dev-*`) encadenando las llamadas de `cadena_esperada`. Este test no usa el modelo, así que no cuenta como "mirar" las congeladas.
- El detector sobre las preguntas `dev-*`, con lo que se espera de cada una según `borrador_tareas.json`.
- La verificación: casos que pasan y casos que fallan, con trazas sintéticas.
- `harness/corridas.py`: copia atómica, retomar, commit distinto, `tomada.json` vencido y vigente, con carpetas temporales.
- Los tests del kit siguen pasando.

## 8. Riesgos

| Riesgo | Mitigación |
|---|---|
| Las cuentas gratis no consiguen T4 | Las tandas son chicas (21 tareas, unos 40 min) y retomables; se reparten entre cuentas |
| No llegan las mediciones | Recortes de la §8; el colchón del domingo 29 |
| El detector anda mal con las redacciones de las congeladas | Se reporta, no se corrige (§4 de la propuesta) |
| Drive para escritorio tarda en sincronizar | Antes de analizar, chequear la fecha del último archivo de la corrida |
| Mezclar versiones de código | El manifiesto fija el commit, y el tag `medicion-v1` |
