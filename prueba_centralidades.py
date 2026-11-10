from pathlib import Path
from diccionario_inverso.corpus.archivos import leer_nodos
from diccionario_inverso.corpus.preprocesamiento import Preprocesador
from diccionario_inverso.modelos.centralidades import ModeloCercaniaReducido, ModeloGradoReducido

# 1. Cargar el preprocesador de David con los nodos válidos
ruta_nodos = Path("data/processed/nodos.txt")
pre = Preprocesador(leer_nodos(ruta_nodos))

# 2. Definiciones de prueba manuales
definiciones = [
    "animal felino doméstico que caza ratones",
    "mueble de madera con cuatro patas para sentarse",
    "vehículo de dos ruedas que se mueve al pedalear"
]

# 3. Instanciar tus modelos (esto cargará el .pkl automáticamente si usaste la función cargar_grafo() en tu init)
print("Cargando grafo y modelos...")
modelo_cercania = ModeloCercaniaReducido(esquema_costo="costo_fa", radio_vecindad=1)
modelo_grado = ModeloGradoReducido(radio_vecindad=1)

# 4. Probar el pipeline completo
for definicion in definiciones:
    print(f"\nDefinición: '{definicion}'")
    
    # Preprocesamiento de David
    lemas = pre.lemas_para_modelo(definicion)
    print(f"Lemas limpios: {lemas}")
    
    if not lemas:
        print("No se encontraron lemas válidos en el grafo.")
        continue

    # Tus modelos de centralidad
    candidatos_cercania = modelo_cercania.rankear(lemas, k=5)
    candidatos_grado = modelo_grado.rankear(lemas, k=5)
    
    print(f"Top 5 Cercanía (100-FA): {candidatos_cercania}")
    print(f"Top 5 Grado (Similitud p): {candidatos_grado}")