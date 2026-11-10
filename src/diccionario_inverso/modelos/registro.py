"""Registro de modelos evaluables por nombre.

Para agregar un modelo (p. ej. node2vec), en este archivo:

    @registrar("node2vec_promedio")
    def _node2vec_promedio(G):
        from .node2vec import ModeloNode2Vec
        return ModeloNode2Vec(G, composicion="promedio")

La fábrica recibe el grafo dirigido y devuelve un objeto con rankear(lemas, k).
"""

from __future__ import annotations

from typing import Callable

import networkx as nx

from .base import ModeloBusqueda

Fabrica = Callable[[nx.DiGraph], ModeloBusqueda]
_FABRICAS: dict[str, Fabrica] = {}


def registrar(nombre: str) -> Callable[[Fabrica], Fabrica]:
    def decorador(fabrica: Fabrica) -> Fabrica:
        if nombre in _FABRICAS:
            raise ValueError(f"Modelo ya registrado: {nombre}")
        _FABRICAS[nombre] = fabrica
        return fabrica

    return decorador


def modelos_disponibles() -> list[str]:
    return list(_FABRICAS)


def construir_modelo(nombre: str, G: nx.DiGraph) -> ModeloBusqueda:
    try:
        fabrica = _FABRICAS[nombre]
    except KeyError:
        raise KeyError(f"Modelo desconocido: {nombre}. Disponibles: {modelos_disponibles()}") from None
    return fabrica(G)


# ------------------------------------------------------------- modelos del proyecto

@registrar("popularidad")
def _popularidad(G):
    from .referencia import ModeloPopularidad
    return ModeloPopularidad(G)


@registrar("grado")
def _grado(G):
    from .centralidades import ModeloGradoReducido
    return ModeloGradoReducido(G)


@registrar("cercania_fa")
def _cercania_fa(G):
    from .centralidades import ModeloCercaniaReducido
    return ModeloCercaniaReducido(G, esquema_costo="fa")


@registrar("cercania_logp")
def _cercania_logp(G):
    from .centralidades import ModeloCercaniaReducido
    return ModeloCercaniaReducido(G, esquema_costo="logp")


@registrar("intermediacion_fa")
def _intermediacion_fa(G):
    from .centralidades import ModeloIntermediacionReducido
    return ModeloIntermediacionReducido(G, esquema_costo="fa")


@registrar("intermediacion_logp")
def _intermediacion_logp(G):
    from .centralidades import ModeloIntermediacionReducido
    return ModeloIntermediacionReducido(G, esquema_costo="logp")
