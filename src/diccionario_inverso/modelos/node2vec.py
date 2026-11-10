"""Modelo híbrido con node2vec: embeddings del grafo y composición de la definición.

La definición se representa como la suma de los vectores de sus lemas (o la
suma ponderada por IDF) y los candidatos se ordenan por similitud coseno.

Uso desde otros bloques:
    from diccionario_inverso.grafo import a_no_dirigido, cargar_grafo
    from diccionario_inverso.modelos.node2vec import ModeloNode2Vec, entrenar, generar_caminatas

    caminatas = generar_caminatas(a_no_dirigido(cargar_grafo()), walk_length=80, num_walks=10, p=1, q=1)
    modelo = ModeloNode2Vec(entrenar(caminatas, dimensiones=300))
    modelo.rankear(["insecto", "miel"], k=10)
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Sequence

import networkx as nx
import numpy as np
from gensim.models import KeyedVectors
from node2vec import Node2Vec

from ..grafo import PESO_SIMILITUD

SEMILLA = 42

# La primera es la configuración usada en clase (dimensions=300 y el resto por defecto).
CONFIGURACIONES = [
    {"dimensions": 300, "walk_length": 80, "num_walks": 10, "p": 1, "q": 1},
    {"dimensions": 100, "walk_length": 80, "num_walks": 10, "p": 1, "q": 1},
    {"dimensions": 100, "walk_length": 40, "num_walks": 10, "p": 1, "q": 0.5},
    {"dimensions": 100, "walk_length": 40, "num_walks": 10, "p": 1, "q": 2},
]


def filtrar_aristas(grafo: nx.Graph, frecuencia_min: int) -> nx.Graph:
    """Copia del grafo sin las aristas con frecuencia menor a frecuencia_min."""
    copia = grafo.copy()
    debiles = [(u, v) for u, v, f in copia.edges(data="frecuencia") if f < frecuencia_min]
    copia.remove_edges_from(debiles)
    return copia


def generar_caminatas(grafo: nx.Graph, walk_length: int, num_walks: int, p: float, q: float,
                      peso: str = PESO_SIMILITUD, workers: int = 1, semilla: int = SEMILLA) -> Node2Vec:
    """Caminatas aleatorias de node2vec; el peso de la arista es la probabilidad de paso."""
    caminatas = Node2Vec(grafo, walk_length=walk_length, num_walks=num_walks, p=p, q=q,
                         weight_key=peso, workers=workers, seed=semilla, quiet=True)
    # Las probabilidades precalculadas solo sirven para caminar; se liberan para ahorrar memoria.
    caminatas.d_graph = None
    return caminatas


def entrenar(caminatas: Node2Vec, dimensiones: int, semilla: int = SEMILLA) -> KeyedVectors:
    modelo = caminatas.fit(vector_size=dimensiones, window=10, min_count=1, seed=semilla)
    return modelo.wv


def calcular_idf(definiciones: Sequence[Sequence[str]]) -> tuple[dict[str, float], float]:
    """IDF(t) = log10(N / df(t)), tomando cada definición como un documento.

    Devuelve el diccionario de IDF y el valor para un lema que no aparece en
    estas definiciones: log10(N), como si estuviera en un solo documento.
    """
    n = len(definiciones)
    df = Counter()
    for lemas in definiciones:
        df.update(set(lemas))
    idf = {lema: math.log10(n / df[lema]) for lema in df}
    return idf, math.log10(n)


class ModeloNode2Vec:
    """Cumple ModeloBusqueda. Con idf=None usa la suma simple de los vectores."""

    def __init__(self, wv: KeyedVectors, idf: dict[str, float] | None = None,
                 idf_por_defecto: float = 0.0, nombre: str | None = None):
        self.wv = wv
        self.idf = idf
        self.idf_por_defecto = idf_por_defecto
        if nombre is None:
            nombre = "node2vec_suma" if idf is None else "node2vec_suma_idf"
        self.nombre = nombre

    def vector_definicion(self, lemas: Sequence[str]):
        utiles = [lema for lema in lemas if lema in self.wv]
        if len(utiles) == 0:
            return None
        if self.idf is None:
            pesos = [1.0] * len(utiles)
        else:
            pesos = [self.idf.get(lema, self.idf_por_defecto) for lema in utiles]
        if sum(pesos) == 0:
            pesos = [1.0] * len(utiles)
        suma = 0
        for lema, peso in zip(utiles, pesos):
            suma += peso * self.wv[lema]
        return suma

    def rankear(self, lemas: Sequence[str], k: int | None = None) -> list[str]:
        suma = self.vector_definicion(lemas)
        if suma is None:
            return []
        # Con topn=None, most_similar devuelve la similitud con todo el vocabulario.
        similitudes = self.wv.most_similar(positive=[suma], topn=None)
        orden = np.argsort(-similitudes, kind="stable")
        entrada = set(lemas)
        candidatos = []
        for i in orden:
            nodo = self.wv.index_to_key[i]
            if nodo not in entrada:
                candidatos.append(nodo)
                if k is not None and len(candidatos) == k:
                    break
        return candidatos

    def guardar(self, ruta: Path) -> None:
        """Vectores con KeyedVectors.save (conserva IDs con espacios) e IDF en un JSON aparte."""
        ruta = Path(ruta)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        self.wv.save(str(ruta))
        datos = {"nombre": self.nombre, "idf": self.idf, "idf_por_defecto": self.idf_por_defecto}
        ruta.with_suffix(".json").write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def cargar(cls, ruta: Path) -> ModeloNode2Vec:
        ruta = Path(ruta)
        wv = KeyedVectors.load(str(ruta))
        datos = json.loads(ruta.with_suffix(".json").read_text(encoding="utf-8"))
        return cls(wv, datos["idf"], datos["idf_por_defecto"], datos["nombre"])


def leer_corpus(ruta: Path) -> list[dict]:
    """Filas de preprocesado.jsonl con concepto, lemas_en_grafo y particion."""
    filas = []
    with Path(ruta).open(encoding="utf-8") as archivo:
        for linea in archivo:
            if linea.strip():
                fila = json.loads(linea)
                filas.append({"concepto": fila["concepto"], "definicion": fila["definicion"],
                              "lemas": fila["lemas_en_grafo"], "particion": fila["particion"]})
    return filas


def particion_provisional(concepto: str) -> str:
    """Partición determinista por concepto (mitad y mitad) mientras no haya una asignada."""
    primer_byte = hashlib.sha256(concepto.encode("utf-8")).digest()[0]
    return "desarrollo" if primer_byte % 2 == 0 else "prueba"


def separar_particiones(filas: list[dict]) -> tuple[list[dict], list[dict], bool]:
    """Devuelve desarrollo, prueba y si la partición es provisional.

    Si alguna fila no dice desarrollo o prueba (p. ej. "pendiente"), se usa la
    partición provisional para todas, sin modificar el corpus.
    """
    provisional = any(f["particion"] not in ("desarrollo", "prueba") for f in filas)
    desarrollo, prueba = [], []
    for fila in filas:
        particion = particion_provisional(fila["concepto"]) if provisional else fila["particion"]
        if particion == "desarrollo":
            desarrollo.append(fila)
        else:
            prueba.append(fila)
    return desarrollo, prueba, provisional


def precision(k: int, candidatos: list[str], concepto: str) -> int:
    return 1 if concepto in candidatos[:k] else 0


def rango_reciproco(candidatos: list[str], concepto: str) -> float:
    if concepto in candidatos:
        return 1 / (candidatos.index(concepto) + 1)
    return 0


def evaluar(modelo: ModeloNode2Vec, filas: list[dict]) -> dict:
    p_1 = p_3 = p_5 = mrr = con_lemas = lemas_utiles = 0
    for fila in filas:
        utiles = len([lema for lema in fila["lemas"] if lema in modelo.wv])
        lemas_utiles += utiles
        if utiles > 0:
            con_lemas += 1
        candidatos = modelo.rankear(fila["lemas"])
        p_1 += precision(1, candidatos, fila["concepto"])
        p_3 += precision(3, candidatos, fila["concepto"])
        p_5 += precision(5, candidatos, fila["concepto"])
        mrr += rango_reciproco(candidatos, fila["concepto"])
    total = len(filas)
    return {
        "p@1": round(p_1 / total, 3),
        "p@3": round(p_3 / total, 3),
        "p@5": round(p_5 / total, 3),
        "MRR": round(mrr / total, 3),
        "cobertura": round(con_lemas / total, 3),
        "lemas_utiles": round(lemas_utiles / total, 2),
    }
