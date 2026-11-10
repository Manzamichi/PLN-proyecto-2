import math

import networkx as nx
import pandas as pd
import pytest

from diccionario_inverso.grafo import (
    OpcionesGrafo,
    a_no_dirigido,
    construir_grafo,
    mayor_componente_fuerte,
)
from diccionario_inverso.swow import a_formato_largo, calcular_fuerzas, cargar_respuestas
from diccionario_inverso.topologia import caracterizar

FILAS = [
    # cue, R1, R2, R3
    ("Perro", "gato", "hueso", "No more responses"),
    ("perro", "gato", "perro", "ladrido"),
    ("gato", "perro", "ratón", ""),
    ("gato", "perro", "Ratón ", "NA"),
    ("ratón", "gato", "queso", "computadora"),
    ("aislado", "nada", "", ""),
]


@pytest.fixture
def csv_respuestas(tmp_path):
    ruta = tmp_path / "SWOW-RP.R70.test.csv"
    pd.DataFrame(FILAS, columns=["cue", "R1", "R2", "R3"]).assign(participantID=1).to_csv(ruta, index=False)
    return ruta


@pytest.fixture
def fuerzas(csv_respuestas):
    return calcular_fuerzas(a_formato_largo(cargar_respuestas(csv_respuestas)))


def fila(fuerzas, cue, resp):
    return fuerzas[(fuerzas.cue == cue) & (fuerzas.response == resp)].iloc[0]


def test_fuerzas_normaliza_y_excluye_vacios(fuerzas):
    # perro: 5 válidas (gato, hueso, gato, perro, ladrido); bucle cuenta en el denominador
    f = fila(fuerzas, "perro", "gato")
    assert f.frecuencia == 2 and f.total_cue == 5
    assert f.p == pytest.approx(0.4)
    assert f.costo_fa == pytest.approx(60.0)
    assert f.costo_logp == pytest.approx(-math.log(0.4))
    assert fila(fuerzas, "gato", "ratón").frecuencia == 2  # "Ratón " normalizado
    assert not ((fuerzas.cue == "perro") & (fuerzas.response == "perro")).any()


def test_grafo_solo_cues_y_cfc(fuerzas):
    G = construir_grafo(fuerzas, OpcionesGrafo(solo_cues=True))
    assert not G.has_node("hueso") and G.has_node("aislado")
    H = mayor_componente_fuerte(G)
    assert set(H) == {"perro", "gato", "ratón"}
    assert nx.is_strongly_connected(H)
    assert H["perro"]["gato"]["costo_fa"] == pytest.approx(60.0)


def test_grafo_todas_las_respuestas(fuerzas):
    G = construir_grafo(fuerzas, OpcionesGrafo(solo_cues=False))
    assert G.has_node("hueso") and G.nodes["hueso"]["es_cue"] is False


def test_no_dirigido_simetriza_p(fuerzas):
    U = a_no_dirigido(mayor_componente_fuerte(construir_grafo(fuerzas)))
    p_esperada = (0.4 + 2 / 4) / 2  # perro->gato 2/5, gato->perro 2/4
    assert U["perro"]["gato"]["p"] == pytest.approx(p_esperada)
    assert U["gato"]["perro"]["costo_logp"] == pytest.approx(-math.log(p_esperada))


def test_caracterizar(fuerzas):
    H = mayor_componente_fuerte(construir_grafo(fuerzas))
    r = caracterizar(H, clustering_exacto=True)
    assert r["nodos"] == 3 and r["componentes_fuertes"] == 1
    assert r["grado_medio_salida"] == pytest.approx(r["aristas_dirigidas"] / 3)
