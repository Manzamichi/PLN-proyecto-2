# Diccionario inverso con SWOW-RP

Proyecto de la Unidad 2 de Procesamiento de Lenguaje Natural, Facultad de Matemáticas, UADY.
Profesor: Dr. Jorge Carlos Reyes Magaña. **Modalidad B**: normas existentes distintas de NAP.

Dada una definición en español («insecto de rayas que produce miel»), el sistema devuelve una
lista ordenada de palabras candidatas. Usa las normas de asociación libre del español
rioplatense *Small World of Words* (SWOW-RP; Cabana et al., 2024) representadas como grafo, y
compara modelos de centralidad con un modelo híbrido de embeddings node2vec, siguiendo el modelo
de búsqueda léxica de Reyes-Magaña et al. (2019).

| Integrante | Bloque |
|---|---|
| Carlos Ermilo Manzanero Canto | Grafo, caracterización, partición y evaluación |
| David Ernesto Escalante García | Corpus de definiciones y preprocesamiento |
| Bryan Chale Chan | Modelos de centralidad |
| Ivan Augusto Perez Saldivar | Modelo híbrido con node2vec |

Documentación adicional: [`DATOS.md`](DATOS.md) (diccionario de datos y licencias) y
[`reports/discusion.md`](reports/discusion.md) (tabla comparativa, preguntas guía, análisis de
errores y costo computacional).

## Resultados en prueba

14,367 definiciones de 6,583 conceptos; 13,451 candidatos. Las definiciones sin lemas en el grafo
o cuyo objetivo no aparece en el ranking cuentan como fallo.

| Modelo | Ponderación | p@1 | p@3 | p@5 | MRR | Cobertura |
|---|---|---|---|---|---|---|
| node2vec, suma IDF | p | **0.066** | **0.139** | **0.182** | **0.128** | 99.5 % |
| node2vec, suma | p | 0.053 | 0.115 | 0.155 | 0.108 | 99.5 % |
| Grado (reducido) | p | 0.023 | 0.056 | 0.083 | 0.061 | 71.6 % |
| Intermediación (reducido) | −log p | 0.008 | 0.021 | 0.032 | 0.026 | 42.1 % |
| Intermediación (reducido) | 100 − FA | 0.007 | 0.020 | 0.030 | 0.025 | 42.1 % |
| Cercanía (reducido) | 100 − FA | 0.009 | 0.022 | 0.032 | 0.024 | 42.1 % |
| Cercanía (reducido) | −log p | 0.009 | 0.022 | 0.032 | 0.024 | 42.1 % |
| Popularidad (referencia) | p | 0.000 | 0.000 | 0.000 | 0.001 | 99.5 % |

Tabla generada por `scripts/evaluar.py` en `reports/evaluacion/prueba/resumen.md`.

## Instalación

Python 3.12 o 3.13. `node2vec` 0.5.0 declara `numpy<2` y el lock fija numpy 2.5.4, así que se
instala aparte con `--no-deps`. Sus dependencias (gensim, joblib, tqdm, networkx) ya vienen en el
proyecto. `pip check` reporta esa restricción de numpy; es esperado.

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock.txt -e ".[dev]"
python -m pip install --no-deps node2vec==0.5.0
python -m pytest
```

Windows (PowerShell, con uv):

```powershell
uv venv --python 3.12 .venv
uv pip install --python .venv/Scripts/python.exe -r requirements.lock.txt -e ".[dev]"
uv pip install --python .venv/Scripts/python.exe --no-deps node2vec==0.5.0
```

Si uv no puede enlazar el Python descargado (pasa cuando AppData está
virtualizado), se pueden dejar Python y caché dentro del proyecto antes de
`uv venv`, en carpetas ya ignoradas por Git:

```powershell
$env:UV_PYTHON_INSTALL_DIR = "$PWD\.local\python"
$env:UV_CACHE_DIR = "$PWD\.uv-cache"
```

En macOS, el proyecto no debe estar en una carpeta sincronizada con iCloud (por ejemplo
`~/Documents`): iCloud descarga bajo demanda los archivos de `.venv` y Python puede quedarse
bloqueado al importarlos.

## Reproducir todo

Los comandos se muestran con `python` dentro del entorno activado (en Windows,
`.venv/Scripts/python.exe`). Semillas fijas: partición 42, node2vec 42.

| # | Paso | Comando | Genera |
|---|---|---|---|
| 1 | Grafo | `python scripts/construir_grafo.py` | grafo, aristas, nodos, `reports/filtrado.json` |
| 2 | Caracterización | `python scripts/caracterizar_grafo.py --clustering-exacto` | `reports/caracterizacion.*`, distribución de grado |
| 3 | Validación de fuerzas | `python scripts/validar_fuerzas.py` | `reports/validacion_fuerzas.json` |
| 4 | Normas en CSV | `python scripts/exportar_normas.py` | `data/processed/normas_swow_rp.csv` |
| 5 | Corpus | `python -m diccionario_inverso.corpus preparar --nodos data/processed/nodos.txt --salida data/processed/corpus` | corpus y cobertura |
| 6 | Partición | `python scripts/particionar.py` y `python scripts/sincronizar_particion.py` | `particion.csv`, columna `particion` del corpus |
| 7 | node2vec | `python scripts/modelo_node2vec.py explorar` | `reports/node2vec_resultados.csv`, `node2vec.kv` |
| 8 | Evaluación | `python scripts/evaluar.py --particion prueba --procesos 6` | `reports/evaluacion/prueba/` (tabla comparativa) |
| 9 | Análisis | `python scripts/analizar_resultados.py` y `python scripts/errores_node2vec.py` | `reports/analisis_resultados.json`, errores de node2vec |

Los pasos 1 a 4 requieren SWOW-RP (ver abajo). Los pasos 6 a 9 se pueden ejecutar con los
archivos versionados más el grafo. Demostración: `python scripts/modelo_node2vec.py consultar
"insecto de rayas que produce miel"`.

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
`descartadas.csv` permanecen locales. La columna `particion` se llena con
`scripts/sincronizar_particion.py` a partir de `particion.csv`; si se vuelve a ejecutar
`preparar`, la columna regresa a `pendiente` y hay que sincronizarla de nuevo.

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

Análisis de errores del modelo final en prueba: `scripts/errores_node2vec.py` genera
`reports/node2vec_errores_prueba.csv` (rango, top 5 y una pista de causa por definición) y
`reports/node2vec_analisis_errores.md` reúne 17 casos clasificados a mano.

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

## Datos y licencias

- **SWOW-RP** (CC BY-NC-ND 3.0): descargar SWOW-RP22 desde
  [smallworldofwords.org](https://smallworldofwords.org/en/project/research) y copiar
  `SWOWRP.R70.20220426.csv` en `data/raw/`. La licencia no permite redistribuir obras derivadas,
  por eso las normas en CSV, el grafo y sus aristas se regeneran localmente y no se versionan.
  SWOW-RP no publica tiempos de respuesta: la columna `tiempo_medio` de las normas queda vacía
  y se usan dos ponderaciones basadas en la fuerza de asociación (100 − FA y −log p).
- **Conjunto de evaluación** (CC BY-SA 4.0, Wikcionario): `data/processed/corpus/corpus.csv`,
  con las columnas `concepto, definicion, fuente, particion` que pide el proyecto, más `id`, `pos`,
  `acepcion` y `licencia`. Se publica con su documentación en [`DATOS.md`](DATOS.md).

## Puntos extra

- **Grafo dirigido:** el grafo es dirigido (estímulo → respuesta). Cercanía e intermediación
  se calculan sobre el grafo dirigido y grado sobre el no dirigido, y node2vec se comparó con
  caminatas dirigidas y no dirigidas (P1 en `reports/discusion.md`).
- **Publicación del conjunto de evaluación** con licencia abierta (CC BY-SA 4.0) y diccionario
  de datos.

## Uso de IA generativa

Se usaron asistentes de IA generativa como apoyo para programar, depurar y redactar
documentación, en particular Claude (Anthropic). Todo el código fue revisado y ejecutado por el
equipo y todos los resultados provienen de las ejecuciones documentadas en este repositorio. No
se usó IA para generar normas, respuestas ni definiciones.

## Referencias

- Cabana, Á., Zugarramurdi, C., Valle-Lisboa, J. C., & De Deyne, S. (2024). The "Small World of
  Words" free association norms for Rioplatense Spanish. *Behavior Research Methods, 56*(2),
  968–985. https://doi.org/10.3758/s13428-023-02070-z
- Reyes-Magaña, J., Bel-Enguix, G., Gómez-Adorno, H., Sierra, G., Pinto, D., & Singh, V. (2019).
  A lexical search model based on word association norms. *Journal of Intelligent & Fuzzy
  Systems, 36*(5).
- Grover, A., & Leskovec, J. (2016). node2vec: Scalable feature learning for networks.
  *Proceedings of KDD 2016*, 855–864.
- Ylonen, T. (2022). Wiktextract: Wiktionary as Machine-Readable Structured Data. *LREC 2022*.
