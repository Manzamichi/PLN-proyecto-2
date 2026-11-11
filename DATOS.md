# Diccionario de datos

Todos los archivos están en UTF-8. Los identificadores de nodo están en minúsculas,
normalizados a Unicode NFC, conservan acentos y ñ, y las expresiones multipalabra usan
un espacio (`fin de semana`).

## Licencias

| Recurso | Licencia | ¿Se versiona? |
|---|---|---|
| SWOW-RP (Cabana et al., 2024) y todo lo derivado de sus respuestas: normas, grafo, aristas | CC BY-NC-ND 3.0 | No. Se regenera con los scripts a partir de la descarga oficial |
| Lista de nodos (`nodos.txt`) | Solo palabras, sin fuerzas | Local |
| Definiciones de Wikcionario y archivos derivados del corpus | CC BY-SA 4.0 | Sí |
| Embeddings node2vec (`node2vec.kv`) | Derivados del grafo | Sí, para la demostración sin reentrenar |

## 1. Normas de asociación: `data/processed/normas_swow_rp.csv`

Generado por `scripts/exportar_normas.py` a partir de `SWOWRP.R70.20220426.csv`. Una fila por
par estímulo–respuesta distinto (1,056,083 pares).

| Columna | Tipo | Descripción |
|---|---|---|
| `estimulo` | texto | Palabra estímulo (*cue*) normalizada |
| `respuesta` | texto | Respuesta normalizada (R1, R2 o R3) |
| `frecuencia` | entero | Veces que se dio esa respuesta al estímulo |
| `tiempo_medio` | vacío | SWOW-RP no publica tiempos de respuesta; por eso se usan las ponderaciones por fuerza |
| `fuerza` | real (0, 1] | p(respuesta \| estímulo) = frecuencia / respuestas válidas del estímulo |
| `costo_fa` | real | 100 − 100·fuerza (esquema 1, transformación lineal) |
| `costo_logp` | real | −ln(fuerza) (esquema 2; el camino más corto es la cadena más probable) |
| `en_grafo` | booleano | El par es arista del grafo final (respuesta que también es estímulo y dentro de la mayor componente fuertemente conexa) |

Respuestas válidas: se excluyen las vacías y los marcadores `NA` y `No more responses`
(728,706 de 2,832,477; 25.7 %). Los pares con respuesta igual al estímulo se eliminan después
de calcular el denominador.

## 2. Grafo: `data/processed/grafo_swow_rp.pkl`

`networkx.DiGraph` (pickle) generado por `scripts/construir_grafo.py`. 13,451 nodos y
833,440 aristas dirigidas estímulo → respuesta.

| Elemento | Atributo | Descripción |
|---|---|---|
| Nodo | `es_cue` | Siempre verdadero en el grafo final |
| Arista | `frecuencia`, `p`, `costo_fa`, `costo_logp` | Igual que `frecuencia`, `fuerza`, `costo_fa` y `costo_logp` de las normas |

`aristas_swow_rp.csv` contiene las mismas aristas con columnas `cue, response, frecuencia, p,
costo_fa, costo_logp`. `nodos.txt` tiene un nodo por línea.

## 3. Conjunto de evaluación: `data/processed/corpus/corpus.csv`

20,512 definiciones de 9,405 conceptos, todas con el concepto objetivo como nodo del grafo.

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | texto | Identificador estable de la definición (hash) |
| `concepto` | texto | Palabra objetivo; coincide con un nodo del grafo |
| `definicion` | texto | Glosa de Wikcionario, sin la palabra objetivo |
| `fuente` | URL | Página de Wikcionario de la que proviene (atribución) |
| `particion` | `desarrollo` \| `prueba` | Asignada por concepto con `scripts/particionar.py` (semilla 42) |
| `pos` | `noun` \| `adj` \| `verb` | Categoría gramatical de la acepción |
| `acepcion` | entero | Número de acepción en Wikcionario (máximo tres por concepto) |
| `licencia` | texto | `CC-BY-SA-4.0` |

Se descartaron 192 definiciones que mencionan la palabra objetivo (en su forma lematizada) y
71,164 cuyo objetivo no es nodo del grafo; el detalle está en `cobertura.json`.

## 4. Corpus preprocesado: `data/processed/corpus/preprocesado.jsonl`

Una línea JSON por definición con todas las columnas de `corpus.csv` más:

| Campo | Tipo | Descripción |
|---|---|---|
| `lemas` | lista | Lemas útiles tras spaCy `es_core_news_md` 3.8.0 (sin palabras funcionales), con expresiones multipalabra unidas |
| `lemas_en_grafo` | lista | Subconjunto de `lemas` que son nodos del grafo; es la entrada de los modelos |
| `fuera_vocabulario` | lista | Lemas útiles que no son nodos del grafo |
| `cobertura_lexica` | real | Proporción de `lemas` presentes en el grafo |

## 5. Partición: `data/processed/corpus/particion.csv`

| Columna | Descripción |
|---|---|
| `id` | Identificador de la definición |
| `concepto` | Concepto objetivo |
| `particion` | `desarrollo` (2,822 conceptos, 6,145 definiciones) o `prueba` (6,583 conceptos, 14,367 definiciones) |

Resumen y hash del corpus usado en `reports/particion.json`.

## 6. Resultados: `reports/evaluacion/prueba/`

`<modelo>.json`: `n`, `p@1`, `p@3`, `p@5`, `mrr`, `cobertura_modelo` (proporción de definiciones
cuyo ranking contiene al objetivo), `cobertura_lexica`, `rango_mediano_encontrados`,
`segundos_por_definicion`, `definiciones_sin_lemas`.

`<modelo>_detalle.csv`, una fila por definición:

| Columna | Descripción |
|---|---|
| `id`, `concepto` | Definición y objetivo |
| `n_lemas` | Lemas de entrada (sin repetidos) |
| `cobertura_lexica` | Igual que en el corpus preprocesado |
| `rango` | Posición del objetivo (desde 1); vacío si no aparece en el ranking |
| `tam_ranking` | Número de candidatos devueltos |
| `top5` | Cinco primeros candidatos separados por `\|` |
| `segundos` | Tiempo de `rankear` para esa definición |

`resumen.md` reúne todos los modelos; `reports/analisis_resultados.json` contiene las pruebas
de significancia y la comparación por definición usadas en `reports/discusion.md`.
