import pytest
import networkx as nx
from diccionario_inverso.modelos.centralidades import (
    ModeloCercaniaReducido,
    ModeloIntermediacionReducido,
    ModeloGradoReducido,
)

@pytest.fixture
def grafo_demo():
    G = nx.DiGraph()
    # Agregamos el atributo 'frecuencia' a todas las aristas
    G.add_edge("perro", "ladrar", costo_fa=10.0, costo_logp=0.5, p=0.9, frecuencia=10)
    G.add_edge("perro", "mascota", costo_fa=20.0, costo_logp=1.2, p=0.7, frecuencia=5)
    G.add_edge("gato", "mascota", costo_fa=15.0, costo_logp=0.8, p=0.8, frecuencia=8)
    G.add_edge("mascota", "animal", costo_fa=5.0, costo_logp=0.2, p=0.95, frecuencia=20)
    return G

def test_modelo_cercania(grafo_demo):
    modelo = ModeloCercaniaReducido(G=grafo_demo, esquema_costo="costo_fa")
    ranking = modelo.rankear(lemas=["perro", "gato"])
    
    assert "mascota" in ranking
    assert "perro" not in ranking  # Exclusión de lemas de la propia definición

def test_modelo_grado(grafo_demo):
    modelo = ModeloGradoReducido(G=grafo_demo)
    ranking = modelo.rankear(lemas=["perro", "gato"])
    
    assert ranking[0] == "mascota"  # Conectado a ambos lemas