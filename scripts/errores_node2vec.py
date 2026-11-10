"""Detalle por definición del modelo node2vec, con pistas para el análisis de errores.

Uso:
    python scripts/errores_node2vec.py
    python scripts/errores_node2vec.py --particion desarrollo

Evalúa data/processed/node2vec.kv con evaluar_modelo de diccionario_inverso.evaluacion
(las mismas métricas que los demás modelos) y agrega columnas que ayudan a clasificar
cada error. La pista es automática y solo orienta; la causa final se asigna a mano.

Salida:
    reports/node2vec_errores_<particion>.csv
"""

from __future__ import annotations

import argparse
import logging

import numpy as np
import spacy

from diccionario_inverso.config import DIR_PROCESADOS, DIR_REPORTES
from diccionario_inverso.corpus.normalizacion import normalizar
from diccionario_inverso.evaluacion import PARTICIONES, cargar_ejemplos, evaluar_modelo, leer_preprocesado
from diccionario_inverso.grafo import a_no_dirigido, cargar_grafo
from diccionario_inverso.modelos.node2vec import ModeloNode2Vec

logger = logging.getLogger("errores_node2vec")


def lemas_de_nodos(nodos: list[str]) -> dict[str, str]:
    """Lema de spaCy de cada nodo, para detectar variantes como abeja / abejas."""
    nlp = spacy.load("es_core_news_md", disable=["parser", "ner"])
    lemas = {}
    for nodo, doc in zip(nodos, nlp.pipe(nodos, batch_size=256)):
        lemas[nodo] = " ".join(normalizar(t.lemma_ or t.text) for t in doc)
    return lemas


def pista(fila, grado_alto: float) -> str:
    if fila["n_lemas"] == 0:
        return "sin lemas en el grafo"
    if fila["rango"] <= 5:
        return "acierto en top 5"
    if fila["variante_en_top5"]:
        return "variante morfológica en top 5"
    if fila["cobertura_lexica"] < 0.5:
        return "palabras fuera del vocabulario"
    if fila["mejor_rango_otra_acepcion"] <= 5:
        return "otra acepción sí se acierta"
    if fila["grado_top1"] >= grado_alto:
        return "top 1 muy conectado"
    return "revisar"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--particion", choices=PARTICIONES, default="prueba")
    parser.add_argument("--modelo", default=DIR_PROCESADOS / "node2vec.kv")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("gensim").setLevel(logging.WARNING)

    modelo = ModeloNode2Vec.cargar(args.modelo)
    detalle, resumen = evaluar_modelo(modelo, cargar_ejemplos(args.particion))
    logger.info("%s en %s: %s", modelo.nombre, args.particion, resumen)

    corpus = leer_preprocesado().set_index("id")
    detalle["definicion"] = detalle["id"].map(corpus["definicion"])
    detalle["lemas"] = detalle["id"].map(corpus["lemas_en_grafo"]).map(" | ".join)
    detalle["fuera_vocabulario"] = detalle["id"].map(corpus["fuera_vocabulario"]).map(" | ".join)
    detalle["rango"] = detalle["rango"].astype("float").fillna(np.inf)

    grado = dict(a_no_dirigido(cargar_grafo()).degree())
    detalle["grado_objetivo"] = detalle["concepto"].map(grado)
    detalle["top1"] = detalle["top5"].str.split("|").str[0]
    detalle["grado_top1"] = detalle["top1"].map(grado)

    lemas = lemas_de_nodos(list(grado))
    detalle["variante_en_top5"] = [
        next((c for c in top5.split("|") if c and c != concepto and lemas.get(c) == lemas.get(concepto)), "")
        for concepto, top5 in zip(detalle["concepto"], detalle["top5"])
    ]

    rangos_concepto = detalle.groupby("concepto")["rango"].apply(list)
    detalle["acepciones"] = detalle["concepto"].map(rangos_concepto.map(len))
    mejores = []
    for concepto, rango in zip(detalle["concepto"], detalle["rango"]):
        otros = list(rangos_concepto[concepto])
        otros.remove(rango)
        mejores.append(min(otros, default=np.inf))
    detalle["mejor_rango_otra_acepcion"] = mejores

    grado_alto = float(np.percentile(list(grado.values()), 90))
    detalle["pista"] = [pista(f, grado_alto) for _, f in detalle.iterrows()]
    logger.info("Grado del percentil 90 (top 1 muy conectado): %.0f", grado_alto)
    print(detalle[detalle["rango"] > 5]["pista"].value_counts().to_string())

    columnas = ["id", "concepto", "definicion", "lemas", "fuera_vocabulario", "cobertura_lexica", "rango", "top5",
                "grado_objetivo", "grado_top1", "variante_en_top5", "acepciones", "mejor_rango_otra_acepcion", "pista"]
    salida = DIR_REPORTES / f"node2vec_errores_{args.particion}.csv"
    detalle[columnas].replace(np.inf, np.nan).to_csv(salida, index=False, encoding="utf-8")
    logger.info("Detalle en %s", salida)


if __name__ == "__main__":
    main()
