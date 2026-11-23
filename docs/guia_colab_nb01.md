# Guía: correr el notebook 01 en Colab (corrida "antes")

Objetivo: dejar en Drive las trazas del **libro cerrado** y del **agente "antes"** sobre las 30 tareas del
Mundial. Con eso se analiza qué falla y se hace el arreglo del Bloque 1.

Tiempo total: unos 10 min de preparación + 30 a 60 min por corrida (son dos corridas: ~1,5 a 2 h).

---

## A · Una sola vez, para todo el grupo

### 1. Carpeta compartida en Drive

Una sola persona:

1. En Google Drive, **Nuevo → Carpeta** → nombre exacto: `TPFinal-heladera`.
2. Clic derecho → **Compartir** → agregar los mails del grupo como **Editor**.

Cada uno de los demás:

1. Drive → **Compartido conmigo** → clic derecho en `TPFinal-heladera` → **Organizar → Agregar acceso directo** → **Mi unidad**.
2. Comprobar que aparece en *Mi unidad*. Colab la busca en `/content/drive/MyDrive/TPFinal-heladera`; si no está ahí, la corrida escribe en otra carpeta.

> No hace falta crear subcarpetas: el notebook crea `corridas/`, `resultados/` y `registros/`.

### 2. Token de GitHub (cada persona que vaya a correr)

El repo `AgustinMendez25/TPFinal-Multiagente` es privado, así que Colab necesita un token para clonarlo.

1. GitHub → tu foto → **Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token**.
2. **Resource owner**: si sos colaborador y no dueño, puede que tengas que usar un *classic token* con permiso `repo`, porque los fine-grained a veces no listan repos ajenos.
3. **Repository access**: *Only select repositories* → `TPFinal-Multiagente`.
4. **Repository permissions → Contents: Read-only**. Vencimiento corto (7 días).
5. Copiá el token y guardalo en un lugar seguro: GitHub lo muestra una sola vez. **No lo pegues en ningún archivo del repo.**

### 3. Drive para escritorio (solo en la PC donde se analiza)

Ya está instalado (`G:\Mi unidad`). Cuando la carpeta compartida esté en *Mi unidad*, va a aparecer como
`G:\Mi unidad\TPFinal-heladera` y las trazas se leen desde ahí.

---

## B · Correr el notebook

### 1. Abrirlo en Colab

Opción simple: en GitHub, abrí `colab/01_bloque1_mundial.ipynb` → botón **Download raw file**. Después, en
[colab.research.google.com](https://colab.research.google.com) → **Archivo → Subir notebook**.

Opción directa: en Colab → **Archivo → Abrir notebook → GitHub** → tildá *Incluir repositorios privados*
(te pide autorizar Colab en GitHub) → elegí el repo y el archivo.

### 2. Elegir la GPU, ANTES de correr nada

**Entorno de ejecución → Cambiar tipo de entorno de ejecución → T4 GPU → Guardar.**

Si la cambiás después, Colab reemplaza la máquina y hay que empezar de nuevo.

### 3. Sección 0 · Preparar el entorno (~10 min)

| Celda | Qué pasa | Qué hacés vos |
|---|---|---|
| 1ª celda de código | Monta Drive y clona el repo | Aceptá el permiso de Drive con tu cuenta. Pegá el token cuando lo pida |
| 2ª celda de código | Instala Ollama 0.40.10, baja `qwen3:8b`, hace una prueba y baja los datos del Mundial | Al final te pide **tu nombre**: escribilo (queda registrado en la tanda) |

Al terminar la 2ª celda se imprime un informe. Revisá:

- `gpu_100: True`. Si dice `False` o aparece **ATENCIÓN: el modelo no corre 100% en la GPU**, desconectá y volvé a conectar con T4.
- `ollama: 0.40.10`.
- `cambios_sin_commit: False`.
- `prueba:` tiene que decir algo como "listo".

### 4. Sección 1 · Cómo funciona el loop

Son celdas que solo muestran código. Correlas (son instantáneas) o salteá la sección: no cambia nada.

### 5. Sección 2 · Libro cerrado (~30 min)

Corré las dos celdas de código en orden:

1. La primera corre las 30 tareas sin herramientas. Va imprimiendo el avance y copia cada traza a Drive apenas termina.
2. La segunda puntúa y escribe `resultados/mundial__libro-cerrado__t0__s1337.csv`.

**Importante:** la primera celda también define `correr()`, que usa la sección 3. Correla aunque la tanda ya esté completa: va a saltear lo que hay y terminar enseguida.

### 6. Sección 3 · El agente "antes" (~30 a 60 min)

- Dejá `ETIQUETA = "antes"` tal como está.
- Corré la celda. Al final imprime la puntuación y escribe `resultados/mundial__agente-antes__t0__s1337.csv`.

### 7. Secciones 4 a 6 (opcionales por ahora)

- **4 · Mirar las trazas:** muestra las tareas que fallaron y una traza legible. Sirve para echar un vistazo.
- **5 · El arreglo:** todavía **no**: necesita la corrida "después".
- **6 · Pregunta suelta:** es para la demo. No hace falta ahora.

---

## C · Si algo sale mal

| Problema | Qué hacer |
|---|---|
| Se cortó la sesión o se desconectó Colab | Volvé a abrir el notebook, corré la **sección 0** completa y después **la misma celda de corrida** donde quedó. Saltea las tareas que ya están en Drive |
| "Ya está tomada por X hace N min" | Otra persona está corriendo esa tanda (o la dejó cortada hace menos de 2 h). Coordinen quién sigue |
| Error de commit distinto al del manifiesto | Alguien hizo push en el medio. **Avisá antes de seguir**: no hay que mezclar versiones del código |
| `git clone` falla con 403 o 404 | El token no tiene acceso al repo. Revisá el paso A.2 |
| No hay T4 disponible | Probá más tarde o con otra cuenta. Las tandas son retomables desde cualquier cuenta con acceso a la carpeta |
| Colab se desconecta por inactividad | Dejá la pestaña abierta y en primer plano. Las cuentas gratis cortan a las ~1,5 h sin interacción |

**No toques `config.toml` ni el código en Colab:** la corrida registra el commit, no los cambios locales.

---

## D · Cuando termina

En Drive tienen que quedar:

```
TPFinal-heladera/
├── corridas/
│   ├── mundial__libro-cerrado__t0__s1337/   (30 .jsonl + manifiesto.json)
│   └── mundial__agente-antes__t0__s1337/    (30 .jsonl + manifiesto.json)
├── resultados/
│   ├── mundial__libro-cerrado__t0__s1337.csv
│   └── mundial__agente-antes__t0__s1337.csv
└── registros/
```

Comprobá que cada carpeta de corrida tenga **30 archivos `.jsonl`** y ningún `tomada.json`. Si queda un
`tomada.json`, la tanda no terminó.

Después **avisá** con la puntuación que imprimió cada corrida. Con las trazas en
`G:\Mi unidad\TPFinal-heladera` se analiza qué falla y se hace el arreglo (Etapa 2). Más adelante, la
corrida "después" se hace con este mismo notebook, cambiando `ETIQUETA = "despues"`.
