"""Construcción, transformación y persistencia del grafo de asociaciones.

Grafo dirigido cue -> respuesta. Atributos por arista:
    frecuencia, p (similitud), costo_fa (100 - FA), costo_logp (-log p).
Atributo por nodo: es_cue (bool).

Uso desde otros bloques:
    from diccionario_inverso.grafo import cargar_grafo, ESQUEMAS_COSTO
    G = cargar_grafo()
    nx.shortest_path_length(G, "perro", "gato", weight=ESQUEMAS_COSTO["logp"])
"""

from __future__ import annotations

import logging
import math
import pickle
from dataclasses import asdict, dataclass
from pathlib import Path

import networkx as nx
import pandas as pd

from .config import RUTA_GRAFO

logger = logging.getLogger(__name__)

ATRIBUTOS_ARISTA = ("frecuencia", "p", "costo_fa", "costo_logp")
PESO_SIMILITUD = "p"
ESQUEMAS_COSTO = {"fa": "costo_fa", "logp": "costo_logp"}


@dataclass(frozen=True)
class OpcionesGrafo:
    """min_frecuencia: descarta pares con menos apariciones.
    solo_cues: conserva solo respuestas que también son cues (metodología SWOW);
    garantiza que todo nodo tenga aristas de salida.
    """

    min_frecuencia: int = 1
    solo_cues: bool = True


def construir_grafo(fuerzas: pd.DataFrame, opciones: OpcionesGrafo = OpcionesGrafo()) -> nx.DiGraph:
    cues = set(fuerzas["cue"].unique())
    aristas = fuerzas[fuerzas["frecuencia"] >= opciones.min_frecuencia]
    if opciones.solo_cues:
        aristas = aristas[aristas["response"].isin(cues)]

    G = nx.DiGraph()
    G.add_nodes_from(cues)
    G.add_edges_from(
        (u, v, {"frecuencia": int(f), "p": float(p), "costo_fa": float(cf), "costo_logp": float(cl)})
        for u, v, f, p, cf, cl in aristas[["cue", "response", *ATRIBUTOS_ARISTA]].itertuples(
            index=False, name=None
        )
    )
    nx.set_node_attributes(G, {n: n in cues for n in G}, "es_cue")
    G.graph.update(fuente="SWOW-RP", **asdict(opciones))
    logger.info("Grafo completo: %d nodos, %d aristas", G.number_of_nodes(), G.number_of_edges())
    return G


def mayor_componente_fuerte(G: nx.DiGraph) -> nx.DiGraph:
    """Subgrafo inducido por la mayor componente fuertemente conexa."""
    nodos = max(nx.strongly_connected_components(G), key=len)
    H = G.subgraph(nodos).copy()
    H.graph.update(G.graph, filtro="mayor_componente_fuerte")
    logger.info("Mayor CFC: %d nodos, %d aristas", H.number_of_nodes(), H.number_of_edges())
    return H


def a_no_dirigido(G: nx.DiGraph) -> nx.Graph:
    """Versión no dirigida para métricas que la requieren (p. ej. comunicabilidad).

    p simétrica = (p(u->v) + p(v->u)) / 2; los costos se recalculan desde ella.
    """
    U = nx.Graph()
    U.add_nodes_from(G.nodes(data=True))
    for u, v, d in G.edges(data=True):
        if U.has_edge(u, v):
            continue
        inversa = G.get_edge_data(v, u)
        p = (d["p"] + (inversa["p"] if inversa else 0.0)) / 2
        U.add_edge(
            u,
            v,
            frecuencia=d["frecuencia"] + (inversa["frecuencia"] if inversa else 0),
            p=p,
            costo_fa=100.0 - 100.0 * p,
            costo_logp=-math.log(p),
        )
    U.graph.update(G.graph, dirigido=False)
    return U


def guardar_grafo(G: nx.DiGraph, ruta: Path = RUTA_GRAFO) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("wb") as f:
        pickle.dump(G, f, protocol=pickle.HIGHEST_PROTOCOL)
    logger.info("Grafo guardado en %s", ruta)


def cargar_grafo(ruta: Path = RUTA_GRAFO) -> nx.DiGraph:
    if not ruta.is_file():
        raise FileNotFoundError(f"{ruta} no existe. Ejecuta scripts/construir_grafo.py")
    with ruta.open("rb") as f:
        return pickle.load(f)


def exportar_aristas(G: nx.DiGraph, ruta: Path) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    df = nx.to_pandas_edgelist(G, source="cue", target="response")
    df = df[["cue", "response", *ATRIBUTOS_ARISTA]].sort_values(["cue", "frecuencia"], ascending=[True, False])
    df.to_csv(ruta, index=False, encoding="utf-8")


def exportar_nodos(G: nx.DiGraph, ruta: Path) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text("\n".join(sorted(G.nodes)) + "\n", encoding="utf-8")
