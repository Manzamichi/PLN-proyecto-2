"""Modelo híbrido con node2vec sobre el grafo SWOW-RP.

Uso:
    python scripts/modelo_node2vec.py explorar
    python scripts/modelo_node2vec.py explorar --configuraciones 1
    python scripts/modelo_node2vec.py consultar "insecto de rayas que produce miel"

explorar entrena las CONFIGURACIONES (1 = la de clase), compara suma y suma
ponderada por IDF en desarrollo, elige la mejor por MRR y solo esa se evalúa
en prueba.

Salidas:
    reports/node2vec_resultados.csv   métricas y segundos por configuración
    data/processed/node2vec.kv        vectores de la mejor configuración
    data/processed/node2vec.json      composición e IDF de la mejor configuración
"""

from __future__ import annotations

import argparse
import csv
import logging
import time
from pathlib import Path

from diccionario_inverso.config import DIR_PROCESADOS, DIR_REPORTES, RUTA_GRAFO, RUTA_PARTICION, RUTA_PREPROCESADO
from diccionario_inverso.corpus.normalizacion import normalizar
from diccionario_inverso.grafo import PESO_SIMILITUD, a_no_dirigido, cargar_grafo
from diccionario_inverso.modelos.node2vec import (
    CONFIGURACIONES,
    ModeloNode2Vec,
    calcular_idf,
    entrenar,
    evaluar,
    filtrar_aristas,
    generar_caminatas,
    leer_corpus,
    separar_particiones,
)

RUTA_MODELO = DIR_PROCESADOS / "node2vec.kv"
RUTA_RESULTADOS = DIR_REPORTES / "node2vec_resultados.csv"

logger = logging.getLogger("modelo_node2vec")


def glosas_compartidas(desarrollo: list[dict], prueba: list[dict]) -> int:
    """Definiciones de prueba cuya glosa normalizada también está en desarrollo."""
    glosas = {normalizar(f["definicion"]) for f in desarrollo}
    return sum(1 for f in prueba if normalizar(f["definicion"]) in glosas)


def explorar(args) -> None:
    grafo = cargar_grafo(args.grafo)
    if not args.dirigido:
        grafo = a_no_dirigido(grafo)
    tipo_grafo = "dirigido" if args.dirigido else "no_dirigido"
    if args.frecuencia_min > 1:
        grafo = filtrar_aristas(grafo, args.frecuencia_min)
    logger.info("Grafo %s: %d nodos, %d aristas (frecuencia >= %d)",
                tipo_grafo, grafo.number_of_nodes(), grafo.number_of_edges(), args.frecuencia_min)

    desarrollo, prueba, provisional = separar_particiones(leer_corpus(args.corpus, args.particion))
    particion = "provisional" if provisional else "asignada"
    logger.info("Definiciones: %d de desarrollo, %d de prueba (partición %s); "
                "%d glosas de prueba también aparecen en desarrollo",
                len(desarrollo), len(prueba), particion, glosas_compartidas(desarrollo, prueba))
    if provisional:
        logger.warning("El corpus no tiene particiones asignadas; se usa una partición PROVISIONAL por concepto.")
    idf, idf_por_defecto = calcular_idf([f["lemas"] for f in desarrollo])

    elegidas = [CONFIGURACIONES[i - 1] for i in args.configuraciones]
    resultados = []
    mejor = None
    caminatas_de = None
    for numero, config in zip(args.configuraciones, elegidas):
        clave = (config["walk_length"], config["num_walks"], config["p"], config["q"])
        segundos_caminatas = 0
        if clave != caminatas_de:
            inicio = time.time()
            caminatas = generar_caminatas(grafo, config["walk_length"], config["num_walks"], config["p"],
                                          config["q"], peso=args.peso, workers=args.workers)
            segundos_caminatas = round(time.time() - inicio)
            caminatas_de = clave
            logger.info("Configuración %d: caminatas en %d s", numero, segundos_caminatas)
        inicio = time.time()
        wv = entrenar(caminatas, config["dimensions"])
        segundos_entrenamiento = round(time.time() - inicio)
        logger.info("Configuración %d: entrenamiento en %d s", numero, segundos_entrenamiento)

        for modelo in (ModeloNode2Vec(wv), ModeloNode2Vec(wv, idf, idf_por_defecto)):
            fila = {"configuracion": numero, **config, "grafo": tipo_grafo, "peso": args.peso,
                    "frecuencia_min": args.frecuencia_min,
                    "composicion": modelo.nombre, "conjunto": "desarrollo", "particion": particion,
                    **evaluar(modelo, desarrollo),
                    "segundos_caminatas": segundos_caminatas, "segundos_entrenamiento": segundos_entrenamiento}
            resultados.append(fila)
            print(fila)
            if mejor is None or fila["MRR"] > mejor[0]["MRR"]:
                mejor = (fila, modelo)

    fila, modelo = mejor
    print("Mejor configuración en desarrollo:", fila)
    fila_prueba = {**fila, "conjunto": "prueba", **evaluar(modelo, prueba)}
    resultados.append(fila_prueba)
    print("Resultados en prueba:", fila_prueba)

    args.resultados.parent.mkdir(parents=True, exist_ok=True)
    with args.resultados.open("w", encoding="utf-8", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=list(resultados[0]))
        escritor.writeheader()
        escritor.writerows(resultados)
    modelo.guardar(args.modelo)
    logger.info("Resultados en %s; modelo en %s", args.resultados, args.modelo)


def consultar(args) -> None:
    from diccionario_inverso.corpus.preprocesamiento import Preprocesador

    modelo = ModeloNode2Vec.cargar(args.modelo)
    # Los nodos del grafo son exactamente el vocabulario de los vectores.
    pre = Preprocesador(modelo.wv.index_to_key)
    lemas = pre.lemas_para_modelo(args.definicion)
    print("Lemas en el grafo:", lemas)
    print(modelo.rankear(lemas, k=args.k))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="comando", required=True)

    ex = sub.add_parser("explorar")
    ex.add_argument("--grafo", type=Path, default=RUTA_GRAFO)
    ex.add_argument("--corpus", type=Path, default=RUTA_PREPROCESADO)
    ex.add_argument("--particion", type=Path, default=RUTA_PARTICION,
                    help="CSV id,concepto,particion; si falta se usa una partición provisional")
    ex.add_argument("--peso", default=PESO_SIMILITUD, help="Atributo de arista usado como peso")
    ex.add_argument("--dirigido", action="store_true",
                    help="Camina sobre el grafo dirigido cue -> respuesta en lugar de la copia no dirigida")
    ex.add_argument("--frecuencia-min", type=int, default=1,
                    help="Descarta aristas no dirigidas con menor frecuencia (1 = no filtra)")
    ex.add_argument("--configuraciones", type=int, nargs="+", default=list(range(1, len(CONFIGURACIONES) + 1)),
                    choices=range(1, len(CONFIGURACIONES) + 1), help="Números de CONFIGURACIONES a entrenar")
    ex.add_argument("--workers", type=int, default=1)
    ex.add_argument("--resultados", type=Path, default=RUTA_RESULTADOS)
    ex.add_argument("--modelo", type=Path, default=RUTA_MODELO)
    ex.set_defaults(funcion=explorar)

    co = sub.add_parser("consultar")
    co.add_argument("--modelo", type=Path, default=RUTA_MODELO)
    co.add_argument("--k", type=int, default=10)
    co.add_argument("definicion")
    co.set_defaults(funcion=consultar)

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("gensim").setLevel(logging.WARNING)
    args.funcion(args)


if __name__ == "__main__":
    main()
