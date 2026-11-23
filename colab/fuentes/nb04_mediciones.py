"""Fuente del notebook 04: la medición congelada, repartida entre cuentas y retomable."""
from comun import CLONAR, entorno

NOMBRE = "04_mediciones.ipynb"

_, _, EXPLICA_ENTORNO, PREPARAR = entorno(gpu=True)

CELDAS = [
    ("md", """
# 04 · La medición congelada: las 21 tareas `rec-*`

**Qué hace este notebook.** Corre las tareas **congeladas** con cada variante del agente y las dos líneas de base, con varias semillas. Esto es lo que se reporta en el informe. Cada corrida, que llamamos **tanda**, es una variante sobre las 21 tareas con una temperatura y una semilla.

**Las reglas de la medición:**
- **El código está congelado** en el tag `medicion-v1`, y todas las cuentas miden con ese mismo commit. Después del tag no se cambia el harness. Si aparece un bug, se registra en `decision_log.md`, se hace un tag nuevo y se rehacen las tandas afectadas.
- **Las trazas de `rec-*` no se usan para ajustar nada.** Se miran recién en el análisis (notebook 05).
- **Lo que se compara quedó declarado antes de medir**, en `decision_log.md`.

**Para correr entre varias cuentas.** Cada integrante abre este notebook en su cuenta y corre la sección 3: toma sola la siguiente tanda libre, la marca como tomada en Drive y, al terminar, sigue con la próxima. Dos cuentas nunca corren la misma tanda.

**Qué necesitás.** Colab con GPU **T4**, la carpeta compartida `TPFinal-heladera` (el acceso directo en *Mi unidad*, no una carpeta propia) y el token de GitHub de solo lectura.

**Cuánto tarda.** Unos 10 minutos de preparación y de 20 a 40 minutos por tanda. Son 25 tandas.

**Qué deja en Drive.** `corridas/congelado__<variante>__t<temp>__s<semilla>/` y `resultados/<lo mismo>.csv`.

**Si se corta la sesión:** volvé a correr las secciones 0 a 2 y después la 3. La tanda que estaba a medias sigue desde donde quedó.
"""),
    ("md", """
## 0 · Preparar el entorno

La primera celda monta tu Drive y baja el código. La segunda lo **fija en el tag `medicion-v1`**, antes de importar nada, para que todo lo que corra después sea exactamente el código congelado. Si el tag todavía no existe, se frena: el código no está listo para medir.
"""),
    ("code", CLONAR),
    ("code", """
TAG = "medicion-v1"
subprocess.run(["git", "fetch", "-q", "--tags", "origin"], check=True)
if subprocess.run(["git", "rev-parse", "-q", "--verify", f"refs/tags/{TAG}"], capture_output=True).returncode != 0:
    raise RuntimeError(f"Todavía no existe el tag {TAG}: el código no está congelado. No midas todavía.")
subprocess.run(["git", "checkout", "-q", f"refs/tags/{TAG}"], check=True)
print(subprocess.run(["git", "log", "--oneline", "-1"], capture_output=True, text=True).stdout)
"""),
    EXPLICA_ENTORNO,
    PREPARAR,
    ("md", """
## 1 · Qué se mide

| Variante | Qué es |
|---|---|
| `libro-cerrado` | El modelo sin herramientas, con la heladera en el prompt. Línea de base. |
| `camino-fijo` | Una llamada que traduce la pregunta a campos y un pipeline sin loop. Línea de base. |
| `base` | El agente: el loop con las 4 herramientas. |
| `plan` | Base + **planificación** antes del loop (decisión 1). |
| `verif` | Base + **verificación** en código antes de `terminar` (decisión 2). Es una ablación limpia: el mismo agente, más el chequeo. |
| `ambas` | Las dos juntas. |

**Las condiciones.** Cada variante corre a **temperatura 0,7 con tres semillas** (1337, 1338 y 1339): de ahí sale la cota de ruido de la propuesta y, en el 05, pass@3, pass^3 y el voto de mayoría del agente base (el control «mismo gasto» de la Clase 12). Además corre una vez a **temperatura 0**, la corrida de referencia.

**El orden.** Las tandas salen en orden de prioridad, así lo que se recorta primero queda al final (propuesta, §8):
1. base, plan y verif a 0,7;
2. las dos líneas de base a 0,7;
3. las referencias a temperatura 0;
4. ambas (la corrida conjunta: es lo primero que se recorta);
5. una repetición de la referencia de base a temperatura 0 (`congelado-bis`): mide cuánto se mueve el número sin cambiar nada (Clase 12, Notebook B §2.2).
"""),
    ("md", """
## 2 · El estado de las tandas

Una fila por tanda: cuántas de las 21 tareas ya están en Drive, y si alguien la está corriendo. Volvé a correr esta celda cuando quieras ver el avance de todos.
"""),
    ("code", """
from colab import tandas
RUTAS = entorno.rutas()


def ver_estado():
    filas = tandas.estado_tandas(RUTAS)
    for f in filas:
        marca = "✓" if f["completa"] else (f"tomada por {f['tomada_por']} hace {f['hace_min']} min"
                                           if not f["libre"] else "libre")
        print(f"{f['n']:>2}. {f['nombre']:<42} {f['en_drive']:>2}/{f['total']}  {marca}")
    hechas = sum(f["completa"] for f in filas)
    print(f"\\n{hechas} de {len(filas)} tandas completas.")


ver_estado()
"""),
    ("md", """
## 3 · Correr

La celda toma la siguiente tanda libre en orden de prioridad, la corre, la puntúa y sigue con la próxima, hasta que no quede ninguna libre (o se corte la sesión). Cada tarea se copia a Drive apenas termina.

Del puntaje se imprime solo el total. Las trazas de `rec-*` se analizan en el 05, cuando ya esté todo medido.
"""),
    ("code", """
import time


def correr_tanda(tanda):
    etiqueta, variante, temperatura, semilla = tanda
    print(f"\\n=== {tandas.nombre_de(tanda)} · {time.strftime('%H:%M')}")
    destino, resumen = tandas.correr("congelado", variante, temperatura, semilla, quien=QUIEN, rutas=RUTAS,
                                     manifiesto=entorno.manifiesto, antes_de_cada=entorno.asegurar_ollama,
                                     etiqueta=etiqueta)
    if resumen["completa"]:
        _, puntaje = tandas.puntuar("congelado", destino, RUTAS["resultados"])
        print(f"→ {puntaje['aciertos']}/{puntaje['tareas']} aciertos · imposibles bien: "
              f"{puntaje['imposibles_negadas']}/{puntaje['imposibles']} · tokens: {puntaje['tokens']}")


fallidas = set()   # las que fallaron en esta sesión no se reintentan en el bucle (se ven en la tabla)
while True:
    libres = [f["tanda"] for f in tandas.estado_tandas(RUTAS) if f["libre"] and f["tanda"] not in fallidas]
    if not libres:
        break
    tanda = libres[0]
    try:
        correr_tanda(tanda)
    except Exception as error:        # una tanda tomada por otra cuenta justo ahora, u otro problema: se sigue
        print(f"No se pudo correr {tandas.nombre_de(tanda)}: {error}")
        fallidas.add(tanda)
print("No quedan tandas libres." + (f" Fallaron en esta sesión: {[tandas.nombre_de(t) for t in fallidas]}"
                                    if fallidas else ""))
ver_estado()
"""),
    ("md", """
**Si querés correr una tanda en particular** (por ejemplo, para terminar una que quedó a medias en otra cuenta que ya no está), poné su número de la tabla de la sección 2:
"""),
    ("code", """
NUMERO = None   # <- por ejemplo, 7
if NUMERO is not None:
    correr_tanda(tandas.TANDAS_CONGELADAS[NUMERO - 1])
"""),
    ("md", """
## Cierre

Cuando la tabla de la sección 2 diga que las 25 tandas están completas (o las que entraron, si hubo que recortar), la medición terminó. Lo que sigue es el **05 · Análisis**, que no usa GPU.

Si hubo que recortar tandas, se anota en `decision_log.md` cuáles y por qué.
"""),
]
