# Diez filas reales del dataset final

RecetasDeLaAbuela, `main.csv`, commit `c9879423`. Diez recetas tomadas al azar (semilla 2026) de `datos/recetas_final.csv`: 4 que no necesitaron ningún cambio y 6 corregidas. De cada una va la fila cruda del CSV (sin `Pasos` ni `Contexto`) y, abajo, qué se decidió con cada línea de ingrediente. Las reglas (U01, D02, P01…) están en `datos/normalizacion/equivalencias.csv`; «PAR» es la cantidad que la propia receta escribe entre paréntesis.

## Id 5627: lomo estofado al vino (sin problema)

- **URL:** `'https://www.recetasgratis.net/receta-de-lomo-estofado-al-vino-11709.html'`
- **Comensales:** `'3 comensales'`
- **Duracion:** `'00:30'`
- **Categoria:** `'[]'`
- **Dificultad:** `'Dificultad baja'`
- **Valor nutricional:** `'Bajo en calorías, Sin grasa, Sin grasas trans'`
- **Ingredientes (crudo):**

  ```
  ['½ kilogramo de Lomo de cerdo', '1 kilogramo de Champiñones', '½ litro de Vino tinto', '100 gramos de Mantequilla', '¼ litro de Aceite', '1 diente de Ajo', '1 pizca de Sal', 'Pimienta al gusto']
  ```

| Línea cruda | Ingrediente | Leído | Normalizado | Estado | Reglas |
|---|---|---|---|---|---|
| ½ kilogramo de Lomo de cerdo | cerdo | 500 g | 500 g | sin_cambio |  |
| 1 kilogramo de Champiñones | champinon | 1000 g | 1000 g | sin_cambio |  |
| ½ litro de Vino tinto | vino | 500 ml | 500 ml | sin_cambio |  |
| 100 gramos de Mantequilla | manteca | 100 g | 100 g | sin_cambio |  |
| ¼ litro de Aceite | aceite | 250 ml | — | basico |  |
| 1 diente de Ajo | ajo | 1 diente | 1 diente | sin_cambio |  |
| 1 pizca de Sal | sal | 1 pizca | — | basico |  |
| Pimienta al gusto | pimienta | — | — | basico |  |

## Id 12585: nuggets de atun (sin problema)

- **URL:** `'https://www.recetasgratis.net/receta-de-nuggets-de-atun-31250.html'`
- **Comensales:** `'2 comensales'`
- **Duracion:** `'00:15'`
- **Categoria:** `'[]'`
- **Dificultad:** `'Dificultad baja'`
- **Valor nutricional:** `'Alto en grasas, Alto en sodio, Sin azúcar añadida'`
- **Ingredientes (crudo):**

  ```
  ['150 gramos de Atún de lata', '100 gramos de Pan rallado', '120 gramos de Queso crema', '5 unidades de Huevo']
  ```

| Línea cruda | Ingrediente | Leído | Normalizado | Estado | Reglas |
|---|---|---|---|---|---|
| 150 gramos de Atún de lata | pescado | 150 g | 150 g | sin_cambio |  |
| 100 gramos de Pan rallado | pan | 100 g | 100 g | sin_cambio |  |
| 120 gramos de Queso crema | queso | 120 g | 120 g | sin_cambio |  |
| 5 unidades de Huevo | huevo | 5 unidad | 5 unidad | sin_cambio |  |

## Id 16643: mayonesa casera (sin problema)

- **URL:** `'https://www.recetasgratis.net/receta-de-mayonesa-casera-62554.html'`
- **Comensales:** `'1 comensal'`
- **Duracion:** `'00:10'`
- **Categoria:** `'[]'`
- **Dificultad:** `'Dificultad baja'`
- **Valor nutricional:** `'Alto en grasas, Alto en calorías, Sin sodio'`
- **Ingredientes (crudo):**

  ```
  ['1 Huevo', '200 mililitros de Aceite de girasol', '1 chorro de Vinagre o Zumo de limón', '1 pizca de Sal']
  ```

| Línea cruda | Ingrediente | Leído | Normalizado | Estado | Reglas |
|---|---|---|---|---|---|
| 1 Huevo | huevo | 1 unidad | 1 unidad | sin_cambio |  |
| 200 mililitros de Aceite de girasol | aceite | 200 ml | — | basico |  |
| 1 chorro de Vinagre o Zumo de limón | condimento | 1 chorro | — | basico |  |
| 1 pizca de Sal | sal | 1 pizca | — | basico |  |

## Id 16755: salsa raita (sin problema)

- **URL:** `'https://www.recetasgratis.net/receta-de-salsa-raita-56122.html'`
- **Comensales:** `'1 comensal'`
- **Duracion:** `'00:15'`
- **Categoria:** `"['Recetas indias']"`
- **Dificultad:** `'Dificultad baja'`
- **Valor nutricional:** `'Bajo en calorías, Sin grasa, Alto en fibra'`
- **Ingredientes (crudo):**

  ```
  ['¼ unidad de Cebolla', '½ unidad de Pepino', '1 unidad de Tomate', '1 pizca de Comino en polvo', '1 pizca de Chat masala o Sal negra', '1 pizca de Sal', '150 gramos de Yogur natural']
  ```

| Línea cruda | Ingrediente | Leído | Normalizado | Estado | Reglas |
|---|---|---|---|---|---|
| ¼ unidad de Cebolla | cebolla | 0.25 unidad | 0.25 unidad | sin_cambio |  |
| ½ unidad de Pepino | pepino | 0.5 unidad | 0.5 unidad | sin_cambio |  |
| 1 unidad de Tomate | tomate | 1 unidad | 1 unidad | sin_cambio |  |
| 1 pizca de Comino en polvo | condimento | 1 pizca | — | basico |  |
| 1 pizca de Chat masala o Sal negra | sal | 1 pizca | — | basico |  |
| 1 pizca de Sal | sal | 1 pizca | — | basico |  |
| 150 gramos de Yogur natural | yogur | 150 g | 150 g | sin_cambio |  |

## Id 14137: crema pastelera basica (corregida)

- **URL:** `'https://www.recetasgratis.net/receta-de-crema-pastelera-basica-57593.html'`
- **Comensales:** `'2 comensales'`
- **Duracion:** `'00:45'`
- **Categoria:** `'[]'`
- **Dificultad:** `'Dificultad media'`
- **Valor nutricional:** `'Alto en calorías, Alto en grasas, Alto en azúcar'`
- **Ingredientes (crudo):**

  ```
  ['4 unidades de Yemas de huevo', '100 gramos de Azúcar                                                                    (½ taza)', '50 gramos de Harina', '2 cucharadas soperas de Maicena', '½ litro de Leche', '1 rama de Canela']
  ```

| Línea cruda | Ingrediente | Leído | Normalizado | Estado | Reglas |
|---|---|---|---|---|---|
| 4 unidades de Yemas de huevo | huevo | 4 unidad | 4 unidad | sin_cambio |  |
| 100 gramos de Azúcar                                                                    (½ taza) | azucar | 100 g | 100 g | sin_cambio |  |
| 50 gramos de Harina | harina | 50 g | 50 g | sin_cambio |  |
| 2 cucharadas soperas de Maicena | maiz | 2 cucharada | 21 g | corregida | U02 D06 |
| ½ litro de Leche | leche | 500 ml | 500 ml | sin_cambio |  |
| 1 rama de Canela | condimento | 1 rama | — | basico |  |

## Id 18019: pimiento relleno de carne molida (corregida)

- **URL:** `'https://www.recetasgratis.net/receta-de-pimiento-relleno-de-carne-molida-59603.html'`
- **Comensales:** `'4 comensales'`
- **Duracion:** `'00:45'`
- **Categoria:** `"['Recetas al horno', 'Recetas mexicanas']"`
- **Dificultad:** `'Dificultad baja'`
- **Valor nutricional:** `'Alto en calorías, Alto en grasas, Alto en sodio'`
- **Ingredientes (crudo):**

  ```
  ['4 piezas de Pimiento morrón', '400 gramos de Carne molida de res', '2 Zanahorias', '200 gramos de Chícharos', '1 Papa grande', '¼ Cebolla', '1 diente de Ajo', '1 pizca de Sal', '1 pizca de Pimienta', '2 cucharadas soperas de Aceite']
  ```

| Línea cruda | Ingrediente | Leído | Normalizado | Estado | Reglas |
|---|---|---|---|---|---|
| 4 piezas de Pimiento morrón | morron | 4 pieza | 4 unidad | corregida | U09 |
| 400 gramos de Carne molida de res | carne vacuna | 400 g | 400 g | sin_cambio |  |
| 2 Zanahorias | zanahoria | 2 unidad | 2 unidad | sin_cambio |  |
| 200 gramos de Chícharos | arveja | 200 g | 200 g | sin_cambio |  |
| 1 Papa grande | papa | 1 unidad | 1 unidad | sin_cambio |  |
| ¼ Cebolla | cebolla | 0.25 unidad | 0.25 unidad | sin_cambio |  |
| 1 diente de Ajo | ajo | 1 diente | 1 diente | sin_cambio |  |
| 1 pizca de Sal | sal | 1 pizca | — | basico |  |
| 1 pizca de Pimienta | pimienta | 1 pizca | — | basico |  |
| 2 cucharadas soperas de Aceite | aceite | 2 cucharada | — | basico |  |

## Id 19278: tortilla de acelgas vegana (corregida)

- **URL:** `'https://www.recetasgratis.net/receta-de-tortilla-de-acelgas-vegana-10448.html'`
- **Comensales:** `'2 comensales'`
- **Duracion:** `'00:15'`
- **Categoria:** `"['Recomendada para veganos']"`
- **Dificultad:** `'Dificultad baja'`
- **Valor nutricional:** `'Sin calorías, Sin grasa, Sin grasas trans'`
- **Ingredientes (crudo):**

  ```
  ['200 gramos de Hojas acelga', '4 cucharadas soperas de Harina trigo', '3 cucharadas soperas de Harina maíz', '½ sobre de Levadura', '1 vaso de Agua', '1 chorro de Vinagre de vino', '1 chorro de Aceite de oliva', '1 pizca de Sal', '1 pizca de Pimienta negra']
  ```

| Línea cruda | Ingrediente | Leído | Normalizado | Estado | Reglas |
|---|---|---|---|---|---|
| 200 gramos de Hojas acelga | espinaca | 200 g | 200 g | sin_cambio |  |
| 4 cucharadas soperas de Harina trigo | harina | 4 cucharada | 33 g | corregida | U02 D01 |
| 3 cucharadas soperas de Harina maíz | harina | 3 cucharada | 24.75 g | corregida | U02 D01 |
| ½ sobre de Levadura | levadura | 0.5 sobre | 3.89 ml | corregida | E27 D09 |
| 1 vaso de Agua | agua | 1 vaso | — | basico |  |
| 1 chorro de Vinagre de vino | condimento | 1 chorro | — | basico |  |
| 1 chorro de Aceite de oliva | aceite | 1 chorro | — | basico |  |
| 1 pizca de Sal | sal | 1 pizca | — | basico |  |
| 1 pizca de Pimienta negra | pimienta | 1 pizca | — | basico |  |

## Id 3591: porridge de avena y platano (corregida)

- **URL:** `'https://www.recetasgratis.net/receta-de-porridge-de-avena-y-platano-76627.html'`
- **Comensales:** `'1 comensal'`
- **Duracion:** `'00:10'`
- **Categoria:** `"['Recomendada para veganos', 'Recomendada para vegetarianos', 'Recomendada para perder peso', 'Receta sin azúcar']"`
- **Dificultad:** `'Dificultad muy baja'`
- **Valor nutricional:** `'Bajo en calorías, Sin grasa, Alto en fibra'`
- **Ingredientes (crudo):**

  ```
  ['4 cucharadas soperas de avena', '½ taza de agua                                                                    (120 mililitros)', '4 cucharadas soperas de leche descremada o bebida vegetal', '1 plátano chico', '1 pizca de canela']
  ```

| Línea cruda | Ingrediente | Leído | Normalizado | Estado | Reglas |
|---|---|---|---|---|---|
| 4 cucharadas soperas de avena | avena | 4 cucharada | 60 ml | corregida | U02 |
| ½ taza de agua                                                                    (120 mililitros) | agua | 0.5 taza | — | basico |  |
| 4 cucharadas soperas de leche descremada o bebida vegetal | leche | 4 cucharada | 60 ml | corregida | U02 |
| 1 plátano chico | banana | 1 unidad | 1 unidad | sin_cambio |  |
| 1 pizca de canela | condimento | 1 pizca | — | basico |  |

## Id 18184: pastel de patata con bacon y queso (corregida)

- **URL:** `'https://www.recetasgratis.net/receta-de-pastel-de-patata-con-bacon-y-queso-57678.html'`
- **Comensales:** `'2 comensales'`
- **Duracion:** `'01:00'`
- **Categoria:** `"['Recetas al horno']"`
- **Dificultad:** `'Dificultad baja'`
- **Valor nutricional:** `'Alto en calorías, Alto en grasas, Alto en sodio'`
- **Ingredientes (crudo):**

  ```
  ['500 gramos de Patata', '100 gramos de Bacon ahumado', '200 mililitros de Nata', '1 unidad de Huevo', '1 pizca de Sal', '120 gramos de Queso en lonchas', '80 gramos de Queso rallado']
  ```

| Línea cruda | Ingrediente | Leído | Normalizado | Estado | Reglas |
|---|---|---|---|---|---|
| 500 gramos de Patata | papa | 500 g | 2.5 unidad | corregida | P02 |
| 100 gramos de Bacon ahumado | cerdo | 100 g | 100 g | sin_cambio |  |
| 200 mililitros de Nata | crema de leche | 200 ml | 200 ml | sin_cambio |  |
| 1 unidad de Huevo | huevo | 1 unidad | 1 unidad | sin_cambio |  |
| 1 pizca de Sal | sal | 1 pizca | — | basico |  |
| 120 gramos de Queso en lonchas | queso | 120 g | 120 g | sin_cambio |  |
| 80 gramos de Queso rallado | queso | 80 g | 80 g | sin_cambio |  |

## Id 6970: batido de manzanas y frutillas bajo en calorias (corregida)

- **URL:** `'https://www.recetasgratis.net/receta-de-batido-de-manzanas-y-frutillas-bajo-en-calorias-51352.html'`
- **Comensales:** `'1 comensal'`
- **Duracion:** `'00:10'`
- **Categoria:** `"['Recomendada para perder peso', 'Receta sin lactosa', 'Receta sin azúcar']"`
- **Dificultad:** `'Dificultad baja'`
- **Valor nutricional:** `'Bajo en calorías, Sin grasa, Sin azúcar añadida'`
- **Ingredientes (crudo):**

  ```
  ['1 litro de Leche sin lactosa', '500 gramos de Fresa o Frutilla', '2 Manzanas verdes', '1 cucharadita de Edulcorante sin azúcar']
  ```

| Línea cruda | Ingrediente | Leído | Normalizado | Estado | Reglas |
|---|---|---|---|---|---|
| 1 litro de Leche sin lactosa | leche | 1000 ml | 1000 ml | sin_cambio |  |
| 500 gramos de Fresa o Frutilla | frutilla | 500 g | 500 g | sin_cambio |  |
| 2 Manzanas verdes | manzana | 2 unidad | 2 unidad | sin_cambio |  |
| 1 cucharadita de Edulcorante sin azúcar | azucar | 1 cucharadita | 4.25 g | corregida | U03 D02 |
