"""Exporta las normas SWOW-RP en el formato de entrega del proyecto.

Columnas: estimulo, respuesta, frecuencia, tiempo_medio, fuerza, costo_fa,
costo_logp, en_grafo. `tiempo_medio` queda vacío porque SWOW-RP no publica
tiempos de respuesta. `en_grafo` indica si el par sobrevivió a los filtros del
grafo final (respuestas que son cue y mayor componente fuertemente conexa).

El archivo no se versiona: la licencia CC BY-NC-ND de SWOW-RP no permite
redistribuir obras derivadas. Se regenera con:
    python scripts/exportar_normas.py

Salida:
    data/processed/normas_swow_rp.csv
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from diccionario_inverso.config import DIR_PROCESADOS, DIR_RAW, RUTA_GRAFO
from diccionario_inverso.grafo import cargar_grafo
from diccionario_inverso.swow import a_formato_largo, calcular_fuerzas, cargar_respuestas

RUTA_NORMAS = DIR_PROCESADOS / "normas_swow_rp.csv"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--entrada", type=Path, help="CSV R70 (por defecto data/raw/*R70*.csv)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    entrada = args.entrada or max(DIR_RAW.rglob("*R70*.csv"), default=None)
    if entrada is None:
        raise SystemExit(f"No se encontró *R70*.csv en {DIR_RAW}. Usa --entrada <ruta>.")

    fuerzas = calcular_fuerzas(a_formato_largo(cargar_respuestas(entrada)))
    G = cargar_grafo(RUTA_GRAFO) if RUTA_GRAFO.is_file() else None

    normas = fuerzas.rename(columns={"cue": "estimulo", "response": "respuesta", "p": "fuerza"})
    normas["tiempo_medio"] = ""
    normas["en_grafo"] = (
        [G.has_edge(u, v) for u, v in zip(normas["estimulo"], normas["respuesta"])] if G is not None else ""
    )
    columnas = ["estimulo", "respuesta", "frecuencia", "tiempo_medio", "fuerza", "costo_fa", "costo_logp", "en_grafo"]
    RUTA_NORMAS.parent.mkdir(parents=True, exist_ok=True)
    normas[columnas].to_csv(RUTA_NORMAS, index=False, encoding="utf-8")
    print(f"{len(normas):,} pares estímulo–respuesta en {RUTA_NORMAS}")


if __name__ == "__main__":
    main()
