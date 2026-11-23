"""Fuente del notebook 05: el análisis de la medición congelada (sin GPU)."""
from comun import entorno

NOMBRE = "05_analisis.ipynb"

CELDAS = [
    ("md", """
# 05 · Análisis: ¿mejoró, o es ruido?

**Qué hace este notebook.** Lee las tandas puntuadas del 04 y contesta la afirmación de la propuesta con los datos, con el ruido a la vista. Sigue la vara de la Clase 12 (Notebook B, §2):

1. **El número de cada variante**, con su intervalo y su costo.
2. **Cuánto se mueve solo:** las tres semillas, la repetición a temperatura 0, pass@3 y pass^3.
3. **Las comparaciones declaradas antes de medir**, de a pares, con el test de signo.
4. **El control «mismo gasto»:** el voto de mayoría de las tres corridas del agente base.
5. **Por grupo:** dentro y fuera del esquema del camino fijo, imposibles y vencimientos.
6. **Acierto y costo juntos:** la frontera.
7. **Lo que hizo la verificación** y lo que detectó el detector, leído de las trazas.
8. **Exportar** las tablas y elegir qué corridas van al repositorio.

**Qué necesitás.** Cualquier entorno de Colab, **sin GPU**: acá no se usa el modelo. La carpeta compartida `TPFinal-heladera`.

**Cuánto tarda.** Un par de minutos.

**Qué deja en Drive.** `resultados/analisis/`: las tablas en CSV y el gráfico.

**La afirmación (propuesta v3, §9).** Con la verificación en código, el agente baja las respuestas inventadas y los filtros salteados, sin perder aciertos. Con la planificación, sube el acierto en las 5 tareas fuera del esquema. Esperamos que el camino fijo empate o gane en las 13 de adentro. Cada mejora cuenta solo si supera la cota de ruido de las 3 semillas.
"""),
    *entorno(gpu=False),
    ("md", """
## 1 · El número de cada variante

Se leen los CSV que dejó el 04 (uno por tanda). Para cada variante:
- **los aciertos de cada semilla a 0,7**, su media y su **rango**: el rango es la cota de ruido de la propuesta;
- **la referencia a temperatura 0**;
- **el intervalo de Wilson del 95%** sobre las 63 corridas (21 tareas × 3 semillas);
- **el costo:** llamadas, tokens y segundos por tarea.
"""),
    ("code", """
import csv, json, statistics
from pathlib import Path
from colab import analisis as A, tandas

RUTAS = entorno.rutas()
SALIDA = RUTAS["resultados"] / "analisis"
SALIDA.mkdir(exist_ok=True)
CORRIDAS = {}
for tanda in tandas.TANDAS_CONGELADAS:
    ruta = RUTAS["resultados"] / f"{tandas.nombre_de(tanda)}.csv"
    if ruta.exists():
        CORRIDAS[tanda] = A.leer_csv(ruta)
faltan = [tandas.nombre_de(t) for t in tandas.TANDAS_CONGELADAS if t not in CORRIDAS]
print(f"{len(CORRIDAS)} tandas leídas.", "Faltan: " + ", ".join(faltan) if faltan else "Están todas.")

VARIANTES = ["libro-cerrado", "camino-fijo", "base", "plan", "verif", "ambas"]
BORRADOR = json.loads(Path("factibilidad/borrador_tareas.json").read_text(encoding="utf-8"))["tareas"]
GRUPOS = A.grupos_de(BORRADOR)


def semillas(variante):
    return {s: CORRIDAS[("congelado", variante, 0.7, s)] for s in tandas.SEMILLAS
            if ("congelado", variante, 0.7, s) in CORRIDAS}


def referencia(variante):
    return CORRIDAS.get(("congelado", variante, 0, 1337))


def guardar(nombre, filas):
    if filas:
        with open(SALIDA / nombre, "w", encoding="utf-8", newline="") as archivo:
            escritor = csv.DictWriter(archivo, fieldnames=list(filas[0]))
            escritor.writeheader()
            escritor.writerows(filas)


TABLA = []
for v in VARIANTES:
    s = semillas(v)
    if not s:
        continue
    aciertos = [A.resumen(f)["aciertos"] for f in s.values()]
    junto = A.resumen(A.juntar_semillas(s))
    ref = A.resumen(referencia(v)) if referencia(v) else None
    TABLA.append({"variante": v, "semillas": len(s), "aciertos_por_semilla": "/".join(map(str, aciertos)),
                  "media": statistics.mean(aciertos), "rango": max(aciertos) - min(aciertos),
                  "ref_t0": ref["aciertos"] if ref else None, "ic95": f"{junto['ic_bajo']:.0%}–{junto['ic_alto']:.0%}",
                  "imposibles_bien": f"{junto['imposibles_bien']}/{junto['imposibles']}", "inventos": junto["inventos"],
                  "llamadas": round(junto["llamadas_por_tarea"], 1), "tokens": round(junto["tokens_por_tarea"]),
                  "segundos": round(junto["segundos_por_tarea"], 1)})
print(f"{'variante':<14}{'por semilla':<13}{'media':>6}{'rango':>6}{'t=0':>5}{'IC 95%':>11}{'imposibles':>12}"
      f"{'inventos':>9}{'llamadas':>9}{'tokens':>8}{'seg':>6}")
for f in TABLA:
    print(f"{f['variante']:<14}{f['aciertos_por_semilla']:<13}{f['media']:>6.1f}{f['rango']:>6}{str(f['ref_t0']):>5}"
          f"{f['ic95']:>11}{f['imposibles_bien']:>12}{f['inventos']:>9}{f['llamadas']:>9}{f['tokens']:>8}{f['segundos']:>6}")
guardar("tabla_principal.csv", TABLA)
"""),
    ("md", """
**Cómo leerla.** Las imposibles son 3 por corrida (9 en las tres semillas), y «inventos» cuenta las imposibles respondidas con un dato inventado. El intervalo es largo: con 21 tareas, una tarea son unos 5 puntos.

## 2 · Cuánto se mueve solo

Antes de creerle a una diferencia, hay que saber cuánto se mueve el número cuando no cambia nada (Clase 12, Notebook B §2.2).

- **La repetición a temperatura 0:** la referencia de base se corrió dos veces, igual. ¿Cuántas respuestas cambiaron?
- **pass@3 y pass^3**, con las tres semillas a 0,7: si la variante **puede** resolver cada tarea en alguna corrida, y si **se puede confiar** en que la resuelva en las tres. Las «mezcladas» son las tareas que a veces acierta y a veces no.
"""),
    ("code", """
bis = CORRIDAS.get(("congelado-bis", "base", 0, 1337))
if bis and referencia("base"):
    a, b = A.por_tarea(referencia("base")), A.por_tarea(bis)
    distintas = [t for t in a if t in b and A._clave_respuesta(a[t]) != A._clave_respuesta(b[t])]
    print(f"Base a temperatura 0, dos veces: {len(distintas)} respuestas distintas de 21 {distintas}; aciertos "
          f"{A.resumen(referencia('base'))['aciertos']} y {A.resumen(bis)['aciertos']}.")
else:
    print("Falta la repetición de base a temperatura 0 (congelado-bis).")

PASS = []
for v in VARIANTES:
    s = semillas(v)
    if len(s) == 3:
        r = A.pass_k(list(s.values()))
        PASS.append({"variante": v, "por_intento": round(r["por_intento"], 3), "pass@3": round(r["pass_at_k"], 3),
                     "pass^3": round(r["pass_hat_k"], 3), "mezcladas": " ".join(r["mezcladas"])})
        print(f"{v:<14} por intento {r['por_intento']:.0%} · pass@3 {r['pass_at_k']:.0%} · pass^3 {r['pass_hat_k']:.0%}"
              f" · mezcladas: {len(r['mezcladas'])}")
guardar("pass_k.csv", PASS)
"""),
    ("md", """
## 3 · Las comparaciones declaradas antes de medir

Están en `decision_log.md`, escritas antes de la primera tanda congelada: comparar después de mirar sería elegir la comparación que conviene.

**Cómo se compara** (Clase 12, Notebook B §2.3): **de a pares**, tarea por tarea y semilla por semilla (63 pares). Solo informan las que cambiaron: **gana** si la segunda variante acertó y la primera no, y **pierde** al revés. El **test de signo** dice qué tan raro sería ese desequilibrio si el cambio no hiciera nada; por debajo de p = 0,05, se distingue del azar.

Al lado, el criterio de la propuesta: la diferencia de medias tiene que superar el rango de las semillas de las dos variantes.

**Una advertencia de potencia.** Con pocas tareas que cambian, el azar explica casi todo: una mejora moderada puede no verse. Un «no se distingue» no prueba que no haya efecto.
"""),
    ("code", """
COMPARACIONES = [
    ("base", "plan", "decisión 1: ¿el plan mejora al agente?"),
    ("base", "verif", "decisión 2: ¿la verificación mejora al agente?"),
    ("base", "ambas", "las dos juntas contra el agente base"),
    ("plan", "ambas", "¿la verificación suma sobre el plan?"),
    ("verif", "ambas", "¿el plan suma sobre la verificación?"),
    ("camino-fijo", "base", "¿el agente le gana al camino fijo?"),
    ("libro-cerrado", "base", "¿las herramientas le ganan a la memoria?"),
]
FILA = {f["variante"]: f for f in TABLA}
COMP = []
for a, b, pregunta in COMPARACIONES:
    if not (semillas(a) and semillas(b)):
        print(f"{a} → {b}: faltan tandas")
        continue
    c = A.comparar(A.juntar_semillas(semillas(a)), A.juntar_semillas(semillas(b)))
    diferencia = FILA[b]["media"] - FILA[a]["media"]
    cota = max(FILA[a]["rango"], FILA[b]["rango"])
    ref = A.comparar(referencia(a), referencia(b)) if referencia(a) and referencia(b) else None
    COMP.append({"a": a, "b": b, "pregunta": pregunta, "pares": c["pares"], "gana": c["gana"], "pierde": c["pierde"],
                 "p": round(c["p"], 4), "azar": "se distingue" if c["p"] < 0.05 else "no se distingue",
                 "diferencia_medias": round(diferencia, 2), "cota_ruido": cota,
                 "supera_cota": abs(diferencia) > cota,
                 "t0_gana_pierde": f"{ref['gana']}-{ref['pierde']} (p={ref['p']:.2f})" if ref else ""})
    print(f"{a:>13} → {b:<6} gana {c['gana']:>2} · pierde {c['pierde']:>2} · p = {c['p']:.3f} ({COMP[-1]['azar']}) · "
          f"medias {diferencia:+.1f} con cota {cota} · a t=0: {COMP[-1]['t0_gana_pierde']}   [{pregunta}]")
guardar("comparaciones.csv", COMP)
"""),
    ("md", """
## 4 · El control «mismo gasto»

Plan y verificación gastan más llamadas que el agente base. Más llamadas suelen dar más aciertos, con o sin la idea nueva: ganarle al agente base no alcanza. El control es el **voto de mayoría** de las tres corridas de base a 0,7 (Clase 12, Notebook B §2.1, control 4): gasta tres veces lo de una corrida y no agrega ningún plan ni chequeo. Las tres corridas ya existen, así que el voto no llama al modelo.
"""),
    ("code", """
if len(semillas("base")) == 3:
    VOTO = A.voto(list(semillas("base").values()))
    rv = A.resumen(VOTO)
    print(f"base, voto de 3: {rv['aciertos']}/21 · imposibles bien {rv['imposibles_bien']}/3 · "
          f"{rv['tokens_por_tarea']:.0f} tokens por tarea (suma de las tres corridas)")
    for v in ("plan", "verif", "ambas"):
        if semillas(v):
            c = A.comparar(A.juntar_semillas({s: VOTO for s in semillas(v)}), A.juntar_semillas(semillas(v)))
            print(f"  voto de base → {v:<6} gana {c['gana']:>2} · pierde {c['pierde']:>2} · p = {c['p']:.3f} · "
                  f"{FILA[v]['tokens']} tokens por tarea")
else:
    print("Faltan semillas de base para el voto.")
"""),
    ("md", """
## 5 · Por grupo

La afirmación es por grupo: el plan apunta a las 5 tareas **fuera del esquema**, la verificación a las **imposibles**, y esperamos que el camino fijo empate o gane **dentro del esquema**. La tabla da el acierto de cada variante en cada grupo (sobre las tres semillas) y, abajo, las comparaciones que la afirmación nombra.

**Para mirar, no para probar:** al partir en grupos quedan muy pocas tareas en cada uno, y probar muchos grupos hace que alguno parezca significativo por suerte.
"""),
    ("code", """
POR_GRUPO = []
print(f"{'grupo':<20}" + "".join(f"{v:>15}" for v in VARIANTES))
for grupo, ids in GRUPOS.items():
    celdas = []
    for v in VARIANTES:
        filas = A.filtrar(A.juntar_semillas(semillas(v)), ids) if semillas(v) else []
        k = sum(f["acierto"] for f in filas)
        celdas.append(f"{k}/{len(filas)}" if filas else "-")
        POR_GRUPO.append({"grupo": grupo, "variante": v, "aciertos": k, "corridas": len(filas)})
    print(f"{grupo:<20}" + "".join(f"{c:>15}" for c in celdas))
guardar("por_grupo.csv", POR_GRUPO)

print()
for a, b, grupo in [("base", "plan", "fuera del esquema"), ("base", "verif", "imposibles"),
                    ("camino-fijo", "base", "dentro del esquema"), ("base", "plan", "usan vencimiento")]:
    if semillas(a) and semillas(b):
        c = A.comparar(A.filtrar(A.juntar_semillas(semillas(a)), GRUPOS[grupo]),
                       A.filtrar(A.juntar_semillas(semillas(b)), GRUPOS[grupo]))
        print(f"{grupo:<20} {a} → {b}: gana {c['gana']} · pierde {c['pierde']} · p = {c['p']:.3f}")
"""),
    ("md", """
## 6 · Acierto y costo, juntos

Cada punto es una variante (las tres semillas juntas), más el voto de base. La altura es el acierto, con la barra del intervalo del 95%, y la posición horizontal son los tokens por tarea (más a la izquierda, más barato). La escalera es la **frontera**: recorriendo de la más barata a la más cara, se queda cada variante que acierta más que todas las anteriores. Estar en la frontera no es ser bueno; quedar adentro quiere decir que otra acierta lo mismo o más por menos.
"""),
    ("code", """
import matplotlib.pyplot as plt

PUNTOS = {}
for v in VARIANTES:
    if semillas(v):
        r = A.resumen(A.juntar_semillas(semillas(v)))
        PUNTOS[v] = (r["tokens_por_tarea"], r["acierto"], r["ic_bajo"], r["ic_alto"])
if len(semillas("base")) == 3:
    r = A.resumen(VOTO)
    PUNTOS["base, voto de 3"] = (r["tokens_por_tarea"], r["acierto"], r["ic_bajo"], r["ic_alto"])
EN_FRONTERA = A.frontera({k: (x, y) for k, (x, y, _, _) in PUNTOS.items()})

fig, ax = plt.subplots(figsize=(9, 5.5))
for nombre, (x, y, bajo, alto) in PUNTOS.items():
    color = "tab:blue" if nombre in EN_FRONTERA else "tab:gray"
    ax.errorbar(x, y, yerr=[[y - bajo], [alto - y]], fmt="o", color=color, capsize=4)
    ax.annotate(nombre, (x, y), textcoords="offset points", xytext=(6, 6), fontsize=9)
xs = [PUNTOS[n][0] for n in EN_FRONTERA]
ys = [PUNTOS[n][1] for n in EN_FRONTERA]
ax.step(xs, ys, where="post", color="tab:blue", alpha=0.5)
ax.set_xscale("log")
ax.set_xlabel("tokens por tarea (escala logarítmica)")
ax.set_ylabel("acierto (21 tareas × 3 semillas)")
ax.set_ylim(0, 1)
ax.set_title("Rescatá la heladera · acierto y costo, con el intervalo del 95%")
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(SALIDA / "acierto_y_costo.png", dpi=150)
plt.show()
print("En la frontera:", EN_FRONTERA)
"""),
    ("md", """
## 7 · Lo que hizo la verificación, y lo que detectó el detector

**Los rechazos.** Cuántas veces la verificación devolvió al modelo, leído de las trazas de cada tanda con verificación. Un rechazo que termina en acierto es el caso que la decisión 2 quería arreglar; uno que termina en error dice que el chequeo vio algo pero el modelo no lo corrigió.
"""),
    ("code", """
for v in ("verif", "ambas"):
    for s, filas in semillas(v).items():
        cuenta = A.rechazos(RUTAS["corridas"] / tandas.nombre_de(("congelado", v, 0.7, s)))
        rechazadas = [t for t, n in cuenta.items() if n]
        resultado = A.por_tarea(filas)
        bien = sum(resultado[t]["acierto"] for t in rechazadas if t in resultado)
        print(f"{v:<6} s{s}: {sum(cuenta.values())} rechazos en {len(rechazadas)} tareas · después del rechazo "
              f"acertó {bien} · {rechazadas}")
"""),
    ("md", """
**El detector sobre las congeladas.** La propuesta pide reportar cuántas detecciones de dieta y porciones salen bien en las preguntas `rec-*`, que el detector nunca vio (se ajustó solo con `dev-*`). La celda imprime lo que detectó en cada una; revisarlo a mano y anotar en el informe cuántas están bien y cuáles no. Si el detector falla en una congelada, se reporta y no se corrige.
"""),
    ("code", """
from harness.detector import detectar
for t in tandas.tareas("congelado"):
    print(f"{t['id']}  {str(detectar(t['pregunta'])):<44} {t['pregunta'][:90]}")
"""),
    ("md", """
## 8 · Exportar

Las tablas quedan en `resultados/analisis/` en Drive. Para el repositorio (el enunciado pide que las trazas de las corridas reportadas estén ahí), estas son las carpetas de `corridas/` y los CSV de `resultados/` que se copian. La copia se hace desde la PC, con Drive para escritorio, y se commitea.
"""),
    ("code", """
REPORTADAS = [tandas.nombre_de(t) for t in tandas.TANDAS_CONGELADAS if t in CORRIDAS]
REPORTADAS += [n for n in sorted(p.name for p in RUTAS["corridas"].iterdir()) if n.startswith(("dev", "mundial__"))
               and n != "mundial__demo"]
(SALIDA / "corridas_reportadas.txt").write_text("\\n".join(REPORTADAS) + "\\n", encoding="utf-8")
print(len(REPORTADAS), "corridas para copiar al repo:")
print("\\n".join(REPORTADAS))
"""),
    ("md", """
## Cierre

Con estas tablas se escribe la sección de resultados del informe: la tabla principal, las comparaciones declaradas con su p, el control del mismo gasto, la lectura por grupo y el gráfico. Las pérdidas y lo que no se distingue del azar también van: una idea que no funcionó, bien explicada, vale casi lo mismo que una que sí.
"""),
]
