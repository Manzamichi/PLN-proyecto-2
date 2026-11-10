import networkx as nx
from src.diccionario_inverso.modelos.centralidades import ModeloCercaniaReducido, ModeloGradoReducido

# 1. Cargar el vocabulario válido desde nodos.txt
def cargar_vocabulario(ruta="data/processed/nodos.txt"):
    with open(ruta, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())

vocabulario_valido = cargar_vocabulario()

# 2. Simular el preprocesamiento de David para 1 definición manual
definicion_cruda = "mamífero felino doméstico que maúlla y caza ratones"
# (Simulamos la lematización y limpieza que haría spaCy)
lemas_definicion = ["mamífero", "felino", "doméstico", "maullar", "cazar", "ratón"]

# Filtramos usando nodos.txt
lemas_utiles = [lema for lema in lemas_definicion if lema in vocabulario_valido]
print(f"Lemas útiles encontrados en nodos.txt: {lemas_utiles}")

# 3. Crear un grafo de juguete (Mock) con los esquemas de costo esperados
G_mock = nx.DiGraph()
# Conectamos los lemas útiles con palabras candidatas ("gato", "perro", etc.)
G_mock.add_edge("felino", "gato", costo_fa=10, costo_logp=0.5, p=0.9)
G_mock.add_edge("ratón", "gato", costo_fa=15, costo_logp=0.8, p=0.8)
G_mock.add_edge("doméstico", "gato", costo_fa=5, costo_logp=0.2, p=0.95)
G_mock.add_edge("doméstico", "perro", costo_fa=8, costo_logp=0.4, p=0.85)

# 4. Probar tu implementación
print("\n--- Ejecutando Modelo de Cercanía ---")
# Usamos G_mock inyectado por dependencia en lugar de cargar_grafo()
modelo_cercania = ModeloCercaniaReducido(G=G_mock, esquema_costo="costo_fa")
ranking_cercania = modelo_cercania.rankear(lemas=lemas_utiles, k=3)
print(f"Top candidatos (Cercanía 100-FA): {ranking_cercania}")

print("\n--- Ejecutando Modelo de Grado ---")
modelo_grado = ModeloGradoReducido(G=G_mock)
ranking_grado = modelo_grado.rankear(lemas=lemas_utiles, k=3)
print(f"Top candidatos (Grado p): {ranking_grado}")