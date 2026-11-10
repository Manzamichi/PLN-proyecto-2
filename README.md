# PLN-proyecto-2

Corpus y preprocesamiento para el diccionario inverso con SWOW-RP.

## Instalación y ejecución

Python 3.12. Desde la raíz del proyecto, en PowerShell:

```powershell
uv venv --python 3.12 .venv
uv pip install --python .venv/Scripts/python.exe -r requirements.lock.txt
.venv/Scripts/python.exe -m corpus preparar --nodos data/nodos_activos.csv
```

Entrada: CSV de nodos con columnas `nodo,grado`; se excluyen los de grado cero.
También se acepta TXT con un nodo activo por línea o JSON con una lista de IDs.
El banco `data/corpus_fuente.csv` está incluido y aún requiere filtrarse contra
los nodos del grafo. `particion=pendiente` debe asignarse a desarrollo/prueba.

Salidas en `data/processed/`: `corpus.csv`, `preprocesado.jsonl`,
`descartadas.csv` y `cobertura.json`. El comando devuelve código 2 si quedan
menos de 300 definiciones. Los casos sin cobertura permanecen en el corpus.

Para integrar los modelos:

```python
from pathlib import Path
from corpus.archivos import leer_nodos
from corpus.preprocesamiento import Preprocesador

pre = Preprocesador(leer_nodos(Path("data/nodos_activos.csv")))
lemas = pre.lemas_para_modelo(definicion)
candidatos = modelo.rankear(lemas)
```

Los lemas conservan repeticiones e IDs originales. Los modelos deben excluirlos
de los candidatos y devolver `[]` cuando no haya lemas. El campo `concepto`
se utiliza exclusivamente para evaluar.

## Reconstrucción y pruebas

```powershell
.venv/Scripts/python.exe -m corpus descargar
.venv/Scripts/python.exe -m corpus extraer
.venv/Scripts/python.exe -m unittest discover -s tests -v
```

Si el dump ya existe en `data/raw/`, ejecutar solo `extraer`.
`corpus_fuente.json` registra los hashes y filtros;
`corpus_fuente_menciones.csv` contiene las glosas excluidas por revelar el objetivo.

## Procedencia de los datos

Definiciones de los colaboradores de [Wikcionario](https://es.wiktionary.org/),
edición española, distribuidas por [Kaikki](https://kaikki.org/dictionary/rawdata.html)
mediante Wiktextract. Cada fila conserva su enlace de atribución en `fuente`.
Texto bajo [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
Se seleccionaron lemas, normalizaron conceptos y espacios, filtraron glosas y
eliminaron duplicados, con un máximo de tres acepciones por concepto.

Extractor: Ylonen, T. (2022).
[Wiktextract: Wiktionary as Machine-Readable Structured Data](https://aclanthology.org/2022.lrec-1.140/).
