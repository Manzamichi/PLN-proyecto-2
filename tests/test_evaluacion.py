import json

import networkx as nx
import pandas as pd
import pytest

from diccionario_inverso.evaluacion import (
    cargar_ejemplos,
    evaluar_modelo,
    evaluar_registrado,
    particionar,
    rango,
    resumir,
)
from diccionario_inverso.modelos.referencia import ModeloPopularidad
from diccionario_inverso.modelos.registro import construir_modelo, modelos_disponibles


def test_rango():
    assert rango(["a", "b", "c"], "b") == 2
    assert rango(["a", "b"], "z") is None


def test_resumir():
    r = resumir([1, 3, None, 10])
    assert r["n"] == 4
    assert r["p@1"] == pytest.approx(0.25)
    assert r["p@3"] == pytest.approx(0.5)
    assert r["p@5"] == pytest.approx(0.5)
    assert r["mrr"] == pytest.approx((1 + 1 / 3 + 0 + 0.1) / 4)
    assert r["cobertura_modelo"] == pytest.approx(0.75)


def test_particionar_por_concepto_y_determinista():
    conceptos = [f"c{i}" for i in range(100)] * 3
    a = particionar(conceptos, 0.3, semilla=7)
    assert a == particionar(conceptos, 0.3, semilla=7)
    assert sum(v == "desarrollo" for v in a.values()) == 30
    assert set(a.values()) == {"desarrollo", "prueba"}


@pytest.fixture
def grafo():
    G = nx.DiGraph()
    for u, v, p in [("ladrar", "perro", 0.5), ("mascota", "perro", 0.4), ("mascota", "gato", 0.3),
                    ("perro", "mascota", 0.2), ("gato", "mascota", 0.6), ("maullar", "gato", 0.7),
                    ("perro", "ladrar", 0.1), ("gato", "maullar", 0.1)]:
        G.add_edge(u, v, p=p, frecuencia=1, costo_fa=100 - 100 * p, costo_logp=1 - p)
    return G


@pytest.fixture
def archivos(tmp_path):
    filas = [
        {"id": "1", "concepto": "perro", "lemas_en_grafo": ["ladrar", "mascota"], "cobertura_lexica": 1.0, "particion": "pendiente"},
        {"id": "2", "concepto": "gato", "lemas_en_grafo": ["maullar", "mascota"], "cobertura_lexica": 1.0, "particion": "pendiente"},
        {"id": "3", "concepto": "gato", "lemas_en_grafo": [], "cobertura_lexica": 0.0, "particion": "pendiente"},
    ]
    pre = tmp_path / "preprocesado.jsonl"
    pre.write_text("\n".join(json.dumps(f) for f in filas) + "\n", encoding="utf-8")
    part = tmp_path / "particion.csv"
    pd.DataFrame({"id": ["1", "2", "3"], "concepto": ["perro", "gato", "gato"],
                  "particion": ["prueba"] * 3}).to_csv(part, index=False)
    return pre, part


def test_cargar_ejemplos(archivos):
    pre, part = archivos
    ejemplos = cargar_ejemplos("prueba", ruta_preprocesado=pre, ruta_particion=part)
    assert [e.id for e in ejemplos] == ["1", "2", "3"]
    assert cargar_ejemplos("desarrollo", ruta_preprocesado=pre, ruta_particion=part) == []


def test_evaluar_grado_encuentra_objetivos(grafo, archivos):
    pre, part = archivos
    ejemplos = cargar_ejemplos("prueba", ruta_preprocesado=pre, ruta_particion=part)
    detalle, resumen = evaluar_registrado("grado", ejemplos, G=grafo)
    assert list(detalle["rango"].iloc[:2]) == [1, 1]
    assert resumen["p@1"] == pytest.approx(2 / 3)       # la definición sin lemas cuenta como fallo
    assert resumen["definiciones_sin_lemas"] == 1


def test_popularidad_excluye_lemas(grafo):
    m = ModeloPopularidad(grafo)
    assert "mascota" not in m.rankear(["mascota"])
    _, resumen = evaluar_modelo(m, [])
    assert resumen["n"] == 0


def test_registro():
    assert {"popularidad", "grado", "cercania_fa", "intermediacion_logp"} <= set(modelos_disponibles())
    with pytest.raises(KeyError):
        construir_modelo("inexistente", nx.DiGraph())
