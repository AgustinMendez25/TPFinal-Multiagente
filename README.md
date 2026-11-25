# Rescatá la heladera: un agente para cocinar con lo que hay

Proyecto final de **IA Generativa Avanzada y Sistemas Multi-Agente** (UTDT). Construimos a mano el loop
de un agente con `qwen3:8b` sobre Ollama, sin frameworks ni APIs pagas, y lo usamos en dos dominios:

- **Bloque 1 · el Mundial** (*Fjelstul World Cup Database*): las 30 tareas públicas del kit.
- **Bloque 2 · Rescatá la heladera** (*RecetasDeLaAbuela*): dada una heladera con cantidades y
  vencimientos, qué receta concreta se puede hacer, qué falta comprar y en qué cantidad, o «no se puede»
  cuando los datos no alcanzan. Medimos dos decisiones de agente, la **planificación** y la
  **verificación en código antes de `terminar`**, contra el agente base y dos líneas de base.

El [informe](informe_final.md) tiene la afirmación, el diseño y los resultados. El
[registro de decisiones](decision_log.md) cuenta qué probamos y por qué cambiamos de opinión. La
[propuesta](propuesta.md) aprobada es la v3; las anteriores están en `docs/`.

## Resultado principal

21 tareas congeladas (`rec-*`), temperatura 0,7 con 3 semillas, en una T4 de Colab (`resultados/analisis/`):

| Variante | Aciertos por semilla | Media | Respuestas inventadas (de 9) | Tokens por tarea |
|---|---|---|---|---|
| libro cerrado | 5 / 5 / 5 | 5,0 | 0 | 351 |
| camino fijo | 15 / 15 / 15 | 15,0 | 0 | 958 |
| agente base | 13 / 15 / 14 | 14,0 | 8 | 18.947 |
| + planificación | 16 / 18 / 18 | 17,3 | 4 | 18.709 |
| + verificación | 16 / 16 / 17 | 16,3 | 0 | 20.708 |
| + las dos | 18 / 17 / 19 | 18,0 | 1 | 18.775 |

## Qué hay acá

| Ruta | Qué es |
|---|---|
| [agente.py](agente.py) | La entrada del agente: una pregunta, un dominio, una config y la carpeta de trazas |
| [harness/bucle.py](harness/bucle.py) | **El loop**, el mismo para los dos dominios: herramientas, errores, reintentos, frenos y trazas |
| [harness/dominios.py](harness/dominios.py) | Lo que cambia entre dominios: herramientas, prompt de sistema y los enganches del Bloque 2 |
| [harness/planificacion.py](harness/planificacion.py) | Decisión 1: el plan antes del loop |
| [harness/verificacion.py](harness/verificacion.py), [harness/detector.py](harness/detector.py) | Decisión 2: el chequeo en código antes de `terminar`, y las reglas que leen la dieta y las porciones de la pregunta |
| [herramientas/](herramientas/) | Las del Mundial (del kit, con `partidos` ampliada) y las 4 de recetas |
| [lineas_de_base/camino_fijo.py](lineas_de_base/camino_fijo.py), [libro_cerrado.py](libro_cerrado.py) | Las dos líneas de base |
| [config.toml](config.toml), [configs/](configs/) | La config del Mundial y las 4 variantes de recetas |
| [factibilidad/](factibilidad/) | La normalización del corpus (`preparar_dataset.py`) y el generador de tareas y respuestas (`borrador_respuestas.py`) |
| [datos/](datos/) | Cómo se bajan los datos (versión fijada), el corpus normalizado y el registro de cada decisión de normalización |
| [tareas/](tareas/) | Las 30 del Mundial, las 21 congeladas de recetas, las 21 de desarrollo y la heladera |
| [trazas/](trazas/) | El esquema y el escritor del kit, y **una carpeta por corrida reportada** (58) |
| [resultados/](resultados/) | Un CSV por corrida y, en `analisis/`, las tablas y el gráfico del informe |
| [colab/](colab/) | Los notebooks de cada etapa (se generan desde `colab/fuentes/`) y la plomería de Drive |
| [registros_desarrollo/](registros_desarrollo/) | Las sesiones con el asistente de código |
| [tests/](tests/) | Tests sin modelo: el loop con un LLM falso, las herramientas contra el generador, las trazas |

## Versiones y hardware

- **Modelo:** `qwen3:8b`, digest `500a1f067a9f…4b2b8b41`, sin cambiar los pesos.
- **Ollama 0.40.10** (la del kit), por la API nativa, con `num_ctx = 8192` en cada llamada.
- **Decodificación:** `think` apagado. Temperatura 0 y semilla 1337 en el Bloque 1 y en el desarrollo;
  en la medición congelada, temperatura 0,7 con las semillas 1337, 1338 y 1339, más una referencia a
  temperatura 0 (propuesta §8).
- **Hardware:** Colab gratis con **Tesla T4**, el modelo 100% en GPU. Cada tanda guarda en su carpeta
  de `trazas/` el commit, la config, la versión de Ollama, el digest y la GPU de cada sesión que la corrió.
- **Código medido:** el tag `medicion-v1`.

## Instalación local

Necesitás [uv](https://docs.astral.sh/uv/) y, para correr el agente, [Ollama](https://ollama.com/download).

```bash
uv sync
uv run pytest                          # sin modelo: tiene que dar todo en verde
uv run datos/descargar.py              # Mundial: CSV en un commit fijado y datos/worldcup.sqlite
uv run datos/descargar_recetas.py      # recetas: main.csv en un commit fijado (solo para rehacer el corpus)
ollama pull qwen3:8b
```

El corpus normalizado (`datos/recetas_final.csv`) y las tareas ya están en el repo. Para rehacerlos desde
el CSV crudo:

```bash
uv run factibilidad/preparar_dataset.py     # normaliza unidades y escribe datos/normalizacion/
uv run factibilidad/borrador_respuestas.py  # recalcula las tareas y sus respuestas sobre el corpus
```

## Cómo correr cada bloque

Los tiempos que reportamos se midieron en Colab con los notebooks. Para correrlos: abrí el notebook en
Colab, elegí una **T4** antes de correr nada y tené la carpeta compartida `TPFinal-heladera` en tu Drive
y un token de GitHub de solo lectura. Cada notebook explica sus pasos y se puede retomar si se corta.

| Notebook | GPU | Qué hace |
|---|---|---|
| [01_bloque1_mundial](colab/01_bloque1_mundial.ipynb) | sí | Bloque 1: libro cerrado y agente sobre las 30 tareas, el arreglo antes y después, una tarea negada |
| [02_herramientas_recetas](colab/02_herramientas_recetas.ipynb) | no | El corpus, la heladera y cada herramienta comprobada contra el generador |
| [03_desarrollo](colab/03_desarrollo.ipynb) | sí | Las variantes y las líneas de base sobre las 21 tareas `dev-*` |
| [04_mediciones](colab/04_mediciones.ipynb) | sí | La medición congelada: 25 tandas repartidas entre cuentas, fijada en `medicion-v1` |
| [05_analisis](colab/05_analisis.ipynb) | no | Ruido, comparaciones declaradas con test de signo, control «mismo gasto», grupos y frontera |
| [06_demo](colab/06_demo.ipynb) | sí | La demo: una tarea del conjunto y una pregunta nueva, con la traza a la vista |

Lo mismo desde la terminal, con Ollama corriendo:

```bash
# Bloque 1: una pregunta, las 30 tareas y el puntaje
uv run agente.py -p "¿Qué edad tenía el goleador del Mundial 1978 el día de la final?" --log trazas/prueba
uv run correr_todas.py --corrida trazas/mi_corrida
uv run evaluar.py --corrida trazas/mi_corrida
uv run libro_cerrado.py --corrida trazas/mi_libro_cerrado

# Bloque 2: el agente de recetas con una variante, y una tanda sobre las congeladas
uv run agente.py --dominio recetas --config configs/recetas_ambas.toml --log trazas/prueba \
    -p "¿Qué receta vegetariana con huevo puedo hacer para 2 personas sin comprar nada?"
uv run correr_todas.py --tareas tareas/recetas.json --dominio recetas --config configs/recetas_ambas.toml \
    --corrida trazas/mi_tanda
uv run evaluar.py --tareas tareas/recetas.json --corrida trazas/mi_tanda
```

**Reproducir los números del informe sin GPU.** Las trazas de las corridas reportadas están en
`trazas/`; `evaluar.py` las vuelve a puntuar sin llamar al modelo:

```bash
uv run evaluar.py --tareas tareas/recetas.json --corrida trazas/congelado__ambas__t0.7__s1337 --csv /tmp/x.csv
```

## Lo que conviene saber

- **El conjunto de desarrollo está separado del congelado.** El harness se ajustó solo con `dev-*` (cinco
  vueltas, en el registro de decisiones). Ninguna tarea `rec-*` se corrió antes del tag `medicion-v1`.
- **Las respuestas esperadas se calculan sobre el corpus**, con un script que no usa ni las herramientas ni
  el modelo. Lo único que comparte con el agente es la capa de datos (léxico, parser y equivalencias).
- **Ningún modelo corrige.** `evaluar.py` compara con un programa y valida cada traza con
  `trazas/esquema.py` antes de puntuarla.

## Datos y licencias

Los datos del Mundial son CC BY-SA 4.0 y las recetas, OpenRAIL. El código es MIT. Detalle en
[LICENCIAS.md](LICENCIAS.md).
