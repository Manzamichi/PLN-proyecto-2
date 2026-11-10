"""Modelo node2vec sobre un grafo sintético pequeño; solo comprueba software, no es SWOW-RP."""

import networkx as nx
import numpy as np
import pytest

from diccionario_inverso.grafo import a_no_dirigido
from diccionario_inverso.modelos import ModeloBusqueda
from diccionario_inverso.modelos.node2vec import (
    ModeloNode2Vec,
    calcular_idf,
    entrenar,
    evaluar,
    filtrar_aristas,
    generar_caminatas,
    particion_provisional,
    separar_particiones,
)

ARISTAS = [
    # cue, respuesta, frecuencia, p
    ("frío", "hielo", 3, 0.5),
    ("hielo", "frío", 2, 0.4),
    ("frío", "muñeco de nieve", 1, 0.2),
    ("muñeco de nieve", "frío", 2, 0.5),
    ("muñeco de nieve", "hielo", 1, 0.3),
    ("hielo", "agua", 2, 0.4),
    ("agua", "mar", 3, 0.6),
    ("mar", "agua", 2, 0.5),
    ("mar", "playa", 2, 0.4),
    ("playa", "sol", 3, 0.6),
    ("sol", "calor", 3, 0.6),
    ("calor", "frío", 1, 0.2),
    ("calor", "sol", 2, 0.5),
]


def grafo_sintetico() -> nx.Graph:
    G = nx.DiGraph()
    for u, v, f, p in ARISTAS:
        G.add_edge(u, v, frecuencia=f, p=p)
    return a_no_dirigido(G)


def entrenar_pequeno(semilla=42):
    caminatas = generar_caminatas(grafo_sintetico(), walk_length=10, num_walks=5, p=1, q=1, semilla=semilla)
    return entrenar(caminatas, dimensiones=16, semilla=semilla)


@pytest.fixture(scope="module")
def wv():
    return entrenar_pequeno()


@pytest.fixture(scope="module")
def modelo(wv):
    return ModeloNode2Vec(wv)


def test_cumple_modelo_busqueda(modelo):
    assert isinstance(modelo, ModeloBusqueda)
    assert modelo.nombre == "node2vec_suma"


def test_vocabulario_conserva_id_multipalabra(wv):
    assert "muñeco de nieve" in wv
    assert set(wv.index_to_key) == set(grafo_sintetico())


def test_excluye_lemas_de_entrada_y_rankea_todo(modelo, wv):
    lemas = ["frío", "muñeco de nieve", "frío"]
    candidatos = modelo.rankear(lemas)
    assert "frío" not in candidatos and "muñeco de nieve" not in candidatos
    assert len(candidatos) == len(wv) - 2
    assert len(set(candidatos)) == len(candidatos)


def test_sin_lemas_devuelve_lista_vacia(modelo):
    assert modelo.rankear([]) == []
    assert modelo.rankear(["fuera del grafo"]) == []


def test_respeta_k(modelo):
    completo = modelo.rankear(["sol", "playa"])
    assert modelo.rankear(["sol", "playa"], k=3) == completo[:3]
    assert len(modelo.rankear(["sol", "playa"], k=100)) == len(completo)


def test_suma_idf_pondera_los_lemas(wv):
    idf, por_defecto = calcular_idf([["frío", "hielo"], ["frío", "mar"], ["sol"]])
    assert idf["frío"] == pytest.approx(np.log10(3 / 2))
    assert idf["sol"] == pytest.approx(np.log10(3))
    assert por_defecto == pytest.approx(np.log10(3))
    modelo = ModeloNode2Vec(wv, idf, por_defecto)
    assert modelo.nombre == "node2vec_suma_idf"
    esperado = idf["frío"] * wv["frío"] + idf["hielo"] * wv["hielo"]
    assert np.allclose(modelo.vector_definicion(["frío", "hielo"]), esperado)


def test_guardar_y_cargar(tmp_path, wv):
    idf, por_defecto = calcular_idf([["frío", "muñeco de nieve"], ["sol"]])
    original = ModeloNode2Vec(wv, idf, por_defecto)
    ruta = tmp_path / "node2vec.kv"
    original.guardar(ruta)
    cargado = ModeloNode2Vec.cargar(ruta)
    assert cargado.nombre == original.nombre
    assert cargado.idf == original.idf
    assert "muñeco de nieve" in cargado.wv
    assert np.array_equal(cargado.wv.vectors, wv.vectors)
    lemas = ["muñeco de nieve", "agua"]
    assert cargado.rankear(lemas) == original.rankear(lemas)


def test_reproducible_con_la_misma_semilla(wv):
    otra = entrenar_pequeno()
    assert otra.index_to_key == wv.index_to_key
    assert np.array_equal(otra.vectors, wv.vectors)


def test_evaluar_metricas():
    # Vectores fijos: "b" es el más parecido a "a", luego "c".
    from gensim.models import KeyedVectors

    kv = KeyedVectors(vector_size=2)
    kv.add_vectors(["a", "b", "c", "d"], np.array([[1, 0], [0.9, 0.1], [0.5, 0.5], [-1, 0]], dtype=np.float32))
    modelo = ModeloNode2Vec(kv)
    assert modelo.rankear(["a"]) == ["b", "c", "d"]
    filas = [{"concepto": "b", "lemas": ["a"]}, {"concepto": "c", "lemas": ["a"]}, {"concepto": "d", "lemas": []}]
    metricas = evaluar(modelo, filas)
    assert metricas["p@1"] == pytest.approx(0.333)
    assert metricas["p@3"] == pytest.approx(0.667)
    assert metricas["MRR"] == pytest.approx(round((1 + 1 / 2) / 3, 3))
    assert metricas["cobertura"] == pytest.approx(0.667)
    assert metricas["lemas_utiles"] == pytest.approx(0.67)


def test_particion_provisional_por_concepto():
    filas = [{"concepto": c, "particion": "pendiente"} for c in ["perro", "perro", "gato", "casa", "muñeco de nieve"]]
    desarrollo, prueba, provisional = separar_particiones(filas)
    assert provisional
    assert len(desarrollo) + len(prueba) == len(filas)
    assert not {f["concepto"] for f in desarrollo} & {f["concepto"] for f in prueba}
    assert particion_provisional("perro") == particion_provisional("perro")


def test_respeta_particion_asignada():
    filas = [{"concepto": "perro", "particion": "prueba"}, {"concepto": "gato", "particion": "desarrollo"}]
    desarrollo, prueba, provisional = separar_particiones(filas)
    assert not provisional
    assert [f["concepto"] for f in prueba] == ["perro"]


def test_filtrar_aristas_debiles():
    G = grafo_sintetico()
    H = filtrar_aristas(G, 3)
    assert set(H) == set(G)
    assert all(f >= 3 for _, _, f in H.edges(data="frecuencia"))
    assert H.number_of_edges() < G.number_of_edges()
