"""Modelo de referencia: ignora la definición y ordena por popularidad en el grafo.

Sirve como piso de comparación: un modelo útil debe superarlo con holgura.
"""

from __future__ import annotations

from typing import Sequence

import networkx as nx

from ..grafo import PESO_SIMILITUD


class ModeloPopularidad:
    """Ranking fijo por fuerza de entrada (suma de p de las aristas entrantes)."""

    nombre = "popularidad"

    def __init__(self, G: nx.DiGraph):
        fuerza = dict(G.in_degree(weight=PESO_SIMILITUD))
        self._orden = sorted(fuerza, key=lambda n: (-fuerza[n], n))

    def rankear(self, lemas: Sequence[str], k: int | None = None) -> list[str]:
        excluir = set(lemas)
        ranking = [n for n in self._orden if n not in excluir]
        return ranking[:k] if k is not None else ranking
