"""Fuente del notebook 03: el agente de recetas y sus variantes sobre el conjunto de desarrollo."""
from comun import entorno

NOMBRE = "03_desarrollo.ipynb"

CELDAS = [
    ("md", """
# 03 · Desarrollo: las variantes del agente sobre las tareas `dev-*`

**Qué hace este notebook.** Corre una **variante** del agente de recetas (o una línea de base) sobre las 21 tareas de **desarrollo**, la puntúa y muestra dónde falló. Con eso ajustamos prompts, el detector y la verificación **antes** de medir.

**Por qué un conjunto de desarrollo.** Las 21 tareas congeladas (`rec-*`) son las que se reportan, y no se miran hasta la medición final: si ajustáramos el harness mirándolas, la mejora que midamos valdría solo para ellas. Las `dev-*` salen del mismo generador, con otras recetas y otras formas de preguntar.

**Para correr en paralelo.** Cada integrante abre este notebook en su cuenta y elige **una variante distinta** en la sección 3. La tabla de la sección 2 muestra cuáles están libres.

**Qué necesitás.** Colab con GPU **T4**, la carpeta `TPFinal-heladera` en tu Drive y el token de GitHub de solo lectura.

**Cuánto tarda.** Unos 10 minutos de preparación y de 20 a 40 minutos por variante.

**Qué deja en Drive.** `corridas/dev__<variante>__t0__s1337/` y `resultados/dev__<variante>__t0__s1337.csv`.
"""),
    *entorno(gpu=True),
    ("md", """
## 1 · Las variantes

| Variante | Qué es |
|---|---|
| `libro-cerrado` | El modelo sin herramientas, con la heladera en el prompt. Línea de base. |
| `camino-fijo` | Una llamada que traduce la pregunta a campos (contiene, excluye, dieta, porciones, que_pide) y un pipeline escrito de antemano, sin loop. Línea de base. |
| `base` | El agente: nuestro loop con las 4 herramientas. |
| `plan` | El agente + **planificación**: antes del loop, una llamada escribe el plan (qué candidatas recorrer, con qué criterio, cuándo parar). |
| `verif` | El agente + **verificación** en código antes de `terminar`. |
| `ambas` | Las dos juntas. |

### La planificación
Apunta a una falla: quedarse con la primera receta de la búsqueda cuando la pregunta pide **comparar** varias («la que deja menos por comprar», «cuántas alcanzan»).
"""),
    ("code", """
import inspect
from harness import planificacion, verificacion, detector
print(planificacion.INSTRUCCION)
"""),
    ("md", """
### La verificación
Un chequeo **en código** (no del modelo) antes de dejar terminar: que la respuesta salga de algún resultado de herramienta, que si la pregunta pide una dieta se haya usado `es_apta`, que si pide porciones se hayan usado esas porciones, y que no haya números grandes inventados. Si algo falla, le devuelve al modelo qué le falta, una sola vez. Negarse (`null`) siempre está permitido.

Para saber qué pide la pregunta usa el **detector**: reglas en código (un diccionario de expresiones por dieta y una expresión regular para las porciones), ajustadas solo con estas tareas de desarrollo. Así detecta cada pregunta `dev-*`:
"""),
    ("code", """
from colab import tandas
for t in tandas.tareas("dev"):
    print(t["id"], detector.detectar(t["pregunta"]), "·", t["pregunta"][:80])
"""),
    ("code", """
print(inspect.getsource(verificacion.verificar))
"""),
    ("md", """
## 2 · Qué tandas de desarrollo hay

Cada fila es una variante sobre `dev-*` (temperatura 0, semilla 1337). Elegí una que esté **pendiente**. Si dice «tomada», la está corriendo otra persona.

**Vueltas.** Después de cada vuelta analizamos las trazas y ajustamos el harness (con un commit nuevo). La vuelta siguiente se guarda en otra carpeta (`dev-v2__…`), así la anterior queda como evidencia de qué cambió y por qué. Usá la vuelta que te digan.
"""),
    ("code", """
from harness import corridas
RUTAS = entorno.rutas()
TEMPERATURA, SEMILLA = 0, 1337
VUELTA = 3   # <- la vuelta de desarrollo que estamos corriendo
ETIQUETA = tandas.etiqueta_dev(VUELTA)
print("Vuelta", VUELTA, "· carpetas", ETIQUETA + "__<variante>__t0__s1337")
for variante in tandas.VARIANTES:
    nombre = corridas.nombre_corrida(ETIQUETA, variante, TEMPERATURA, SEMILLA)
    estado = corridas.estado(RUTAS["corridas"] / nombre, tandas.tareas("dev"))
    tomada = f"tomada por {estado['tomada_por']} hace {estado['hace_min']} min" if estado["tomada_por"] else ""
    print(f"{variante:<14} {estado['en_drive']:>2}/{estado['total']} en Drive  {tomada}")
"""),
    ("md", """
## 3 · Correr una variante

Cambiá `VARIANTE` y corré la celda. Cada tarea se copia a Drive apenas termina; si se corta la sesión, volvé a correr la sección 0 y esta celda, y sigue desde donde quedó.
"""),
    ("code", """
VARIANTE = "base"   # <- libro-cerrado, camino-fijo, base, plan, verif o ambas

destino, resumen = tandas.correr("dev", VARIANTE, TEMPERATURA, SEMILLA, quien=QUIEN, rutas=RUTAS,
                                 manifiesto=entorno.manifiesto, antes_de_cada=entorno.asegurar_ollama,
                                 etiqueta=ETIQUETA)
print(resumen)
"""),
    ("code", """
import evaluar
filas, puntaje = tandas.puntuar("dev", destino, RUTAS["resultados"])
evaluar.imprimir(filas, puntaje)
"""),
    ("md", """
## 4 · Dónde falló

Las trazas de las tareas que no acertó. Fijate qué pasó **primero**: ¿buscó mal?, ¿salteó `es_apta`?, ¿usó otras porciones?, ¿se quedó con la primera candidata?, ¿inventó?
"""),
    ("code", """
from harness import ver_traza
fallidas = [f for f in filas if f["resultado"] != "acierto"]
print(len(fallidas), "tareas sin acertar:", [f["tarea"] for f in fallidas])
for f in fallidas[:3]:
    print("\\n" + "=" * 100)
    print(f["tarea"], "· esperado:", f["esperado"], "· obtenido:", f["obtenido"], "·", f["resultado"])
    print(ver_traza.resumen(destino / f"{f['tarea']}.jsonl"))
"""),
    ("md", """
## 5 · Todas las variantes de desarrollo juntas

Cuando las otras personas terminen sus variantes, esta celda junta los resultados de **todas las vueltas** que haya en Drive, para ver qué cambió de una a otra.
"""),
    ("code", """
import csv
for vuelta in range(1, VUELTA + 1):
    print(f"--- vuelta {vuelta}")
    for variante in tandas.VARIANTES:
        nombre = corridas.nombre_corrida(tandas.etiqueta_dev(vuelta), variante, TEMPERATURA, SEMILLA)
        archivo = RUTAS["resultados"] / f"{nombre}.csv"
        if not archivo.exists():
            print(f"{variante:<14} (todavía no está)")
            continue
        filas_v = list(csv.DictReader(open(archivo, encoding="utf-8")))
        aciertos = sum(f["resultado"] == "acierto" for f in filas_v)
        inventos = sum(f["resultado"] == "invento" for f in filas_v)
        print(f"{variante:<14} {aciertos:>2}/{len(filas_v)} aciertos · {inventos} imposibles con respuesta inventada")
"""),
    ("md", """
## Cierre

Avisá que terminó tu variante. Las trazas se analizan desde Drive para escritorio y, si hace falta, se ajusta el harness y se hace otra vuelta: con un commit nuevo y `VUELTA` + 1, en carpetas nuevas.
"""),
]
