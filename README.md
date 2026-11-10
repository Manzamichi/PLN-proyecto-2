# Diccionario inverso con normas de asociación SWOW-RP

Proyecto Unidad II — Procesamiento de Lenguaje Natural, FMAT-UADY.

## Estructura

```
PLN-proyecto-2/
├── pyproject.toml
├── data/
│   ├── raw/          # SWOW-RP descargado (no versionado)
│   └── processed/    # grafo, aristas y nodos generados (no versionado)
├── reports/          # caracterización topológica (versionado)
├── scripts/
│   ├── construir_grafo.py
│   └── caracterizar_grafo.py
├── src/diccionario_inverso/
│   ├── config.py     # rutas
│   ├── swow.py       # carga y fuerzas de asociación
│   ├── grafo.py      # construcción, ponderaciones, persistencia
│   ├── topologia.py  # caracterización y reportes
│   └── modelos/base.py  # interfaz común rankear(lemas)
└── tests/
```

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest
```

## Datos

1. Descargar **SWOW-RP22** desde https://smallworldofwords.org/en/project/research
2. Descomprimir y copiar el archivo balanceado `SWOW-RP.R70.<version>.csv` en `data/raw/`.

Licencia de los datos: CC BY-NC-ND 3.0. **No se suben al repositorio**, tampoco el grafo derivado.
Compartir `data/processed/` por Drive dentro del equipo.

## Construcción del grafo

```bash
python scripts/construir_grafo.py
python scripts/caracterizar_grafo.py
```

Opciones de `construir_grafo.py`:

| Opción | Efecto |
|---|---|
| `--entrada RUTA` | CSV explícito (por defecto busca `data/raw/**/*R70*.csv`) |
| `--min-frecuencia N` | Descarta pares cue→respuesta con menos de N apariciones |
| `--todas-las-respuestas` | Conserva respuestas que no son cue (por defecto se filtran) |
| `--sin-filtro-cfc` | No reduce a la mayor componente fuertemente conexa |

### Definición del grafo

- Dirigido `cue → respuesta`, usando R1+R2+R3.
- `p = frecuencia / respuestas válidas del cue`; `FA = 100·p`.
- Atributos por arista: `frecuencia`, `p` (similitud), `costo_fa = 100 − FA`, `costo_logp = −log p`.
- Nodos en minúsculas, NFC, con acentos; expresiones multipalabra con un espacio (`"fin de semana"`).
- Por defecto: solo respuestas que también son cue + mayor componente fuertemente conexa.

## Uso desde otros bloques

```python
import networkx as nx
from diccionario_inverso.grafo import cargar_grafo, a_no_dirigido, ESQUEMAS_COSTO, PESO_SIMILITUD

G = cargar_grafo()                                   # DiGraph
nx.shortest_path_length(G, "perro", "gato", weight=ESQUEMAS_COSTO["fa"])    # costo 100 − FA
nx.shortest_path_length(G, "perro", "gato", weight=ESQUEMAS_COSTO["logp"])  # costo −log p
U = a_no_dirigido(G)                                 # para comunicabilidad
# node2vec: usar weight=PESO_SIMILITUD ("p"), no los costos
```

Lista de nodos para filtrar el corpus: `data/processed/nodos.txt` (uno por línea).

Todo modelo implementa `diccionario_inverso.modelos.ModeloBusqueda`:

```python
class MiModelo:
    nombre = "cercania_logp"
    def rankear(self, lemas: Sequence[str], k: int | None = None) -> list[str]: ...
```

## Referencia de datos

Cabana, Á., Zugarramurdi, C., Valle-Lisboa, J. C., & De Deyne, S. (2024). The "Small World of Words"
free association norms for Rioplatense Spanish. *Behavior Research Methods, 56*(2), 968–985.
https://doi.org/10.3758/s13428-023-02070-z
