# Diccionario inverso con SWOW-RP

Proyecto Unidad II de PLN, FMAT-UADY. Grafo de asociaciones y preprocesamiento
del corpus de definiciones.

## Instalación

Python 3.12. Desde la raíz, en PowerShell:

```powershell
uv venv --python 3.12 .venv
uv pip install --python .venv/Scripts/python.exe -r requirements.lock.txt -e ".[dev]"
uv pip install --python .venv/Scripts/python.exe --no-deps node2vec==0.5.0
```

`node2vec` 0.5.0 declara `numpy<2` y el lock fija numpy 2.5.4, así que se
instala aparte con `--no-deps` para no bajar numpy. Sus dependencias (gensim,
joblib, tqdm, networkx) ya vienen en el proyecto. Probado con Python 3.12,
numpy 2.5.4 y gensim 4.4.0. `uv pip check` reporta esa restricción de numpy;
es esperado.

Si uv no puede enlazar el Python descargado (pasa cuando AppData está
virtualizado), se pueden dejar Python y caché dentro del proyecto antes de
`uv venv`, en carpetas ya ignoradas por Git:

```powershell
$env:UV_PYTHON_INSTALL_DIR = "$PWD\.local\python"
$env:UV_CACHE_DIR = "$PWD\.uv-cache"
```

## Grafo

Descargar SWOW-RP22 desde [Small World of Words](https://smallworldofwords.org/en/project/research)
y colocar el CSV balanceado `SWOW-RP.R70.<version>.csv` en `data/raw/`.
Las respuestas de SWOW, el grafo y su lista de nodos se comparten entre el equipo
fuera de Git.
Para el bloque de corpus basta con `data/processed/nodos.txt`, generado por el
script o proporcionado por quien construyó el grafo.

```powershell
.venv/Scripts/python.exe scripts/construir_grafo.py
.venv/Scripts/python.exe scripts/caracterizar_grafo.py
```

Se genera un grafo dirigido con R1+R2+R3, restringido por defecto a cues y a su
mayor componente fuertemente conexa. Atributos: `frecuencia`, `p`,
`costo_fa = 100 - 100*p` y `costo_logp = -log(p)`.
`--help` muestra los filtros configurables. Para caminos se usan los costos;
para node2vec se usa la similitud `p`.

Salidas: `data/processed/grafo_swow_rp.pkl`, `aristas_swow_rp.csv`, `nodos.txt`
y caracterización en `reports/`. Los IDs multipalabra del grafo usan espacios.

## Corpus

Con `nodos.txt` del grafo final (generado localmente o compartido por el equipo):

```powershell
.venv/Scripts/python.exe -m diccionario_inverso.corpus preparar --nodos data/processed/nodos.txt --salida data/processed/corpus
```

También se acepta CSV `nodo,grado` (se excluye grado cero) o JSON con una lista
de IDs activos. El banco `data/corpus_fuente.csv` está incluido.

El corpus validado se encuentra en `data/processed/corpus/`: **20,512 definiciones
para 9,405 conceptos**, contrastadas con la lista de 13,451 nodos de Carlos.
Se versionan `corpus.csv`, `preprocesado.jsonl` y `cobertura.json` para que los
modelos puedan usar la misma entrada. La lista de nodos y la auditoría completa
`descartadas.csv` permanecen locales. `particion=pendiente` debe asignarse a
desarrollo/prueba por concepto, evitando glosas idénticas entre particiones,
antes de ajustar o evaluar los modelos.

Cobertura de definiciones: **99.50%**; cobertura léxica micro: **84.05%**;
promedio de lemas presentes: **5.15**. Se conservan 102 definiciones sin lemas
en el grafo. Estas cifras miden cobertura, no aciertos de los modelos.

Se generan `corpus.csv`, `preprocesado.jsonl`, `descartadas.csv` y `cobertura.json`.
Código de salida 2 si quedan menos de 300 definiciones. Los casos sin cobertura
permanecen en el corpus.

```python
from pathlib import Path
from diccionario_inverso.corpus.archivos import leer_nodos
from diccionario_inverso.corpus.preprocesamiento import Preprocesador

pre = Preprocesador(leer_nodos(Path("data/processed/nodos.txt")))
candidatos = modelo.rankear(pre.lemas_para_modelo(definicion))
```

Los lemas conservan repeticiones e IDs originales, incluidos los espacios.
Los modelos implementan `diccionario_inverso.modelos.ModeloBusqueda`, excluyen
los lemas de entrada de sus candidatos y devuelven `[]` si no hay lemas.
El campo `concepto` se utiliza exclusivamente para evaluar.

## Evaluación

Partición desarrollo/prueba por concepto objetivo (30 % / 70 % de los conceptos, semilla 42).
Todas las definiciones de un mismo concepto quedan en la misma partición, así el ajuste en
desarrollo no ve objetivos de prueba. Se genera una sola vez y se versiona:

```bash
python scripts/particionar.py            # data/processed/corpus/particion.csv, reports/particion.json
```

Evaluación (p@1, p@3, p@5, MRR, cobertura del modelo y cobertura léxica):

```bash
python scripts/evaluar.py --listar
python scripts/evaluar.py --particion desarrollo --muestra 300 --procesos 8   # prueba rápida
python scripts/evaluar.py --particion prueba --procesos 8                      # resultados finales
```

Resultados en `reports/evaluacion/<particion>/`: `<modelo>.json`, `<modelo>_detalle.csv`
(rango del objetivo y top 5 por definición) y `resumen.md`. Las definiciones sin lemas en el
grafo o cuyo objetivo no aparece en el ranking cuentan como fallo.

Para agregar un modelo, registrarlo en `src/diccionario_inverso/modelos/registro.py` con
`@registrar("nombre")`. Para ajustar hiperparámetros en desarrollo desde código:

```python
from diccionario_inverso.evaluacion import cargar_ejemplos, evaluar_modelo
detalle, resumen = evaluar_modelo(mi_modelo, cargar_ejemplos("desarrollo"))
```

## Modelo híbrido con node2vec

Requiere `data/processed/grafo_swow_rp.pkl` y el corpus versionado.

```powershell
.venv/Scripts/python.exe scripts/modelo_node2vec.py explorar --configuraciones 1
.venv/Scripts/python.exe scripts/modelo_node2vec.py explorar
.venv/Scripts/python.exe scripts/modelo_node2vec.py consultar "insecto de rayas que produce miel"
```

Entrena node2vec sobre la copia no dirigida del grafo (`a_no_dirigido`) con
peso `p` (`--peso` permite otro atributo), `SEMILLA=42` y `workers=1`, que dan
embeddings idénticos entre corridas. Recorre `CONFIGURACIONES` de
`diccionario_inverso.modelos.node2vec` (la 1 es la de clase, 300 dimensiones) y
reutiliza las caminatas cuando solo cambia la dimensión
(`segundos_caminatas = 0`). La definición se representa como suma de los
vectores de sus lemas o suma ponderada por IDF = log10(N / df), con cada
definición de desarrollo como documento. La mejor combinación por MRR en
desarrollo es la única evaluada en prueba.

Usa la partición de `data/processed/corpus/particion.csv` (ver Evaluación).
Si ese archivo falta, usa una partición **provisional** determinista por
concepto (mitad y mitad, sin modificar el corpus). La columna `particion`
de los resultados dice `asignada` o `provisional`.
`--frecuencia-min N` descarta en la copia no dirigida las aristas con
frecuencia menor a N; por defecto no filtra. `--dirigido` camina sobre el
grafo dirigido cue -> respuesta; con la configuración 1 bajó el MRR de
desarrollo de 0.125 a 0.087 (`reports/node2vec_resultados_dirigido.csv`).

Salidas: `reports/node2vec_resultados.csv` y la mejor configuración en
`data/processed/node2vec.kv` (con `KeyedVectors.save`, que conserva los IDs con
espacios) más `node2vec.json` con la composición y el IDF. Ambos se versionan
para consultar sin reentrenar; el modelo de `--dirigido` queda local.

```python
from diccionario_inverso.modelos.node2vec import ModeloNode2Vec

modelo = ModeloNode2Vec.cargar("data/processed/node2vec.kv")
modelo.rankear(["insecto", "miel"], k=10)
```

## Reconstrucción del banco y pruebas

```powershell
.venv/Scripts/python.exe -m diccionario_inverso.corpus descargar
.venv/Scripts/python.exe -m diccionario_inverso.corpus extraer
.venv/Scripts/python.exe -m pytest --basetemp=tmp/pytest
```

Si el dump ya existe en `data/raw/`, ejecutar solo `extraer`.
`corpus_fuente.json` registra hashes y filtros; `corpus_fuente_menciones.csv`
contiene las glosas excluidas por revelar el objetivo.

## Procedencia del corpus

Definiciones de los colaboradores de [Wikcionario](https://es.wiktionary.org/),
edición española, distribuidas por [Kaikki](https://kaikki.org/dictionary/rawdata.html)
mediante Wiktextract. Cada fila conserva su enlace de atribución en `fuente`.
Texto bajo [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
Se seleccionaron lemas, normalizaron conceptos y espacios, filtraron glosas y
eliminaron duplicados, con un máximo de tres acepciones por concepto.

Extractor: Ylonen, T. (2022).
[Wiktextract: Wiktionary as Machine-Readable Structured Data](https://aclanthology.org/2022.lrec-1.140/).
