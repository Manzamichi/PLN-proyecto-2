"""
Módulo de modelos de búsqueda léxica basados en centralidad sobre el subgrafo reducido.
"""

from typing import Sequence
import networkx as nx

from diccionario_inverso.modelos.base import ModeloBusqueda
from diccionario_inverso.grafo import (
    cargar_grafo,
    a_no_dirigido,
    ESQUEMAS_COSTO,
    PESO_SIMILITUD,
)


def extraer_subgrafo_reducido(G: nx.Graph | nx.DiGraph, lemas: Sequence[str], radio: int = 1) -> nx.Graph | nx.DiGraph:
    """
    Construye el subgrafo reducido compuesto por los lemas presentes en el grafo
    y su vecindad a 'radio' saltos (por defecto k=1).
    """
    lemas_validos = set(l for l in lemas if l in G)
    if not lemas_validos:
        return G.subgraph([]).copy()

    nodos_subgrafo = set(lemas_validos)
    for nodo in lemas_validos:
        # Extrae vecinos a distancia 1 (dirigidos o no dirigidos)
        vecinos = set(G.successors(nodo)) if G.is_directed() else set(G.neighbors(nodo))
        nodos_subgrafo.update(vecinos)

        if radio > 1 and G.is_directed():
            for v in vecinos:
                nodos_subgrafo.update(G.successors(v))

    return G.subgraph(nodos_subgrafo).copy()


class ModeloCercaniaReducido(ModeloBusqueda):
    """
    Modelo de cercanía (Closeness Centrality) sobre el subgrafo reducido.
    Suma de las distancias más cortas desde los lemas de la definición hacia los candidatos.
    """

    def __init__(self, G: nx.DiGraph | None = None, esquema_costo: str = "fa", radio_vecindad: int = 1):
        self.G = G if G is not None else cargar_grafo()
        self.esquema_costo = ESQUEMAS_COSTO.get(esquema_costo, esquema_costo)
        self.radio_vecindad = radio_vecindad
        self.nombre = f"cercania_{esquema_costo}_reducido"

    def rankear(self, lemas: Sequence[str], k: int | None = None) -> list[str]:
        lemas_validos = list(dict.fromkeys(l for l in lemas if l in self.G))
        if not lemas_validos:
            return []

        # Subgrafo reducido de la vecindad de los lemas
        sub_G = extraer_subgrafo_reducido(self.G, lemas_validos, radio=self.radio_vecindad)

        # Un Dijkstra por lema (en vez de uno por par lema-candidato): mismo resultado
        distancias = [
            nx.single_source_dijkstra_path_length(sub_G, lema, weight=self.esquema_costo)
            for lema in lemas_validos
        ]
        candidatos = set(sub_G) - set(lemas_validos)
        for d in distancias:
            candidatos &= d.keys()  # alcanzable desde todos los lemas

        # A menor distancia total, mayor relevancia; desempate alfabético
        puntajes = {c: sum(d[c] for d in distancias) for c in candidatos}
        candidatos_ordenados = sorted(puntajes, key=lambda c: (puntajes[c], c))
        return candidatos_ordenados[:k] if k is not None else candidatos_ordenados


class ModeloIntermediacionReducido(ModeloBusqueda):
    """
    Modelo de intermediación (Betweenness Centrality) sobre el subgrafo reducido.
    """

    def __init__(self, G: nx.DiGraph | None = None, esquema_costo: str = "fa", radio_vecindad: int = 1):
        self.G = G if G is not None else cargar_grafo()
        self.esquema_costo = ESQUEMAS_COSTO.get(esquema_costo, esquema_costo)
        self.radio_vecindad = radio_vecindad
        self.nombre = f"intermediacion_{esquema_costo}_reducido"

    def rankear(self, lemas: Sequence[str], k: int | None = None) -> list[str]:
        lemas_validos = [l for l in lemas if l in self.G]
        if not lemas_validos:
            return []

        sub_G = extraer_subgrafo_reducido(self.G, lemas_validos, radio=self.radio_vecindad)
        
        # Intermediación calculada sobre el subgrafo con el peso como distancia
        btw = nx.betweenness_centrality(sub_G, weight=self.esquema_costo, normalized=True)

        # Excluir lemas de la propia definición
        puntajes = {nodo: score for nodo, score in btw.items() if nodo not in lemas_validos}
        
        candidatos_ordenados = sorted(puntajes.keys(), key=lambda x: puntajes[x], reverse=True)
        return candidatos_ordenados[:k] if k is not None else candidatos_ordenados


class ModeloGradoReducido(ModeloBusqueda):
    """
    Modelo de grado / fuerza de conexión sobre el subgrafo no dirigido.
    Suma de las fuerzas de asociación ('p') directas entre los lemas y los nodos vecinos.
    """

    def __init__(self, G: nx.DiGraph | None = None, radio_vecindad: int = 1):
        di_graph = G if G is not None else cargar_grafo()
        self.G = a_no_dirigido(di_graph)
        self.radio_vecindad = radio_vecindad
        self.nombre = "grado_asociacion_reducido"

    def rankear(self, lemas: Sequence[str], k: int | None = None) -> list[str]:
        lemas_validos = [l for l in lemas if l in self.G]
        if not lemas_validos:
            return []

        sub_G = extraer_subgrafo_reducido(self.G, lemas_validos, radio=self.radio_vecindad)
        puntajes: dict[str, float] = {}

        for candidato in sub_G.nodes():
            if candidato in lemas_validos:
                continue

            # Suma ponderada del peso 'p' de las aristas conectadas a los lemas en el subgrafo
            fuerza_total = 0.0
            for lema in lemas_validos:
                if sub_G.has_edge(candidato, lema):
                    fuerza_total += sub_G[candidato][lema].get(PESO_SIMILITUD, 1.0)
            
            if fuerza_total > 0:
                puntajes[candidato] = fuerza_total

        candidatos_ordenados = sorted(puntajes.keys(), key=lambda x: puntajes[x], reverse=True)
        return candidatos_ordenados[:k] if k is not None else candidatos_ordenados