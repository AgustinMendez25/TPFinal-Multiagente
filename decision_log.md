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
