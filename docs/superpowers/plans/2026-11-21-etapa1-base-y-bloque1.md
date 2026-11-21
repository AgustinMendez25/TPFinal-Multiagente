# Etapa 1 (base y Bloque 1): plan de implementación

> **Para agentes:** SUB-SKILL REQUERIDA: usar superpowers:subagent-driven-development (recomendado) o superpowers:executing-plans para implementar este plan tarea por tarea. Los pasos usan casillas (`- [ ]`) para el seguimiento.

**Objetivo:** dejar listo el loop del Bloque 1 sobre el Mundial, la infraestructura de corridas en Drive (que se pueden retomar) y el notebook `01_bloque1_mundial`, para que el grupo corra en Colab la corrida "antes" y el libro cerrado.

**Arquitectura:**
- **El loop.** Vive en `harness/bucle.py`. Recibe un `Dominio` (prompt de sistema, fichas y funciones) y se va a reusar después para recetas.
- **`agente.py`.** Sigue siendo la entrada del kit y delega en el loop.
- **`harness/corridas.py`.** Corre una tanda de tareas en el disco local y copia cada traza cerrada a Drive. Al retomar, saltea las tareas que ya tienen una traza válida. El manifiesto fija el commit.
- **Notebooks.** Se generan con un script (`colab/construir.py`) a partir de fuentes Python, así se pueden revisar en un diff.

**Tecnologías:** Python 3.11+, biblioteca estándar, Ollama 0.40.10 (API nativa, a través de `llm.py` del kit), pytest, uv; Google Colab (T4) y Google Drive.

**Spec:** `docs/superpowers/specs/2026-11-21-proyecto-completo-design.md`

## Restricciones globales

- Nada de frameworks de agentes. Solo el cliente de Ollama (`llm.py`) y la biblioteca estándar (ENUNCIADO §4).
- Las trazas cumplen el esquema de `trazas/esquema.py`. Se pueden **agregar** campos y eventos; no se cambian ni se sacan los del enunciado.
- `num_ctx` explícito en cada llamada. La configuración se copia entera en `corrida_inicio`.
- Decodificación fija para el Bloque 1: temperatura 0, semilla 1337, `think` apagado.
- Ollama **0.40.10** en Colab. Modelo `qwen3:8b`, con el tag explícito.
- **Nunca correr notebooks ni el modelo en la máquina local.** Local solo corre `uv run pytest` (tests sin modelo).
- Carpeta de Drive: `/content/drive/MyDrive/TPFinal-heladera`, que se puede cambiar con la variable de entorno `TPFINAL_DRIVE`.
- Repositorio: `AgustinMendez25/TPFinal-Multiagente`, privado. El token de GitHub se pide al correr y no se escribe en ningún archivo.
- Código, comentarios, mensajes y textos de los notebooks en español, con el estilo del kit (rioplatense, sin anglicismos innecesarios).
- Commits con la línea `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Mapa de archivos

| Archivo | Acción | Responsabilidad |
|---|---|---|
| `decision_log.md` | crear | Registro de decisiones: presupuesto inicial, plan y decisiones de la etapa |
| `config.toml`, `config.py` | modificar | Claves nuevas: `frenos.reintentos`, `frenos.espera_reintento_s`, `contexto.herramienta_timeout_s` |
| `tests/llm_falso.py` | crear | LLM con guion para probar el loop sin Ollama |
| `harness/__init__.py` | crear | Paquete vacío |
| `harness/bucle.py` | crear | `Dominio`, `Fin`, `validar_argumentos`, `bucle` |
| `harness/dominios.py` | crear | `construir("mundial")`: prompt de sistema, fichas y funciones del Mundial |
| `agente.py` | modificar | `--dominio`; delega en `harness.bucle`; escribe `corrida_fin` con `motivo` |
| `correr_todas.py` | modificar | `correr_tarea(..., dominio=None)` pasa `--dominio` |
| `harness/corridas.py` | crear | Corridas en Drive: nombre, manifiesto, tomada/latido, copia atómica, retomar, configuración por tanda |
| `harness/ver_traza.py` | crear | Traza legible para los notebooks |
| `colab/entorno.py` | crear | Ollama, modelo, chequeos y rutas de Drive en Colab |
| `colab/construir.py` | crear | Arma los `.ipynb` desde `colab/fuentes/*.py` |
| `colab/fuentes/nb01_bloque1_mundial.py` | crear | Celdas del notebook 01 |
| `colab/01_bloque1_mundial.ipynb` | generado | El notebook que se abre en Colab |
| `tests/test_bucle.py`, `tests/test_corridas.py`, `tests/test_ver_traza.py`, `tests/test_notebooks.py` | crear | Tests sin modelo |
| `tests/test_agente.py`, `tests/test_config.py` | modificar | Pasan de esperar el esqueleto a esperar el loop |

---

### Tarea 1: entorno local de tests y decision log inicial

**Archivos:**
- Crear: `decision_log.md`

**Interfaces:** no aplica (preparación).

- [ ] **Paso 1: instalar uv y las dependencias**

Correr (PowerShell):
```powershell
python -m pip install --user uv
python -m uv sync
```
Lo esperado: se crea `.venv/` (ya está en `.gitignore`) con pytest instalado.

- [ ] **Paso 2: bajar los datos del Mundial (sin modelo) y correr los tests del kit**

```powershell
python -m uv run datos/descargar.py
python -m uv run pytest -q
```
Lo esperado: todo en verde, salvo `test_agente.py`, que todavía espera el esqueleto y también pasa. Si algo falla en este punto, anotarlo y no seguir sin entender por qué.

- [ ] **Paso 3: escribir `decision_log.md` con la primera entrada**

```markdown
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
`qwen3:8b`. La prueba de factibilidad de la propuesta corrió en CPU local con Ollama 0.40.16. Las
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
- Cada traza se copia a Drive (`TPFinal-heladera/corridas/`) cuando su tarea termina. Una corrida cortada se retoma salteando las tareas que ya tienen una traza válida.
- Un `manifiesto.json` por corrida fija el commit con que se corrió, para no mezclar versiones del harness.

**Descartado:**
- Escribir todo dentro de los notebooks: duplica código entre notebooks y no se puede testear.
- Sincronizar a Drive cada N tareas: un corte de sesión pierde hasta N tareas.
- Guardar el modelo en Drive: copiar 5 GB tarda más o menos lo mismo que bajarlo.
```

- [ ] **Paso 4: commit**

```powershell
git add decision_log.md uv.lock
git commit -m "Decision log inicial: presupuesto, cómputo y plan" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tarea 2: configuración nueva y LLM falso

**Archivos:**
- Modificar: `config.toml`, `config.py`
- Modificar: `tests/test_config.py`
- Crear: `tests/llm_falso.py`

**Interfaces:**
- Produce las claves de configuración `config["frenos"]["reintentos"]` (int), `config["frenos"]["espera_reintento_s"]` (número) y `config["contexto"]["herramienta_timeout_s"]` (número).
- Produce `tests.llm_falso.LLMFalso(guion)`, que se llama como `llm.chat(mensajes, **opciones) -> llm.Respuesta`. Además:
  - `llamada(*pares, contenido="", entrada=100, salida=20) -> llm.Respuesta`, donde cada par es `(nombre, argumentos)` o `(nombre, argumentos, id)`;
  - `texto(contenido, entrada=100, salida=20) -> llm.Respuesta`.

- [ ] **Paso 1: test que falla para las claves nuevas**

En `tests/test_config.py`, agregar a la lista de `test_falta_una_clave_obligatoria` los pares `("frenos", "reintentos")`, `("frenos", "espera_reintento_s")` y `("contexto", "herramienta_timeout_s")`. Así queda el decorador:

```python
@pytest.mark.parametrize("seccion, clave", [("modelo", "num_ctx"), ("modelo", "think"), ("frenos", "max_pasos"),
                                            ("frenos", "max_tokens"), ("frenos", "reintentos"),
                                            ("frenos", "espera_reintento_s"),
                                            ("contexto", "tope_resultado_caracteres"),
                                            ("contexto", "herramienta_timeout_s")])
```

- [ ] **Paso 2: correr y ver que falla**

`python -m uv run pytest tests/test_config.py -q`. Lo esperado es que falle por `KeyError`, porque las claves no están en `config.toml`.

- [ ] **Paso 3: agregar las claves**

En `config.toml`, sección `[frenos]`, debajo de `max_seg`:
```toml
reintentos = 3            # reintentos ante un error del servidor del modelo (sin contar el primer intento)
espera_reintento_s = 2.0  # espera antes del primer reintento; se duplica en cada uno
```
Sección `[contexto]`, debajo de `tope_resultado_caracteres`:
```toml
herramienta_timeout_s = 30   # una herramienta que tarda más se corta y vuelve como error
```
En `config.py`, `OBLIGATORIAS`:
```python
OBLIGATORIAS = {
    "modelo": {"nombre": str, "num_ctx": int, "temperatura": NUMERO, "semilla": int, "think": bool,
               "num_predict": int, "timeout_s": NUMERO},
    "frenos": {"max_pasos": int, "max_tokens": int, "reintentos": int, "espera_reintento_s": NUMERO},
    "contexto": {"tope_resultado_caracteres": int, "herramienta_timeout_s": NUMERO},
}
```

- [ ] **Paso 4: escribir `tests/llm_falso.py`**

```python
"""Un LLM con guion: devuelve las respuestas (o levanta los errores) en el orden dado.

Se llama igual que `llm.chat` y guarda cada pedido, para que los tests miren qué mensajes recibió el modelo.
"""
import copy

import llm


class LLMFalso:
    def __init__(self, guion):
        self.guion = list(guion)
        self.pedidos = []

    def __call__(self, mensajes, **opciones):
        self.pedidos.append({"mensajes": copy.deepcopy(mensajes), **opciones})
        if not self.guion:
            raise AssertionError("el guion del LLM falso se terminó")
        siguiente = self.guion.pop(0)
        if isinstance(siguiente, Exception):
            raise siguiente
        return siguiente


def llamada(*pares, contenido="", entrada=100, salida=20) -> llm.Respuesta:
    """Una respuesta con llamadas a herramientas. Cada par: (nombre, argumentos) o (nombre, argumentos, id)."""
    llamadas = []
    for par in pares:
        item = {"function": {"name": par[0], "arguments": par[1]}}
        if len(par) > 2:
            item["id"] = par[2]
        llamadas.append(item)
    return llm.Respuesta({"role": "assistant", "content": contenido, "tool_calls": llamadas},
                         entrada, salida, 50, "stop")


def texto(contenido, entrada=100, salida=20) -> llm.Respuesta:
    """Una respuesta sin llamadas a herramientas."""
    return llm.Respuesta({"role": "assistant", "content": contenido}, entrada, salida, 50, "stop")
```

- [ ] **Paso 5: correr los tests**

`python -m uv run pytest tests/test_config.py -q`. Lo esperado: PASS.

- [ ] **Paso 6: commit**

```powershell
git add config.toml config.py tests/test_config.py tests/llm_falso.py
git commit -m "Config: reintentos y timeout de herramientas; LLM falso para tests" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tarea 3: el loop (`harness/bucle.py`)

**Archivos:**
- Crear: `harness/__init__.py` (vacío), `harness/bucle.py`
- Test: `tests/test_bucle.py`

**Interfaces:**
- Consume: `llm.chat`, `llm.LLMError`, `llm.ContextOverflow`, `llm.Respuesta` (del kit), `tests.llm_falso` (Tarea 2) y `config` con las claves de la Tarea 2.
- Produce:
  - `Dominio(nombre: str, sistema: str, fichas: list[dict], herramientas: dict[str, Callable])`
  - `Fin(estado: str, respuesta: str | None, pasos: int, motivo: str | None = None)`
  - `validar_argumentos(ficha: dict, argumentos) -> str | None`
  - `bucle(pregunta: str, config: dict, registro, dominio: Dominio, *, chat=llm.chat, dormir=time.sleep) -> Fin`
  - `RECORDATORIO: str`, el mensaje que se le manda al modelo cuando contesta sin llamar herramientas.
- **Eventos de traza que agrega** (además de los del enunciado):
  - `llamada_modelo.texto`: lo que escribió el modelo, hasta 500 caracteres;
  - `llamada_modelo.razon_fin`;
  - `resultado_herramienta.contenido`: lo que vio el modelo;
  - un evento `sin_llamadas` con `paso` y `texto`.

- [ ] **Paso 1: escribir los tests**

`tests/test_bucle.py`:

```python
"""El loop del agente, probado con un LLM con guion: sin Ollama y sin datos."""
import json
import time

import pytest

import llm
from harness.bucle import RECORDATORIO, Dominio, bucle, validar_argumentos
from herramientas.mundial import FICHAS_POR_NOMBRE, _ficha
from tests.llm_falso import LLMFalso, llamada, texto
from trazas import esquema
from trazas.registro import Registro

CONFIG = {
    "modelo": {"nombre": "qwen3:8b", "num_ctx": 8192, "temperatura": 0, "semilla": 1337, "think": False,
               "num_predict": 800, "timeout_s": 300},
    "frenos": {"max_pasos": 6, "max_tokens": 10000, "reintentos": 2, "espera_reintento_s": 0},
    "contexto": {"tope_resultado_caracteres": 200, "herramienta_timeout_s": 0.5},
}
TERMINAR = FICHAS_POR_NOMBRE["terminar"]


def _dominio():
    def sumar(a, b):
        return {"total": a + b}

    def explota():
        raise ValueError("se rompió")

    def lenta():
        time.sleep(2)
        return {"ok": True}

    def larga():
        return {"texto": "x" * 500}

    def vacia():
        return []

    fichas = [_ficha("sumar", "Suma dos enteros.", {"a": {"type": "integer"}, "b": {"type": "integer"}}, ("a", "b")),
              _ficha("explota", "Falla siempre.", {}), _ficha("lenta", "Tarda.", {}),
              _ficha("larga", "Devuelve mucho texto.", {}), _ficha("vacia", "No encuentra nada.", {}), TERMINAR]
    return Dominio("prueba", "Sistema de prueba.", fichas,
                   {"sumar": sumar, "explota": explota, "lenta": lenta, "larga": larga, "vacia": vacia})


def _correr(tmp_path, guion, config=CONFIG):
    registro = Registro(tmp_path, "t-1")
    registro.evento("corrida_inicio", modelo="qwen3:8b", config=config)
    chat = LLMFalso(guion)
    fin = bucle("¿Cuánto es 2 + 3?", config, registro, _dominio(), chat=chat, dormir=lambda s: None)
    registro.evento("corrida_fin", estado=fin.estado, respuesta=fin.respuesta, pasos=fin.pasos, motivo=fin.motivo)
    assert esquema.validar_archivo(registro.ruta) == []
    eventos = [json.loads(l) for l in registro.ruta.read_text(encoding="utf-8").splitlines()]
    return fin, eventos, chat


def _ultimo_resultado(chat):
    return chat.pedidos[-1]["mensajes"][-1]


def test_responde_con_una_herramienta_y_terminar(tmp_path):
    fin, eventos, chat = _correr(tmp_path, [llamada(("sumar", {"a": 2, "b": 3})),
                                            llamada(("terminar", {"respuesta": "5", "motivo": "sumar dio 5"}))])
    assert (fin.estado, fin.respuesta, fin.pasos) == ("respondida", "5", 2)
    assert fin.motivo == "sumar dio 5"
    assert _ultimo_resultado(chat) == {"role": "tool", "content": '{"total": 5}', "tool_name": "sumar"}
    assert chat.pedidos[0]["num_ctx"] == 8192 and chat.pedidos[0]["temperatura"] == 0
    assert [e["evento"] for e in eventos].count("llamada_modelo") == 2


def test_terminar_con_null_es_negada(tmp_path):
    fin, _, _ = _correr(tmp_path, [llamada(("terminar", {"respuesta": None, "motivo": "no hay datos"}))])
    assert (fin.estado, fin.respuesta) == ("negada", None)


@pytest.mark.parametrize("valor, esperado", [(5, "5"), (2.5, "2.5"), (["a", "b"], "a; b"), ("null", None),
                                             ("  ", None)])
def test_terminar_normaliza_la_respuesta(tmp_path, valor, esperado):
    fin, _, _ = _correr(tmp_path, [llamada(("terminar", {"respuesta": valor, "motivo": "m"}))])
    assert fin.respuesta == esperado


def test_json_roto_vuelve_como_error_y_sigue(tmp_path):
    fin, eventos, chat = _correr(tmp_path, [llamada(("sumar", "{a: 2")),
                                            llamada(("terminar", {"respuesta": "5", "motivo": "m"}))])
    assert fin.estado == "respondida"
    assert "JSON" in _ultimo_resultado(chat)["content"]
    resultado = next(e for e in eventos if e["evento"] == "resultado_herramienta")
    assert resultado["ok"] is False
    assert next(e for e in eventos if e["evento"] == "llamada_herramienta")["argumentos"] == "{a: 2"


def test_json_en_texto_valido_se_acepta(tmp_path):
    fin, _, chat = _correr(tmp_path, [llamada(("sumar", '{"a": 2, "b": 3}')),
                                      llamada(("terminar", {"respuesta": "5", "motivo": "m"}))])
    assert '"total": 5' in _ultimo_resultado(chat)["content"]


def test_herramienta_inexistente(tmp_path):
    _, _, chat = _correr(tmp_path, [llamada(("multiplicar", {"a": 2})),
                                    llamada(("terminar", {"respuesta": None, "motivo": "m"}))])
    contenido = _ultimo_resultado(chat)["content"]
    assert "no existe" in contenido and "sumar" in contenido


def test_argumento_de_tipo_equivocado(tmp_path):
    _, _, chat = _correr(tmp_path, [llamada(("sumar", {"a": "2", "b": 3})),
                                    llamada(("terminar", {"respuesta": None, "motivo": "m"}))])
    assert "«a» tiene que ser integer" in _ultimo_resultado(chat)["content"]


def test_argumento_que_falta_o_sobra(tmp_path):
    _, _, chat = _correr(tmp_path, [llamada(("sumar", {"a": 2, "c": 1})),
                                    llamada(("terminar", {"respuesta": None, "motivo": "m"}))])
    assert "faltan argumentos obligatorios: b" in _ultimo_resultado(chat)["content"]


@pytest.mark.parametrize("nombre, fragmento", [("explota", "la herramienta falló: ValueError"),
                                               ("lenta", "tardó más de 0.5 s"),
                                               ("vacia", "no encontró nada")])
def test_herramientas_que_fallan_o_no_encuentran(tmp_path, nombre, fragmento):
    fin, _, chat = _correr(tmp_path, [llamada((nombre, {})),
                                      llamada(("terminar", {"respuesta": None, "motivo": "m"}))])
    assert fin.estado == "negada"
    assert fragmento in _ultimo_resultado(chat)["content"]


def test_resultado_largo_se_recorta(tmp_path):
    _, eventos, chat = _correr(tmp_path, [llamada(("larga", {})),
                                          llamada(("terminar", {"respuesta": None, "motivo": "m"}))])
    resultado = next(e for e in eventos if e["evento"] == "resultado_herramienta")
    assert resultado["truncado"] is True and resultado["caracteres"] > 200
    assert "recortado" in _ultimo_resultado(chat)["content"]


def test_reintenta_ante_error_del_servidor(tmp_path):
    fin, eventos, _ = _correr(tmp_path, [llm.LLMError("caído"),
                                         llamada(("terminar", {"respuesta": "5", "motivo": "m"}))])
    assert fin.estado == "respondida"
    reintento = next(e for e in eventos if e["evento"] == "reintento_modelo")
    assert reintento["intento"] == 1 and "caído" in reintento["motivo"]


def test_se_rinde_despues_de_los_reintentos(tmp_path):
    fin, eventos, _ = _correr(tmp_path, [llm.LLMError("caído")] * 3)
    assert fin.estado == "error" and "reintentos" in fin.motivo
    assert sum(e["evento"] == "reintento_modelo" for e in eventos) == 2


def test_contexto_desbordado_es_error_sin_reintentar(tmp_path):
    fin, eventos, _ = _correr(tmp_path, [llm.ContextOverflow("no entra")])
    assert fin.estado == "error" and "num_ctx" in fin.motivo
    assert not any(e["evento"] == "reintento_modelo" for e in eventos)


def test_tope_de_pasos(tmp_path):
    fin, _, _ = _correr(tmp_path, [llamada(("sumar", {"a": 1, "b": 1}))] * 6)
    assert (fin.estado, fin.respuesta, fin.pasos) == ("tope_pasos", None, 6)


def test_tope_de_tokens(tmp_path):
    config = {**CONFIG, "frenos": {**CONFIG["frenos"], "max_tokens": 150}}
    fin, _, _ = _correr(tmp_path, [llamada(("sumar", {"a": 1, "b": 1}))] * 2, config)
    assert (fin.estado, fin.pasos) == ("tope_tokens", 2)


def test_respuesta_sin_llamadas_recibe_un_recordatorio(tmp_path):
    fin, eventos, chat = _correr(tmp_path, [texto("Son 5."),
                                            llamada(("terminar", {"respuesta": "5", "motivo": "m"}))])
    assert fin.estado == "respondida"
    assert chat.pedidos[1]["mensajes"][-1] == {"role": "user", "content": RECORDATORIO}
    assert any(e["evento"] == "sin_llamadas" and e["texto"] == "Son 5." for e in eventos)


def test_ids_generados_y_respetados(tmp_path):
    _, eventos, _ = _correr(tmp_path, [llamada(("sumar", {"a": 1, "b": 1}), ("sumar", {"a": 2, "b": 2}),
                                               ("sumar", {"a": 3, "b": 3}, "call_x")),
                                       llamada(("terminar", {"respuesta": "x", "motivo": "m"}))])
    ids = [e["id"] for e in eventos if e["evento"] == "llamada_herramienta"]
    assert ids[:3] == ["p1-1", "p1-2", "call_x"] and len(set(ids)) == len(ids)


def test_validar_argumentos():
    ficha = _ficha("f", "", {"n": {"type": "integer"}, "s": {"type": ["string", "null"]}}, ("n",))
    assert validar_argumentos(ficha, {"n": 1, "s": None}) is None
    assert "tiene que ser integer" in validar_argumentos(ficha, {"n": True})
    assert "no existen" in validar_argumentos(ficha, {"n": 1, "x": 2})
    assert "objeto" in validar_argumentos(ficha, [1])
```

- [ ] **Paso 2: correr y ver que falla**

`python -m uv run pytest tests/test_bucle.py -q`. Lo esperado: falla con `ModuleNotFoundError: No module named 'harness'`.

- [ ] **Paso 3: implementar `harness/bucle.py`**

```python
"""El loop del agente, compartido por los dominios (Mundial y recetas).

Lo que resuelve, en el orden de la sección 4 del enunciado:
  1. el ciclo: llamar al modelo, ejecutar cada llamada a herramienta, devolver un resultado por llamada;
  2. el contrato: cada herramienta tiene su ficha JSON y los argumentos se validan contra ella;
  3. la salida mal formada: JSON roto, herramienta inexistente o argumentos equivocados vuelven al
     modelo como error, y el loop sigue;
  4. las herramientas que fallan: excepciones, timeouts y resultados vacíos también vuelven como texto;
  5. el contexto: un resultado más largo que `contexto.tope_resultado_caracteres` se recorta;
  6. los reintentos: un error del servidor se reintenta `frenos.reintentos` veces, con espera creciente;
  7. la parada: topes de pasos, de tokens y (opcional) de segundos, y `terminar(respuesta, motivo)`;
  8. las trazas: un evento por cada cosa que pasa.
"""
import json
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturoVencido
from dataclasses import dataclass
from typing import Callable

import llm

RECORDATORIO = ("No llamaste a ninguna herramienta. Si necesitás datos, llamá a una herramienta. Si ya tenés "
                "la respuesta, llamá a terminar(respuesta, motivo); si los datos no alcanzan, a "
                "terminar(null, motivo). No contestes con texto suelto.")
_TIPOS = {"string": str, "integer": int, "number": (int, float), "boolean": bool, "array": list,
          "object": dict, "null": type(None)}
_EJECUTOR = ThreadPoolExecutor(max_workers=4)


@dataclass
class Dominio:
    nombre: str
    sistema: str                         # el prompt de sistema
    fichas: list[dict]                   # los esquemas JSON, incluida la de `terminar`
    herramientas: dict[str, Callable]    # nombre -> función; `terminar` no está: la atiende el loop


@dataclass
class Fin:
    estado: str                          # respondida, negada, tope_pasos, tope_tokens o error
    respuesta: str | None
    pasos: int
    motivo: str | None = None


def _es_tipo(valor, tipo) -> bool:
    for nombre in (tipo if isinstance(tipo, list) else [tipo]):
        if nombre in ("integer", "number") and isinstance(valor, bool):
            continue
        if isinstance(valor, _TIPOS[nombre]):
            return True
    return False


def validar_argumentos(ficha: dict, argumentos) -> str | None:
    """None si los argumentos cumplen la ficha; si no, el error explicado para el modelo."""
    parametros = ficha["function"]["parameters"]
    propiedades = parametros.get("properties", {})
    if not isinstance(argumentos, dict):
        return "los argumentos tienen que ser un objeto JSON"
    faltan = [r for r in parametros.get("required", []) if r not in argumentos]
    if faltan:
        return f"faltan argumentos obligatorios: {', '.join(faltan)}"
    sobran = [k for k in argumentos if k not in propiedades]
    if sobran:
        return f"argumentos que no existen: {', '.join(sobran)}. Los válidos son: {', '.join(propiedades)}"
    for clave, valor in argumentos.items():
        tipo = propiedades[clave].get("type")
        if tipo and not _es_tipo(valor, tipo):
            return f"«{clave}» tiene que ser {tipo}, y llegó {type(valor).__name__}: {valor!r}"
    return None


def _parsear(crudos) -> tuple[dict | None, str | None]:
    if isinstance(crudos, dict):
        return crudos, None
    if isinstance(crudos, str):
        try:
            valor = json.loads(crudos) if crudos.strip() else {}
        except json.JSONDecodeError as error:
            return None, f"los argumentos no son JSON válido ({error.msg}). Mandalos como un objeto JSON"
        return (valor, None) if isinstance(valor, dict) else (None, "los argumentos tienen que ser un objeto JSON")
    return None, "los argumentos tienen que ser un objeto JSON"


def _respuesta_final(valor) -> str | None:
    """`terminar` puede traer un número, una lista o el texto «null»: todo se lleva a texto o None."""
    if valor is None:
        return None
    if isinstance(valor, list):
        valor = "; ".join(str(x) for x in valor)
    texto = str(valor).strip()
    return None if texto.casefold() in ("", "null", "none") else texto


def _ejecutar(funcion: Callable, argumentos: dict, timeout_s: float):
    futuro = _EJECUTOR.submit(funcion, **argumentos)
    try:
        return futuro.result(timeout=timeout_s)
    except FuturoVencido:
        return {"error": f"la herramienta tardó más de {timeout_s:g} s y se cortó"}
    except Exception as error:  # noqa: BLE001 (cualquier falla de la herramienta vuelve al modelo)
        return {"error": f"la herramienta falló: {type(error).__name__}: {error}"}


def _texto_resultado(datos, tope: int) -> tuple[str, bool, int]:
    if datos is None or datos == [] or datos == {} or datos == "":
        datos = {"resultado": "vacío", "nota": "la herramienta no encontró nada con esos argumentos"}
    texto = datos if isinstance(datos, str) else json.dumps(datos, ensure_ascii=False)
    if len(texto) <= tope:
        return texto, False, len(texto)
    resto = len(texto) - tope
    return texto[:tope] + f"\n[…recortado: {resto} caracteres más. Pedí algo más específico.]", True, len(texto)


def _llamar_modelo(mensajes, dominio, config, registro, paso, chat, dormir) -> llm.Respuesta:
    modelo, frenos = config["modelo"], config["frenos"]
    for intento in range(1, frenos["reintentos"] + 2):
        try:
            return chat(mensajes, modelo=modelo["nombre"], num_ctx=modelo["num_ctx"],
                        temperatura=modelo["temperatura"], semilla=modelo["semilla"], think=modelo["think"],
                        num_predict=modelo["num_predict"], herramientas=dominio.fichas,
                        timeout_s=modelo["timeout_s"])
        except llm.ContextOverflow:
            raise
        except llm.LLMError as error:
            if intento > frenos["reintentos"]:
                raise
            registro.evento("reintento_modelo", paso=paso, motivo=str(error)[:300] or "error del servidor",
                            intento=intento)
            dormir(frenos["espera_reintento_s"] * 2 ** (intento - 1))
    raise AssertionError("no se llega acá")


def _atender(llamada: dict, indice: int, paso: int, dominio: Dominio, fichas: dict, config: dict, registro,
             mensajes: list, vistos: set) -> Fin | None:
    """Ejecuta una llamada a herramienta y agrega su resultado. Devuelve un Fin si fue `terminar`."""
    funcion = llamada.get("function") or {}
    nombre = funcion.get("name") or "(sin nombre)"
    ident = llamada.get("id")
    if not ident or ident in vistos:          # el id tiene que ser único en toda la traza
        ident = f"p{paso}-{indice + 1}"
    vistos.add(ident)
    crudos = funcion.get("arguments", {})
    argumentos, error = _parsear(crudos)
    registro.evento("llamada_herramienta", paso=paso, id=ident, nombre=nombre,
                    argumentos=argumentos if error is None else str(crudos))
    inicio = time.perf_counter()
    if error is None and nombre not in fichas:
        error = f"la herramienta «{nombre}» no existe. Las que hay: {', '.join(fichas)}"
    if error is None and nombre == "terminar" and "respuesta" in argumentos:
        argumentos = {**argumentos, "respuesta": _respuesta_final(argumentos["respuesta"])}
    if error is None:
        error = validar_argumentos(fichas[nombre], argumentos)
    tope = config["contexto"]["tope_resultado_caracteres"]
    if error is None and nombre == "terminar":
        texto, truncado, caracteres = _texto_resultado({"ok": "respuesta registrada"}, tope)
        _registrar(registro, mensajes, paso, ident, nombre, True, texto, truncado, caracteres, inicio)
        respuesta = argumentos["respuesta"]
        return Fin("respondida" if respuesta is not None else "negada", respuesta, paso, argumentos.get("motivo"))
    datos = {"error": error} if error is not None else \
        _ejecutar(dominio.herramientas[nombre], argumentos, config["contexto"]["herramienta_timeout_s"])
    ok = not (isinstance(datos, dict) and "error" in datos)
    texto, truncado, caracteres = _texto_resultado(datos, tope)
    _registrar(registro, mensajes, paso, ident, nombre, ok, texto, truncado, caracteres, inicio)
    return None


def _registrar(registro, mensajes, paso, ident, nombre, ok, texto, truncado, caracteres, inicio):
    registro.evento("resultado_herramienta", paso=paso, id=ident, ok=ok, truncado=truncado, caracteres=caracteres,
                    duracion_ms=round((time.perf_counter() - inicio) * 1000), contenido=texto)
    mensajes.append({"role": "tool", "content": texto, "tool_name": nombre})


def bucle(pregunta: str, config: dict, registro, dominio: Dominio, *, chat=llm.chat,
          dormir=time.sleep) -> Fin:
    frenos = config["frenos"]
    fichas = {f["function"]["name"]: f for f in dominio.fichas}
    mensajes = [{"role": "system", "content": dominio.sistema}, {"role": "user", "content": pregunta}]
    tokens = 0
    vistos: set[str] = set()
    inicio = time.monotonic()
    for paso in range(1, frenos["max_pasos"] + 1):
        if tokens >= frenos["max_tokens"]:
            return Fin("tope_tokens", None, paso - 1, f"se usaron {tokens} tokens (tope {frenos['max_tokens']})")
        if frenos.get("max_seg") and time.monotonic() - inicio > frenos["max_seg"]:
            return Fin("error", None, paso - 1, f"se pasó el tope de {frenos['max_seg']} s")
        try:
            respuesta = _llamar_modelo(mensajes, dominio, config, registro, paso, chat, dormir)
        except llm.ContextOverflow as error:
            return Fin("error", None, paso, f"el contexto no entra en num_ctx: {error}")
        except llm.LLMError as error:
            return Fin("error", None, paso, f"el servidor no respondió después de {frenos['reintentos']} "
                                            f"reintentos: {error}")
        mensaje = respuesta.mensaje
        contenido = mensaje.get("content") or ""
        registro.evento("llamada_modelo", paso=paso, modelo=config["modelo"]["nombre"],
                        num_ctx=config["modelo"]["num_ctx"], tokens_entrada=respuesta.tokens_entrada,
                        tokens_salida=respuesta.tokens_salida, duracion_ms=respuesta.duracion_ms,
                        razon_fin=respuesta.razon_fin, texto=contenido[:500])
        tokens += respuesta.tokens_entrada + respuesta.tokens_salida
        llamadas = mensaje.get("tool_calls") or []
        mensajes.append({"role": "assistant", "content": contenido, **({"tool_calls": llamadas} if llamadas else {})})
        if not llamadas:
            registro.evento("sin_llamadas", paso=paso, texto=contenido[:500])
            mensajes.append({"role": "user", "content": RECORDATORIO})
            continue
        for indice, llamada in enumerate(llamadas):
            fin = _atender(llamada, indice, paso, dominio, fichas, config, registro, mensajes, vistos)
            if fin is not None:
                return fin
    return Fin("tope_pasos", None, frenos["max_pasos"], f"se llegó al tope de {frenos['max_pasos']} pasos")
```

- [ ] **Paso 4: correr los tests**

`python -m uv run pytest tests/test_bucle.py -q`. Lo esperado: todos PASS. Si `test_herramientas_que_fallan_o_no_encuentran[lenta]` tarda unos 2 s, es normal: el hilo de la función lenta termina en segundo plano.

- [ ] **Paso 5: commit**

```powershell
git add harness/__init__.py harness/bucle.py tests/test_bucle.py
git commit -m "Loop del agente compartido entre dominios, con tests sobre un LLM falso" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tarea 4: dominio Mundial, `agente.py` y `correr_todas.py`

**Archivos:**
- Crear: `harness/dominios.py`
- Modificar: `agente.py`, `correr_todas.py:46-50` (función `correr_tarea`)
- Modificar: `tests/test_agente.py`

**Interfaces:**
- Consume: `harness.bucle.Dominio`, `harness.bucle.bucle` y `harness.bucle.Fin` (Tarea 3); `herramientas.mundial.FICHAS` y `herramientas.mundial.HERRAMIENTAS` (kit).
- Produce:
  - `harness.dominios.construir(nombre: str) -> Dominio`, con `nombre in DOMINIOS`;
  - `harness.dominios.DOMINIOS: tuple[str, ...]`, que en esta etapa es `("mundial",)`;
  - CLI: `agente.py -p ... [--tarea] [--log] [--config] [--dominio mundial]`. Sale con código 0 si el loop devolvió un `Fin` (con cualquier estado) y con 1 si hubo una excepción inesperada. En los dos casos cierra la traza con `corrida_fin` y `motivo`;
  - `correr_todas.correr_tarea(tarea, carpeta, agente, python, timeout_s, config=None, dominio=None) -> dict`.

- [ ] **Paso 1: reescribir `tests/test_agente.py`**

El esqueleto ya no existe. Ahora el agente, sin servidor, reintenta y termina con estado `error` y una traza válida. Para que el test sea rápido se usa una configuración con espera 0.

```python
"""agente.py de punta a punta sin servidor: reintenta, cierra la traza con error y no inventa nada."""
import json
import subprocess
import sys
from pathlib import Path

import correr_todas
import evaluar
from tests.ayudas import leer
from trazas import esquema
from trazas.registro import SinRegistro

RAIZ = Path(__file__).resolve().parent.parent


def _config_rapida(tmp_path) -> Path:
    texto = (RAIZ / "config.toml").read_text(encoding="utf-8").replace("espera_reintento_s = 2.0",
                                                                       "espera_reintento_s = 0")
    ruta = tmp_path / "rapida.toml"
    ruta.write_text(texto, encoding="utf-8")
    return ruta


def _correr(*argumentos):
    return subprocess.run([sys.executable, str(RAIZ / "agente.py"), *argumentos], capture_output=True,
                          text=True, cwd=RAIZ, timeout=60,
                          env={"PATH": "", "SYSTEMROOT": "", "OLLAMA_HOST": "127.0.0.1:1"})


def test_sin_servidor_reintenta_y_cierra_con_error(tmp_path):
    proceso = _correr("-p", "¿Cuántos?", "--tarea", "mun-001", "--log", str(tmp_path / "c"),
                      "--config", str(_config_rapida(tmp_path)))
    assert proceso.returncode == 0
    ruta = tmp_path / "c" / "mun-001.jsonl"
    assert esquema.validar_archivo(ruta) == []
    eventos = leer(ruta)
    assert [e["evento"] for e in eventos].count("reintento_modelo") == 3
    assert eventos[-1]["estado"] == "error" and eventos[-1]["respuesta"] is None
    assert "reintentos" in eventos[-1]["motivo"]


def test_la_traza_registra_la_configuracion_y_el_dominio(tmp_path):
    _correr("-p", "?", "--tarea", "t", "--log", str(tmp_path / "c"), "--config", str(_config_rapida(tmp_path)))
    inicio = leer(tmp_path / "c" / "t.jsonl")[0]
    assert inicio["modelo"] == "qwen3:8b"
    assert inicio["config"]["modelo"]["num_ctx"] == 8192
    assert inicio["config"]["dominio"] == "mundial"
    assert inicio["config"]["ollama_version"] is None and inicio["config"]["modelo_digest"] is None


def test_sin_log_no_escribe_trazas(tmp_path):
    proceso = _correr("-p", "?", "--config", str(_config_rapida(tmp_path)))
    assert proceso.returncode == 0
    assert [p.name for p in tmp_path.iterdir()] == ["rapida.toml"]


def test_una_config_invalida_falla_antes_de_correr(tmp_path):
    roto = tmp_path / "roto.toml"
    roto.write_text("[modelo]\nnombre = 'qwen3:8b'\n", encoding="utf-8")
    proceso = _correr("-p", "?", "--config", str(roto))
    assert proceso.returncode != 0 and "falta" in proceso.stderr


def test_dominio_desconocido_falla(tmp_path):
    proceso = _correr("-p", "?", "--dominio", "ajedrez")
    assert proceso.returncode != 0 and "ajedrez" in proceso.stderr


def test_correr_todas_y_evaluar_de_punta_a_punta_sin_servidor(tmp_path, monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "127.0.0.1:1")   # correr_tarea hereda el entorno
    tareas = json.loads(evaluar.TAREAS.read_text(encoding="utf-8"))[:2]
    carpeta = tmp_path / "corrida"
    config = _config_rapida(tmp_path)
    for tarea in tareas:
        resultado = correr_todas.correr_tarea(tarea, carpeta, RAIZ / "agente.py", sys.executable, 60, config,
                                              dominio="mundial")
        assert resultado["estado"] == "ok"
    filas, resumen = evaluar.evaluar(tareas, carpeta, evaluar.PESOS)
    assert resumen["aciertos"] == 0
    assert {f["resultado"] for f in filas} == {"sin_respuesta"}


def test_sin_registro_acepta_eventos_y_no_escribe():
    assert SinRegistro().evento("corrida_inicio", modelo="x")["evento"] == "corrida_inicio"
```

- [ ] **Paso 2: correr y ver que falla**

`python -m uv run pytest tests/test_agente.py -q`. Lo esperado: FAIL. El agente todavía es el esqueleto y no conoce `--dominio`.

- [ ] **Paso 3: escribir `harness/dominios.py`**

```python
"""Los dominios del agente: qué herramientas ve el modelo y con qué instrucciones.

El loop (`harness/bucle.py`) es el mismo para todos; acá cambia solo lo propio de cada uno.
"""
from harness.bucle import Dominio
from herramientas import mundial

SISTEMA_MUNDIAL = """Sos un agente que responde preguntas sobre los Mundiales de fútbol usando solo las herramientas.

Reglas:
1. Cada número, nombre o fecha de tu respuesta tiene que salir de un resultado de herramienta. No respondas de memoria.
2. En las herramientas, los nombres de las selecciones van en inglés (Argentina, Germany, Brazil, Netherlands).
3. Si un jugador es ambiguo, la herramienta te devuelve candidatos con su id: usá el id, no repitas el nombre.
4. Para cuentas y diferencias entre fechas usá `calcular`; no hagas cuentas de cabeza.
5. Cuando tengas la respuesta, llamá a terminar(respuesta, motivo) con la respuesta en el formato que pide la pregunta y, en el motivo, de qué resultado sale.
6. Si los datos de las herramientas no alcanzan para responder, llamá a terminar con respuesta null y decí en el motivo qué dato falta. No inventes.
7. Contestá siempre llamando a una herramienta; nunca con texto suelto."""

DOMINIOS = ("mundial",)


def construir(nombre: str) -> Dominio:
    if nombre == "mundial":
        return Dominio("mundial", SISTEMA_MUNDIAL, mundial.FICHAS, mundial.HERRAMIENTAS)
    raise ValueError(f"dominio desconocido: {nombre!r}. Los que hay: {', '.join(DOMINIOS)}")
```

- [ ] **Paso 4: reescribir `agente.py`**

Hay que reemplazar el docstring, `bucle` y `main`; `entorno_del_servidor` queda igual. El archivo completo queda así:

```python
"""El agente: recibe una pregunta y la responde llamando herramientas.

    uv run agente.py -p "¿Qué edad tenía el goleador del Mundial 1978 el día de la final?" --log trazas/mi_corrida
    uv run agente.py -p "..." --tarea mun-024 --log trazas/mi_corrida --config config.toml --dominio mundial

El loop vive en `harness/bucle.py` y es el mismo para todos los dominios; `harness/dominios.py` arma
las herramientas y el prompt de cada uno. Este archivo lee y valida la configuración, abre la traza,
escribe `corrida_inicio` (con la configuración, el dominio y la versión de Ollama) y `corrida_fin`.
"""
import argparse
import sys
import traceback
from pathlib import Path

import config as configuracion
import llm
from harness import bucle as harness_bucle
from harness import dominios
from trazas.registro import Registro, SinRegistro

RAIZ = Path(__file__).resolve().parent


def bucle(pregunta: str, config: dict, registro, dominio: str = "mundial") -> harness_bucle.Fin:
    return harness_bucle.bucle(pregunta, config, registro, dominios.construir(dominio))


def entorno_del_servidor(modelo: str) -> dict:
    """La versión de Ollama y el digest del modelo; null si el servidor no responde."""
    try:
        return {"ollama_version": llm.version(), "modelo_digest": llm.digest(modelo)}
    except llm.LLMError:
        return {"ollama_version": None, "modelo_digest": None}


def main() -> int:
    parser = argparse.ArgumentParser(description="Responde una pregunta llamando herramientas.")
    parser.add_argument("-p", "--pregunta", required=True)
    parser.add_argument("--tarea", help="id de la tarea, para la traza")
    parser.add_argument("--log", type=Path, help="carpeta de trazas; sin esto no se escribe ninguna")
    parser.add_argument("--config", type=Path, default=configuracion.CONFIG)
    parser.add_argument("--dominio", default="mundial", choices=dominios.DOMINIOS)
    argumentos = parser.parse_args()

    config = configuracion.cargar(argumentos.config)
    registro = Registro(argumentos.log, argumentos.tarea) if argumentos.log else SinRegistro()
    modelo = config["modelo"]["nombre"]
    registro.evento("corrida_inicio", modelo=modelo,
                    config=config | {"dominio": argumentos.dominio} | entorno_del_servidor(modelo))
    try:
        fin = bucle(argumentos.pregunta, config, registro, argumentos.dominio)
    except Exception as error:  # noqa: BLE001 (la traza tiene que cerrarse pase lo que pase)
        registro.evento("corrida_fin", estado="error", respuesta=None, pasos=0,
                        motivo=f"{type(error).__name__}: {error}", detalle=traceback.format_exc()[-2000:])
        print(traceback.format_exc(), file=sys.stderr)
        return 1
    registro.evento("corrida_fin", estado=fin.estado, respuesta=fin.respuesta, pasos=fin.pasos, motivo=fin.motivo)
    print(fin.respuesta if fin.respuesta is not None else f"({fin.estado}: {fin.motivo})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Paso 5: agregar `dominio` a `correr_todas.correr_tarea`**

En `correr_todas.py`, cambiar la firma y el armado de la orden:

```python
def correr_tarea(tarea: dict, carpeta: Path, agente: Path, python: str, timeout_s: float,
                 config: Path | None = None, dominio: str | None = None) -> dict:
    carpeta.mkdir(parents=True, exist_ok=True)
    orden = [python, str(agente), "-p", pregunta_con_formato(tarea), "--tarea", tarea["id"], "--log", str(carpeta)]
    if config:
        orden += ["--config", str(config)]
    if dominio:
        orden += ["--dominio", dominio]
```

En `main`, agregar `parser.add_argument("--dominio", help="dominio del agente (por defecto, el de agente.py)")` y pasar `argumentos.dominio` como último argumento de `correr_tarea`.

- [ ] **Paso 6: correr toda la suite**

`python -m uv run pytest -q`. Lo esperado: todo PASS, incluidos `test_correr_todas.py` (su agente falso no recibe `--dominio` porque se pasa `None`) y `test_bucle.py`.

- [ ] **Paso 7: commit**

```powershell
git add harness/dominios.py agente.py correr_todas.py tests/test_agente.py
git commit -m "agente.py usa el loop compartido; dominio mundial y --dominio en el runner" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tarea 5: corridas en Drive que se pueden retomar (`harness/corridas.py`)

**Archivos:**
- Crear: `harness/corridas.py`
- Test: `tests/test_corridas.py`

**Interfaces:**
- Consume: `trazas.esquema.validar_archivo`, `correr_todas.correr_tarea(..., dominio=)` (Tarea 4) y `libro_cerrado.responder_tarea` (kit).
- Produce:
  - `nombre_corrida(conjunto: str, config: str, temperatura: float, semilla: int) -> str`, que da por ejemplo `"mundial__agente-antes__t0__s1337"`;
  - `config_con(base: dict, **modelo) -> dict`, que devuelve una copia con las claves de `[modelo]` cambiadas;
  - `a_toml(config: dict) -> str`;
  - `class CommitDistinto(RuntimeError)` y `class TandaTomada(RuntimeError)`;
  - `preparar(destino: Path, manifiesto: dict) -> dict`;
  - `hecha(destino: Path, tarea_id: str) -> bool`;
  - `tomar(destino: Path, quien: str, *, ahora: float | None = None, vigencia_h: float = 2.0) -> None`;
  - `latido(destino: Path, quien: str, *, ahora: float | None = None) -> None`;
  - `copiar_traza(trabajo: Path, destino: Path, tarea_id: str) -> None`;
  - `estado(destino: Path, tareas: list[dict], *, ahora: float | None = None) -> dict`, con las claves `en_drive`, `total`, `tomada_por` y `hace_min`;
  - `correr_tanda(tareas, destino, trabajo, correr_una, *, manifiesto, quien, antes_de_cada=None, al_avanzar=print) -> dict`, con las claves `tareas`, `en_drive`, `corridas_ahora` y `completa`;
  - `corredor_agente(config_path: Path, dominio: str, timeout_s: float = 600) -> Callable[[dict, Path], None]`;
  - `corredor_libro_cerrado(config: dict) -> Callable[[dict, Path], None]`.

- [ ] **Paso 1: escribir los tests**

`tests/test_corridas.py`:

```python
"""Corridas en Drive: copia atómica, retomar, commit fijado y tandas tomadas."""
import json

import pytest

from harness import corridas
from trazas.registro import Registro

TAREAS = [{"id": "t-1"}, {"id": "t-2"}, {"id": "t-3"}]
MANIFIESTO = {"commit": "aaaa1111", "corrida": "x"}


def _corredor(fallar_en=None, llamadas=None):
    """Un corredor falso que escribe una traza válida (o la deja abierta en `fallar_en`)."""
    def correr(tarea, trabajo):
        if llamadas is not None:
            llamadas.append(tarea["id"])
        registro = Registro(trabajo, tarea["id"])
        registro.evento("corrida_inicio", modelo="qwen3:8b", config={"num_ctx": 8192})
        if tarea["id"] == fallar_en:
            raise KeyboardInterrupt("se cortó la sesión")
        registro.evento("corrida_fin", estado="respondida", respuesta="1", pasos=1)
    return correr


def test_nombre_corrida():
    assert corridas.nombre_corrida("mundial", "agente-antes", 0, 1337) == "mundial__agente-antes__t0__s1337"
    assert corridas.nombre_corrida("congelado", "plan", 0.7, 1338) == "congelado__plan__t0.7__s1338"


def test_corre_todo_y_suelta_la_tanda(tmp_path):
    destino = tmp_path / "drive" / "c"
    resumen = corridas.correr_tanda(TAREAS, destino, tmp_path / "local", _corredor(), manifiesto=MANIFIESTO,
                                    quien="ana", al_avanzar=lambda m: None)
    assert resumen == {"tareas": 3, "en_drive": 3, "corridas_ahora": 3, "completa": True}
    assert sorted(p.name for p in destino.glob("*.jsonl")) == ["t-1.jsonl", "t-2.jsonl", "t-3.jsonl"]
    assert not (destino / "tomada.json").exists()
    assert not list(destino.glob("*.tmp"))
    assert json.loads((destino / "manifiesto.json").read_text(encoding="utf-8"))["commit"] == "aaaa1111"


def test_un_corte_deja_solo_trazas_completas_y_se_retoma(tmp_path):
    destino, local = tmp_path / "drive" / "c", tmp_path / "local"
    with pytest.raises(KeyboardInterrupt):
        corridas.correr_tanda(TAREAS, destino, local, _corredor(fallar_en="t-2"), manifiesto=MANIFIESTO,
                              quien="ana", al_avanzar=lambda m: None)
    assert [p.name for p in destino.glob("*.jsonl")] == ["t-1.jsonl"]
    llamadas = []
    resumen = corridas.correr_tanda(TAREAS, destino, local, _corredor(llamadas=llamadas), manifiesto=MANIFIESTO,
                                    quien="ana", al_avanzar=lambda m: None)
    assert llamadas == ["t-2", "t-3"] and resumen["completa"] and resumen["corridas_ahora"] == 2


def test_una_traza_invalida_en_drive_se_vuelve_a_correr(tmp_path):
    destino = tmp_path / "drive" / "c"
    destino.mkdir(parents=True)
    (destino / "t-1.jsonl").write_text('{"evento": "corrida_inicio"}\n', encoding="utf-8")
    assert not corridas.hecha(destino, "t-1")
    llamadas = []
    corridas.correr_tanda(TAREAS[:1], destino, tmp_path / "local", _corredor(llamadas=llamadas),
                          manifiesto=MANIFIESTO, quien="ana", al_avanzar=lambda m: None)
    assert llamadas == ["t-1"] and corridas.hecha(destino, "t-1")


def test_no_mezcla_commits(tmp_path):
    destino = tmp_path / "c"
    corridas.preparar(destino, MANIFIESTO)
    with pytest.raises(corridas.CommitDistinto, match="aaaa1111"):
        corridas.preparar(destino, {**MANIFIESTO, "commit": "bbbb2222"})


def test_tanda_tomada_por_otro(tmp_path):
    corridas.tomar(tmp_path, "ana", ahora=1000)
    with pytest.raises(corridas.TandaTomada, match="ana"):
        corridas.tomar(tmp_path, "beto", ahora=1000 + 3600)
    corridas.tomar(tmp_path, "ana", ahora=1000 + 3600)              # la misma persona puede retomar
    corridas.latido(tmp_path, "ana", ahora=5000)
    with pytest.raises(corridas.TandaTomada):
        corridas.tomar(tmp_path, "beto", ahora=5000 + 3600)
    corridas.tomar(tmp_path, "beto", ahora=5000 + 2 * 3600 + 1)     # pasaron 2 horas sin latido: abandonada


def test_estado(tmp_path):
    destino = tmp_path / "c"
    assert corridas.estado(destino, TAREAS)["en_drive"] == 0
    corridas.correr_tanda(TAREAS[:1], destino, tmp_path / "l", _corredor(), manifiesto=MANIFIESTO, quien="ana",
                          al_avanzar=lambda m: None)
    corridas.tomar(destino, "ana", ahora=100)
    info = corridas.estado(destino, TAREAS, ahora=100 + 600)
    assert (info["en_drive"], info["total"], info["tomada_por"], info["hace_min"]) == (1, 3, "ana", 10)


def test_config_con_y_a_toml(tmp_path):
    import tomllib
    base = {"modelo": {"nombre": "qwen3:8b", "temperatura": 0, "semilla": 1337, "think": False},
            "frenos": {"max_pasos": 14, "espera_reintento_s": 2.0}, "contexto": {"tope_resultado_caracteres": 4000}}
    cambiada = corridas.config_con(base, temperatura=0.7, semilla=1338)
    assert base["modelo"]["temperatura"] == 0
    assert tomllib.loads(corridas.a_toml(cambiada)) == cambiada
```

- [ ] **Paso 2: correr y ver que falla**

`python -m uv run pytest tests/test_corridas.py -q`. Lo esperado: falla con `ImportError: cannot import name 'corridas'`.

- [ ] **Paso 3: implementar `harness/corridas.py`**

```python
"""Corridas en Drive que se pueden retomar.

Una corrida es una carpeta en Drive con una traza por tarea. Cada tarea corre en el disco local de
Colab y, cuando su traza se cerró, se copia a Drive con un nombre provisorio y se renombra: en Drive
nunca queda una traza a medias. Para retomar se vuelve a llamar a `correr_tanda`: saltea las tareas que
ya tienen en Drive una traza que pasa el validador del kit.

`manifiesto.json` fija el commit con que se corrió: retomar con otro commit es un error, para no mezclar
versiones del harness en una medición. `tomada.json` avisa que alguien está corriendo esa tanda.
"""
import copy
import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Callable

import correr_todas
import libro_cerrado
from trazas import esquema

RAIZ = Path(__file__).resolve().parent.parent


class CommitDistinto(RuntimeError):
    pass


class TandaTomada(RuntimeError):
    pass


def nombre_corrida(conjunto: str, config: str, temperatura: float, semilla: int) -> str:
    return f"{conjunto}__{config}__t{temperatura:g}__s{semilla}"


def config_con(base: dict, **modelo) -> dict:
    nueva = copy.deepcopy(base)
    nueva["modelo"].update(modelo)
    return nueva


def _valor_toml(valor) -> str:
    if isinstance(valor, bool):
        return "true" if valor else "false"
    if isinstance(valor, (int, float)):
        return repr(valor)
    if isinstance(valor, str):
        return json.dumps(valor, ensure_ascii=False)
    raise TypeError(f"no sé escribir en TOML: {valor!r}")


def a_toml(config: dict) -> str:
    """Solo lo que usa config.toml: secciones con valores sueltos."""
    lineas = []
    for seccion, claves in config.items():
        lineas.append(f"[{seccion}]")
        lineas += [f"{clave} = {_valor_toml(valor)}" for clave, valor in claves.items()]
        lineas.append("")
    return "\n".join(lineas)


def _escribir_atomico(ruta: Path, texto: str) -> None:
    provisorio = ruta.with_name(ruta.name + ".tmp")
    provisorio.write_text(texto, encoding="utf-8")
    os.replace(provisorio, ruta)


def _leer_json(ruta: Path) -> dict:
    return json.loads(ruta.read_text(encoding="utf-8"))


def preparar(destino: Path, manifiesto: dict) -> dict:
    destino.mkdir(parents=True, exist_ok=True)
    ruta = destino / "manifiesto.json"
    if ruta.exists():
        previo = _leer_json(ruta)
        if previo["commit"] != manifiesto["commit"]:
            raise CommitDistinto(
                f"La corrida {destino.name} empezó con el commit {previo['commit'][:8]} y ahora el código está en "
                f"{manifiesto['commit'][:8]}. Para retomarla: git checkout {previo['commit'][:8]}. Si no, empezá "
                f"una corrida nueva con otro nombre.")
        return previo
    _escribir_atomico(ruta, json.dumps(manifiesto, ensure_ascii=False, indent=2))
    return manifiesto


def hecha(destino: Path, tarea_id: str) -> bool:
    ruta = destino / f"{tarea_id}.jsonl"
    return ruta.exists() and not esquema.validar_archivo(ruta)


def tomar(destino: Path, quien: str, *, ahora: float | None = None, vigencia_h: float = 2.0) -> None:
    ahora = time.time() if ahora is None else ahora
    destino.mkdir(parents=True, exist_ok=True)
    ruta = destino / "tomada.json"
    if ruta.exists():
        previa = _leer_json(ruta)
        hace = ahora - previa["latido"]
        if previa["quien"] != quien and hace < vigencia_h * 3600:
            raise TandaTomada(f"La tanda {destino.name} la está corriendo {previa['quien']} (último avance hace "
                              f"{hace / 60:.0f} min). Elegí otra.")
    _escribir_atomico(ruta, json.dumps({"quien": quien, "inicio": ahora, "latido": ahora}))


def latido(destino: Path, quien: str, *, ahora: float | None = None) -> None:
    ruta = destino / "tomada.json"
    datos = _leer_json(ruta) if ruta.exists() else {"quien": quien, "inicio": ahora}
    datos |= {"quien": quien, "latido": time.time() if ahora is None else ahora}
    _escribir_atomico(ruta, json.dumps(datos))


def copiar_traza(trabajo: Path, destino: Path, tarea_id: str) -> None:
    """La salida primero y la traza al final: si hay .jsonl en Drive, la tarea terminó."""
    for sufijo in (".salida.txt", ".jsonl"):
        origen = trabajo / f"{tarea_id}{sufijo}"
        if origen.exists():
            provisorio = destino / f"{tarea_id}{sufijo}.tmp"
            shutil.copyfile(origen, provisorio)
            os.replace(provisorio, destino / f"{tarea_id}{sufijo}")


def estado(destino: Path, tareas: list[dict], *, ahora: float | None = None) -> dict:
    ahora = time.time() if ahora is None else ahora
    en_drive = sum(hecha(destino, t["id"]) for t in tareas) if destino.exists() else 0
    tomada = destino / "tomada.json"
    datos = _leer_json(tomada) if tomada.exists() else None
    return {"en_drive": en_drive, "total": len(tareas), "tomada_por": datos["quien"] if datos else None,
            "hace_min": round((ahora - datos["latido"]) / 60) if datos else None}


def correr_tanda(tareas: list[dict], destino: Path, trabajo: Path, correr_una: Callable[[dict, Path], None], *,
                 manifiesto: dict, quien: str, antes_de_cada: Callable[[], None] | None = None,
                 al_avanzar: Callable[[str], None] = print) -> dict:
    preparar(destino, manifiesto)
    tomar(destino, quien)
    trabajo.mkdir(parents=True, exist_ok=True)
    corridas_ahora = 0
    for tarea in tareas:
        if hecha(destino, tarea["id"]):
            continue
        if antes_de_cada:
            antes_de_cada()
        correr_una(tarea, trabajo)
        copiar_traza(trabajo, destino, tarea["id"])
        latido(destino, quien)
        corridas_ahora += 1
        listas = sum(hecha(destino, t["id"]) for t in tareas)
        al_avanzar(f"{tarea['id']}: lista · {listas}/{len(tareas)} en Drive")
    en_drive = sum(hecha(destino, t["id"]) for t in tareas)
    completa = en_drive == len(tareas)
    if completa:
        (destino / "tomada.json").unlink(missing_ok=True)
    return {"tareas": len(tareas), "en_drive": en_drive, "corridas_ahora": corridas_ahora, "completa": completa}


def corredor_agente(config_path: Path, dominio: str, timeout_s: float = 600) -> Callable[[dict, Path], None]:
    def correr(tarea: dict, trabajo: Path) -> None:
        correr_todas.correr_tarea(tarea, trabajo, RAIZ / "agente.py", sys.executable, timeout_s, config_path,
                                  dominio=dominio)
    return correr


def corredor_libro_cerrado(config: dict) -> Callable[[dict, Path], None]:
    modelo = config["modelo"]

    def correr(tarea: dict, trabajo: Path) -> None:
        libro_cerrado.responder_tarea(tarea, trabajo, modelo=modelo["nombre"], num_ctx=modelo["num_ctx"],
                                      temperatura=modelo["temperatura"], semilla=modelo["semilla"])
    return correr
```

- [ ] **Paso 4: correr los tests**

`python -m uv run pytest tests/test_corridas.py -q`. Lo esperado: PASS.

- [ ] **Paso 5: commit**

```powershell
git add harness/corridas.py tests/test_corridas.py
git commit -m "Corridas en Drive retomables: copia atómica, manifiesto con commit y tandas tomadas" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tarea 6: traza legible (`harness/ver_traza.py`)

**Archivos:**
- Crear: `harness/ver_traza.py`
- Test: `tests/test_ver_traza.py`

**Interfaces:**
- Consume: los eventos que escribe `harness/bucle.py` (Tarea 3), incluidos los campos extra `texto`, `contenido` y `motivo`.
- Produce:
  - `resumen(ruta: Path, *, ancho: int = 160) -> str`: una línea por evento;
  - `comparar(ruta_a: Path, ruta_b: Path, *, ancho: int = 70) -> str`: dos columnas, para el arreglo del Bloque 1.

- [ ] **Paso 1: escribir el test**

```python
"""La traza legible que muestran los notebooks."""
from harness import ver_traza
from trazas.registro import Registro


def _traza(carpeta, respuesta):
    r = Registro(carpeta, "mun-001")
    r.evento("corrida_inicio", modelo="qwen3:8b", config={"modelo": {"num_ctx": 8192}})
    r.evento("llamada_modelo", paso=1, modelo="qwen3:8b", num_ctx=8192, tokens_entrada=900, tokens_salida=40,
             duracion_ms=1200, texto="")
    r.evento("llamada_herramienta", paso=1, id="p1-1", nombre="goleadores", argumentos={"torneo": 1978})
    r.evento("resultado_herramienta", paso=1, id="p1-1", ok=True, truncado=False, caracteres=30, duracion_ms=4,
             contenido='[{"jugador": "Mario Kempes", "goles": 6}]')
    r.evento("corrida_fin", estado="respondida", respuesta=respuesta, pasos=1, motivo="goleadores 1978")
    return r.ruta


def test_resumen_muestra_cada_paso(tmp_path):
    texto = ver_traza.resumen(_traza(tmp_path, "6"))
    assert "modelo · 900 → 40 tokens · 1.2 s" in texto
    assert 'goleadores({"torneo": 1978})' in texto
    assert "Mario Kempes" in texto
    assert "FIN respondida · respuesta: '6' · motivo: goleadores 1978" in texto


def test_comparar_pone_dos_trazas_lado_a_lado(tmp_path):
    texto = ver_traza.comparar(_traza(tmp_path / "a", "5"), _traza(tmp_path / "b", "6"))
    assert "'5'" in texto and "'6'" in texto and " | " in texto
```

- [ ] **Paso 2: correr y ver que falla**

`python -m uv run pytest tests/test_ver_traza.py -q`. Lo esperado: falla con `ImportError`.

- [ ] **Paso 3: implementar**

```python
"""Una traza JSONL en texto legible, para mirarla en los notebooks."""
import json
from itertools import zip_longest
from pathlib import Path


def _corto(texto, ancho: int) -> str:
    texto = " ".join(str(texto).split())
    return texto if len(texto) <= ancho else texto[: ancho - 1] + "…"


def _linea(e: dict, ancho: int) -> str:
    tipo, paso = e["evento"], e.get("paso")
    pre = f"[{paso}] " if paso is not None else ""
    if tipo == "corrida_inicio":
        config = e.get("config", {})
        num_ctx = config.get("modelo", {}).get("num_ctx", config.get("num_ctx"))
        return f"INICIO {e['tarea']} · {e['modelo']} · num_ctx {num_ctx}"
    if tipo == "llamada_modelo":
        extra = f" · escribió: {_corto(e['texto'], ancho // 2)}" if e.get("texto") else ""
        return f"{pre}modelo · {e['tokens_entrada']} → {e['tokens_salida']} tokens · {e['duracion_ms'] / 1000:.1f} s{extra}"
    if tipo == "llamada_herramienta":
        argumentos = e["argumentos"] if isinstance(e["argumentos"], str) else json.dumps(e["argumentos"], ensure_ascii=False)
        return f"{pre}→ {e['nombre']}({argumentos})"
    if tipo == "resultado_herramienta":
        marca = "ok" if e["ok"] else "ERROR"
        recorte = " (recortado)" if e["truncado"] else ""
        return f"{pre}← {marca}{recorte} {e['caracteres']} car.: {_corto(e.get('contenido', ''), ancho)}"
    if tipo == "reintento_modelo":
        return f"{pre}reintento {e['intento']}: {_corto(e['motivo'], ancho)}"
    if tipo == "sin_llamadas":
        return f"{pre}sin llamadas, escribió: {_corto(e['texto'], ancho)}"
    if tipo == "corrida_fin":
        return f"FIN {e['estado']} · respuesta: {e['respuesta']!r} · motivo: {e.get('motivo')}"
    return f"{pre}{tipo}"


def _lineas(ruta: Path, ancho: int) -> list[str]:
    eventos = [json.loads(l) for l in Path(ruta).read_text(encoding="utf-8").splitlines() if l.strip()]
    return [_linea(e, ancho) for e in eventos]


def resumen(ruta: Path, *, ancho: int = 160) -> str:
    return "\n".join(_lineas(ruta, ancho))


def comparar(ruta_a: Path, ruta_b: Path, *, ancho: int = 70) -> str:
    filas = zip_longest(_lineas(ruta_a, ancho), _lineas(ruta_b, ancho), fillvalue="")
    return "\n".join(f"{_corto(a, ancho):<{ancho}} | {_corto(b, ancho)}" for a, b in filas)
```

- [ ] **Paso 4: correr los tests**

`python -m uv run pytest tests/test_ver_traza.py -q`. Lo esperado: PASS.

- [ ] **Paso 5: commit**

```powershell
git add harness/ver_traza.py tests/test_ver_traza.py
git commit -m "Traza legible para los notebooks" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tarea 7: entorno de Colab y generador de notebooks

**Archivos:**
- Crear: `colab/__init__.py` (vacío), `colab/entorno.py`, `colab/construir.py`
- Test: `tests/test_notebooks.py` (en esta tarea solo prueba el constructor)

**Interfaces:**
- Produce:
  - `colab.entorno.DRIVE: Path`, `colab.entorno.OLLAMA_VERSION = "0.40.10"`;
  - `rutas() -> dict[str, Path]`, con las claves `corridas`, `resultados`, `registros` y `trabajo`;
  - `preparar(gpu: bool = True) -> dict`, que devuelve el informe de chequeos;
  - `asegurar_ollama() -> None`;
  - `commit_actual() -> str`;
  - `manifiesto(corrida: str, conjunto: str, config: dict, tareas: list[dict]) -> dict`;
  - `colab.construir.notebook(celdas: list[tuple[str, str]]) -> dict`;
  - `colab.construir.construir_todos(carpeta: Path = COLAB) -> list[Path]`, que lee cada `colab/fuentes/nb*.py` con sus variables `NOMBRE: str` y `CELDAS: list[tuple[str, str]]`, donde el tipo es `"md"` o `"code"`.

- [ ] **Paso 1: escribir el test del constructor**

`tests/test_notebooks.py`:

```python
"""Los notebooks se generan desde colab/fuentes y cada celda de código es Python válido."""
import ast
import json

from colab import construir


def _python(fuente: str) -> str:
    """Saca las líneas de shell (!) y las mágicas (%), que no son Python."""
    return "\n".join("" if l.lstrip().startswith(("!", "%")) else l for l in fuente.splitlines())


def test_notebook_arma_celdas():
    nb = construir.notebook([("md", "# Título"), ("code", "x = 1\nprint(x)")])
    assert nb["nbformat"] == 4 and nb["metadata"]["accelerator"] == "GPU"
    assert [c["cell_type"] for c in nb["cells"]] == ["markdown", "code"]
    assert nb["cells"][1]["source"] == ["x = 1\n", "print(x)"]


def test_todos_los_notebooks_generados_son_validos(tmp_path):
    rutas = construir.construir_todos(tmp_path)
    assert rutas, "no hay fuentes en colab/fuentes"
    for ruta in rutas:
        nb = json.loads(ruta.read_text(encoding="utf-8"))
        assert nb["cells"][0]["cell_type"] == "markdown"
        for celda in nb["cells"]:
            if celda["cell_type"] == "code":
                ast.parse(_python("".join(celda["source"])))
```

- [ ] **Paso 2: correr y ver que falla**

`python -m uv run pytest tests/test_notebooks.py -q`. Lo esperado: falla con `ModuleNotFoundError: No module named 'colab'`.

- [ ] **Paso 3: escribir `colab/construir.py`**

```python
"""Genera los notebooks de Colab a partir de colab/fuentes/nb*.py.

    uv run colab/construir.py

Cada fuente define NOMBRE (el archivo .ipynb) y CELDAS, una lista de ("md" | "code", texto). Así los
notebooks se revisan como código y se regeneran sin editar JSON a mano.
"""
import importlib.util
import json
from pathlib import Path

COLAB = Path(__file__).resolve().parent


def _lineas(texto: str) -> list[str]:
    partes = texto.strip("\n").split("\n")
    return [p + "\n" for p in partes[:-1]] + [partes[-1]]


def notebook(celdas: list[tuple[str, str]]) -> dict:
    cuerpo = []
    for tipo, texto in celdas:
        if tipo == "md":
            cuerpo.append({"cell_type": "markdown", "metadata": {}, "source": _lineas(texto)})
        elif tipo == "code":
            cuerpo.append({"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
                           "source": _lineas(texto)})
        else:
            raise ValueError(f"tipo de celda desconocido: {tipo}")
    return {"nbformat": 4, "nbformat_minor": 5, "cells": cuerpo,
            "metadata": {"accelerator": "GPU", "colab": {"provenance": [], "gpuType": "T4"},
                         "kernelspec": {"name": "python3", "display_name": "Python 3"},
                         "language_info": {"name": "python"}}}


def _cargar(ruta: Path):
    spec = importlib.util.spec_from_file_location(ruta.stem, ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def construir_todos(carpeta: Path = COLAB) -> list[Path]:
    rutas = []
    for fuente in sorted((COLAB / "fuentes").glob("nb*.py")):
        modulo = _cargar(fuente)
        ruta = Path(carpeta) / modulo.NOMBRE
        ruta.write_text(json.dumps(notebook(modulo.CELDAS), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        rutas.append(ruta)
    return rutas


if __name__ == "__main__":
    for ruta in construir_todos():
        print("escrito", ruta)
```

- [ ] **Paso 4: escribir `colab/entorno.py`**

```python
"""El entorno de Colab, igual para todos los notebooks: Drive, Ollama, el modelo y los chequeos.

Se usa después de la primera celda de cada notebook (que monta Drive y clona el repo):

    from colab import entorno
    informe = entorno.preparar(gpu=True)
"""
import datetime as dt
import os
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path

import config as configuracion
import llm

DRIVE = Path(os.environ.get("TPFINAL_DRIVE", "/content/drive/MyDrive/TPFinal-heladera"))
OLLAMA_VERSION = "0.40.10"
RAIZ = Path(__file__).resolve().parent.parent


def rutas() -> dict[str, Path]:
    carpetas = {"corridas": DRIVE / "corridas", "resultados": DRIVE / "resultados",
                "registros": DRIVE / "registros", "trabajo": Path("/content/trabajo")}
    for carpeta in carpetas.values():
        carpeta.mkdir(parents=True, exist_ok=True)
    return carpetas


def _sh(orden: str) -> None:
    subprocess.run(orden, shell=True, check=True)


def ollama_vivo() -> bool:
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=2):
            return True
    except OSError:
        return False


def instalar_ollama(version: str = OLLAMA_VERSION) -> None:
    instalada = shutil.which("ollama") and version in subprocess.run(
        ["ollama", "--version"], capture_output=True, text=True).stdout
    if not instalada:
        _sh("apt-get -qq update && apt-get -qq install -y zstd > /dev/null")
        _sh(f"curl -fsSL https://ollama.com/install.sh | OLLAMA_VERSION={version} sh")


def asegurar_ollama() -> None:
    """Levanta el servidor si no responde. Se llama antes de cada tarea: Colab a veces lo mata."""
    if ollama_vivo():
        return
    os.environ.update({"OLLAMA_HOST": "127.0.0.1:11434", "OLLAMA_MAX_LOADED_MODELS": "1", "OLLAMA_NUM_PARALLEL": "1"})
    log = open(rutas()["registros"] / f"ollama_{dt.date.today()}.log", "a")
    subprocess.Popen(["ollama", "serve"], start_new_session=True, stdout=log, stderr=subprocess.STDOUT)
    for _ in range(60):
        if ollama_vivo():
            return
        time.sleep(1)
    raise RuntimeError("Ollama no levantó: mirá el log en TPFinal-heladera/registros/")


def commit_actual() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=RAIZ,
                          check=True).stdout.strip()


def cambios_sin_commit() -> bool:
    return bool(subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, cwd=RAIZ,
                               check=True).stdout.strip())


def preparar(gpu: bool = True) -> dict:
    rutas()
    informe = {"commit": commit_actual(), "cambios_sin_commit": cambios_sin_commit(), "drive": str(DRIVE)}
    if gpu:
        instalar_ollama()
        asegurar_ollama()
        modelo = configuracion.cargar()["modelo"]["nombre"]
        subprocess.run(["ollama", "pull", modelo], check=True)
        respuesta = llm.chat([{"role": "user", "content": "Respondé solo con la palabra: listo"}], modelo=modelo,
                             num_ctx=configuracion.cargar()["modelo"]["num_ctx"], num_predict=20)
        ps = subprocess.run(["ollama", "ps"], capture_output=True, text=True).stdout
        informe |= {"ollama": llm.version(), "ollama_esperada": OLLAMA_VERSION, "modelo": modelo,
                    "digest": llm.digest(modelo), "prueba": respuesta.mensaje.get("content", "").strip(),
                    "gpu_100": "100% GPU" in ps}
    for clave, valor in informe.items():
        print(f"{clave:>18}: {valor}")
    if informe["cambios_sin_commit"]:
        print("ATENCIÓN: hay cambios sin commit en la copia de Colab; las corridas registran el commit, no esos cambios.")
    if gpu and not informe["gpu_100"]:
        print("ATENCIÓN: el modelo no corre 100% en la GPU. Los tiempos no sirven para comparar.")
    if gpu and informe["ollama"] != OLLAMA_VERSION:
        print("ATENCIÓN: la versión de Ollama no es la del kit; hay que declararlo en el informe.")
    return informe


def manifiesto(corrida: str, conjunto: str, config: dict, tareas: list[dict]) -> dict:
    modelo = config["modelo"]["nombre"]
    try:
        servidor = {"ollama": llm.version(), "digest": llm.digest(modelo)}
    except llm.LLMError:
        servidor = {"ollama": None, "digest": None}
    return {"corrida": corrida, "conjunto": conjunto, "commit": commit_actual(), "config": config,
            "tareas": [t["id"] for t in tareas], "creada": dt.datetime.now(dt.timezone.utc).isoformat(), **servidor}
```

- [ ] **Paso 5: correr el test del constructor**

`python -m uv run pytest tests/test_notebooks.py::test_notebook_arma_celdas -q`. Lo esperado: PASS. El otro test falla hasta que exista una fuente, en la Tarea 8.

- [ ] **Paso 6: commit**

```powershell
git add colab/__init__.py colab/entorno.py colab/construir.py tests/test_notebooks.py
git commit -m "Entorno de Colab y generador de notebooks desde fuentes Python" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tarea 8: notebook `01_bloque1_mundial`

**Archivos:**
- Crear: `colab/fuentes/nb01_bloque1_mundial.py`
- Generado: `colab/01_bloque1_mundial.ipynb`

**Interfaces:**
- Consume: `colab.entorno` (Tarea 7), `harness.corridas` (Tarea 5), `harness.ver_traza` (Tarea 6), `harness.bucle` (Tarea 3), `evaluar.evaluar`, `evaluar.escribir_csv`, `evaluar.imprimir` y `evaluar.PESOS` (kit).
- Produce: el notebook. Nombres de corrida: `mundial__libro-cerrado__t0__s1337` y `mundial__agente-<ETIQUETA>__t0__s1337`, con `ETIQUETA` igual a `"antes"` o `"despues"`.

- [ ] **Paso 1: escribir la fuente del notebook**

`colab/fuentes/nb01_bloque1_mundial.py`:

````python
"""Fuente del notebook 01: el loop del Bloque 1 sobre el Mundial."""
NOMBRE = "01_bloque1_mundial.ipynb"

CELDAS = [
    ("md", """
# 01 · Bloque 1: el loop del agente sobre el Mundial

**Qué hace este notebook.** Corre las 30 tareas públicas del Mundial de dos maneras y las puntúa:
1. **Libro cerrado**: el modelo contesta de memoria, sin herramientas. Es la línea de base.
2. **El agente**: el mismo modelo, pero dentro de nuestro loop, con herramientas sobre los datos.

**Qué necesitás.** Una cuenta de Colab con GPU **T4** (*Entorno de ejecución → Cambiar tipo de entorno de ejecución → T4*, **antes** de correr nada), acceso a la carpeta compartida `TPFinal-heladera` en tu Drive (agregala a *Mi unidad* con *Agregar acceso directo*) y un token de GitHub de solo lectura para el repo.

**Cuánto tarda.** Unos 10 minutos de preparación (Ollama y el modelo) y después unos 30 a 60 minutos por corrida de 30 tareas.

**Qué deja en Drive.** `TPFinal-heladera/corridas/<corrida>/` con una traza por tarea, y `TPFinal-heladera/resultados/<corrida>.csv` con la puntuación.

**Si se corta la sesión:** volvé a abrir el notebook, corré la sección 0 y después la misma celda de corrida. Sigue desde la última tarea que quedó en Drive.
"""),
    ("md", """
## 0 · Preparar el entorno

La primera celda monta tu Drive y baja el código del repositorio. El token se pide al correr y no queda en el notebook. Para crearlo: GitHub → *Settings* → *Developer settings* → *Fine-grained tokens* → solo este repositorio, permiso **Contents: Read-only**, vencimiento corto.
"""),
    ("code", """
from google.colab import drive
drive.mount("/content/drive")

import os, subprocess, sys
from getpass import getpass

REPO = "AgustinMendez25/TPFinal-Multiagente"
CARPETA = "/content/proyecto"
if not os.path.exists(CARPETA):
    url = f"https://{getpass('Token de GitHub (solo lectura): ')}@github.com/{REPO}.git"
    subprocess.run(["git", "clone", "-q", url, CARPETA], check=True)
    del url
os.chdir(CARPETA)
subprocess.run(["git", "pull", "-q"], check=True)
sys.path.insert(0, CARPETA)
print(subprocess.run(["git", "log", "--oneline", "-1"], capture_output=True, text=True).stdout)
"""),
    ("md", """
La segunda celda instala Ollama **0.40.10** (la versión del kit), baja `qwen3:8b`, hace una llamada de prueba y chequea que el modelo corra **100% en la GPU**. Si aparece un aviso de ATENCIÓN, leelo antes de seguir: los tiempos de una corrida que no está 100% en GPU no sirven para comparar.

Después baja los datos del Mundial (la *Fjelstul World Cup Database*, con la versión fijada) y arma la base SQLite que usan las herramientas.
"""),
    ("code", """
from colab import entorno
INFORME = entorno.preparar(gpu=True)
subprocess.run([sys.executable, "datos/descargar.py"], check=True)
QUIEN = input("Tu nombre (queda en la tanda que corras): ").strip() or "anonimo"
"""),
    ("md", """
## 1 · Cómo funciona el loop

Un agente es un programa que le deja al modelo decidir **el próximo paso**, pero se queda con todo lo demás: qué herramientas puede usar, cómo se ejecutan, qué vuelve a la ventana y cuándo se frena. Nuestro loop está en `harness/bucle.py` y es **el mismo** para el Mundial y para las recetas; lo que cambia es el `Dominio` (las herramientas y las instrucciones).

En cada **paso**:
1. Se le manda al modelo toda la conversación más las fichas JSON de las herramientas.
2. Si el modelo pide herramientas, se ejecuta cada una y se le devuelve **un resultado por llamada**.
3. Si llama a `terminar(respuesta, motivo)`, la corrida termina: con respuesta es `respondida`, con `null` es `negada` (los datos no alcanzan).
4. Si contesta con texto suelto, se le recuerda que tiene que llamar a una herramienta.

La función principal:
"""),
    ("code", """
import inspect
from harness import bucle
print(inspect.getsource(bucle.bucle))
"""),
    ("md", """
### Qué pasa cuando algo sale mal

El modelo se equivoca y las herramientas fallan. El loop **no se cae**: le devuelve el error al modelo como resultado y sigue. Cada caso de la sección 4 del enunciado:

| Caso | Qué hace el loop | Dónde |
|---|---|---|
| JSON roto en los argumentos | devuelve «los argumentos no son JSON válido» | `_parsear` |
| Herramienta que no existe | devuelve la lista de las que hay | `_atender` |
| Argumento de tipo equivocado, que falta o que sobra | devuelve qué argumento está mal y por qué | `validar_argumentos` |
| La herramienta levanta una excepción o tarda demasiado | devuelve «la herramienta falló» o «tardó más de N s» | `_ejecutar` |
| Resultado vacío | devuelve «la herramienta no encontró nada» | `_texto_resultado` |
| Resultado demasiado largo | lo recorta a `contexto.tope_resultado_caracteres` y avisa | `_texto_resultado` |
| El servidor del modelo falla | reintenta con espera creciente, hasta `frenos.reintentos` | `_llamar_modelo` |
| El prompt no entra en `num_ctx` | termina con `error` (reintentar no lo arregla) | `bucle` |
| Demasiados pasos o tokens | termina con `tope_pasos` o `tope_tokens` | `bucle` |
"""),
    ("code", """
print(inspect.getsource(bucle.validar_argumentos))
print(inspect.getsource(bucle._ejecutar))
print(inspect.getsource(bucle._llamar_modelo))
"""),
    ("md", """
### La configuración

`config.toml` fija el modelo, `num_ctx` (que se manda **en cada llamada**: Ollama usa 4.096 por defecto en una T4 y recortaría en silencio), la decodificación (temperatura 0, semilla 1337, `think` apagado) y los frenos. Se copia entera en el primer evento de cada traza.
"""),
    ("code", """
print(open("config.toml", encoding="utf-8").read())
"""),
    ("md", """
## 2 · Línea de base: libro cerrado

Las mismas 30 preguntas, al mismo modelo, **sin herramientas**. Sirve para saber cuánto sabe el modelo de memoria. Lo que compra el agente no es solo acertar: es una respuesta que sale de los datos y un «los datos no alcanzan» honesto en las 4 imposibles.

La celda corre la tanda y copia cada traza a Drive apenas termina. Si se corta, volvé a correrla: saltea lo que ya está.
"""),
    ("code", """
import json
from pathlib import Path
import config as configuracion
import evaluar
from harness import corridas

RUTAS = entorno.rutas()
TAREAS = json.loads(Path("tareas/mundial_publicas.json").read_text(encoding="utf-8"))
CONFIG = configuracion.cargar()


def correr(nombre, correr_una):
    destino = RUTAS["corridas"] / nombre
    resumen = corridas.correr_tanda(
        TAREAS, destino, RUTAS["trabajo"] / nombre, correr_una,
        manifiesto=entorno.manifiesto(nombre, "mundial", CONFIG, TAREAS), quien=QUIEN,
        antes_de_cada=entorno.asegurar_ollama)
    print(resumen)
    return destino


LIBRO = corridas.nombre_corrida("mundial", "libro-cerrado", 0, 1337)
destino_libro = correr(LIBRO, corridas.corredor_libro_cerrado(CONFIG))
"""),
    ("code", """
def puntuar(destino):
    filas, resumen = evaluar.evaluar(TAREAS, destino, evaluar.PESOS)
    evaluar.escribir_csv(filas, RUTAS["resultados"] / f"{destino.name}.csv")
    evaluar.imprimir(filas, resumen)
    return filas, resumen


filas_libro, resumen_libro = puntuar(destino_libro)
"""),
    ("md", """
## 3 · El agente

Ahora con herramientas. `ETIQUETA` distingue la corrida **antes** del arreglo de la corrida **después** (sección 5). La primera vez dejala en `"antes"`.

Cada tarea corre en su propio proceso (`agente.py`), con un tope de 10 minutos; si el proceso se cuelga, el runner cierra la traza con `error` para que la falla quede registrada.
"""),
    ("code", """
ETIQUETA = "antes"   # <- después del arreglo, cambiala a "despues"

AGENTE = corridas.nombre_corrida("mundial", f"agente-{ETIQUETA}", 0, 1337)
destino_agente = correr(AGENTE, corridas.corredor_agente(Path("config.toml").resolve(), "mundial"))
filas_agente, resumen_agente = puntuar(destino_agente)
"""),
    ("md", """
## 4 · Mirar las trazas

Una traza es la evidencia de lo que hizo el agente: cada llamada al modelo (con sus tokens), cada herramienta (con sus argumentos y lo que devolvió) y cómo terminó. Elegí una tarea para verla. Empezá por las que fallaron.
"""),
    ("code", """
from harness import ver_traza

fallidas = [f["tarea"] for f in filas_agente if f["resultado"] != "acierto"]
print("Tareas que no acertó:", fallidas)
TAREA = fallidas[0] if fallidas else "mun-001"   # <- cambiá el id para ver otra
print(ver_traza.resumen(destino_agente / f"{TAREA}.jsonl"))
"""),
    ("md", """
**Una tarea que el agente se niega a responder.** El enunciado pide mostrar una: la traza tiene que dejar ver qué dato falta. Las imposibles son las que tienen `respondible: false`.
"""),
    ("code", """
imposibles = [t["id"] for t in TAREAS if not t["respondible"]]
negadas = [f["tarea"] for f in filas_agente if f["tarea"] in imposibles and f["resultado"] == "acierto"]
print("Imposibles:", imposibles, "· bien negadas:", negadas)
if negadas:
    print(ver_traza.resumen(destino_agente / f"{negadas[0]}.jsonl"))
"""),
    ("md", """
## 5 · El arreglo explicado

Después de la corrida **antes**, analizamos las trazas, elegimos una tarea que falla, vemos qué falló **primero** según la traza, cambiamos el harness y volvemos a correr con `ETIQUETA = "despues"` (sección 3). El cambio y su motivo quedan en `decision_log.md`.

Esta celda pone lado a lado las dos trazas de la tarea arreglada. Solo funciona cuando existen las dos corridas.
"""),
    ("code", """
TAREA_ARREGLADA = "mun-001"   # <- la tarea del arreglo (está en decision_log.md)
antes = RUTAS["corridas"] / corridas.nombre_corrida("mundial", "agente-antes", 0, 1337) / f"{TAREA_ARREGLADA}.jsonl"
despues = RUTAS["corridas"] / corridas.nombre_corrida("mundial", "agente-despues", 0, 1337) / f"{TAREA_ARREGLADA}.jsonl"
if antes.exists() and despues.exists():
    print("ANTES".ljust(70), "| DESPUÉS")
    print(ver_traza.comparar(antes, despues))
else:
    print("Todavía falta alguna de las dos corridas:", antes.exists(), despues.exists())
"""),
    ("md", """
## 6 · Pregunta suelta (para la demo)

En la presentación, el equipo docente hace una pregunta nueva. Esta celda corre el agente sobre cualquier pregunta y muestra la traza. Queda en `corridas/mundial__demo/`, fuera de las mediciones.
"""),
    ("code", """
PREGUNTA = "¿Qué edad tenía el goleador del Mundial 1978 el día de la final? Respondé solo con el número."
demo = RUTAS["corridas"] / "mundial__demo"
subprocess.run([sys.executable, "agente.py", "-p", PREGUNTA, "--tarea", "demo", "--log", str(demo)], check=False)
print(ver_traza.resumen(demo / "demo.jsonl"))
"""),
    ("md", """
## Cierre

En Drive quedaron:
- `corridas/mundial__libro-cerrado__t0__s1337/` y `corridas/mundial__agente-<etiqueta>__t0__s1337/`, con una traza por tarea y el `manifiesto.json` (commit, configuración y versión de Ollama);
- `resultados/<corrida>.csv`, con la puntuación de cada tarea.

**Qué sigue:** avisar que la corrida terminó. Las trazas se analizan desde Drive para escritorio para elegir el arreglo.
"""),
]
````

- [ ] **Paso 2: generar el notebook y correr los tests**

```powershell
python -m uv run colab/construir.py
python -m uv run pytest -q
```
Lo esperado: se escribe `colab/01_bloque1_mundial.ipynb` y la suite completa queda en PASS, incluido `test_todos_los_notebooks_generados_son_validos`.

- [ ] **Paso 3: revisar el notebook generado**

Abrir `colab/01_bloque1_mundial.ipynb` y confirmar tres cosas:
- que las celdas se lean en orden (ficha → entorno → concepto → libro cerrado → agente → trazas → arreglo → demo → cierre);
- que ninguna celda tenga el token ni datos personales;
- que el repositorio sea `AgustinMendez25/TPFinal-Multiagente`.

- [ ] **Paso 4: commit**

```powershell
git add colab/fuentes/nb01_bloque1_mundial.py colab/01_bloque1_mundial.ipynb
git commit -m "Notebook 01: loop del Bloque 1 sobre el Mundial, retomable desde Drive" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tarea 9: cerrar la etapa y dejar todo listo para Colab

**Archivos:**
- Modificar: `decision_log.md`

- [ ] **Paso 1: entrada del decision log sobre el diseño del loop**

Agregar al final de `decision_log.md`:

```markdown
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
- **Ids generados `p<paso>-<n>`** cuando Ollama no trae uno.
```

- [ ] **Paso 2: correr la suite completa una vez más**

`python -m uv run pytest -q`. Lo esperado: todo PASS. Copiar el resumen de pytest en el mensaje del commit.

- [ ] **Paso 3: commit**

```powershell
git add decision_log.md
git commit -m "Decision log: diseño del loop del Bloque 1" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Paso 4: pedir el OK para el push**

Colab clona desde GitHub, así que sin push el grupo no puede correr nada. Hacer push solo con el OK explícito del usuario (`git push origin main`). Después, avisarle qué tiene que hacer:
1. Crear `TPFinal-heladera` en Drive, compartirla y que cada cuenta la agregue a *Mi unidad*.
2. Instalar Drive para escritorio en la PC.
3. Abrir `colab/01_bloque1_mundial.ipynb` en Colab con una T4 y correrlo hasta la sección 3 (corrida "antes").
4. Avisar cuando las trazas estén en Drive.
