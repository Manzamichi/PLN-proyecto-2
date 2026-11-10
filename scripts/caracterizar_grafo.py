"""Caracterización topológica del grafo guardado.

Uso:
    python scripts/caracterizar_grafo.py                    # clustering aproximado
    python scripts/caracterizar_grafo.py --clustering-exacto

Salidas:
    reports/caracterizacion.json
    reports/caracterizacion.md
    reports/figuras/distribucion_grado.png
"""

from __future__ import annotations

import argparse
import logging

from diccionario_inverso.config import DIR_FIGURAS, DIR_REPORTES, RUTA_GRAFO
from diccionario_inverso.grafo import cargar_grafo
from diccionario_inverso.topologia import (
    caracterizar,
    graficar_distribucion_grado,
    guardar_json,
    guardar_markdown,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--clustering-exacto", action="store_true")
    parser.add_argument("--muestras", type=int, default=20_000)
    parser.add_argument("--semilla", type=int, default=42)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    G = cargar_grafo(RUTA_GRAFO)
    resultado = caracterizar(
        G, clustering_exacto=args.clustering_exacto, muestras_clustering=args.muestras, semilla=args.semilla
    )
    guardar_json(resultado, DIR_REPORTES / "caracterizacion.json")
    guardar_markdown({"SWOW-RP": resultado}, DIR_REPORTES / "caracterizacion.md")
    graficar_distribucion_grado(G, DIR_FIGURAS / "distribucion_grado.png")
    print((DIR_REPORTES / "caracterizacion.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
