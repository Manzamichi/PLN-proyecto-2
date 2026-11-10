"""Construye el grafo SWOW-RP con las dos ponderaciones y lo guarda.

Uso:
    python scripts/construir_grafo.py
    python scripts/construir_grafo.py --entrada data/raw/SWOW-RP.R70.26-04-2022.csv --min-frecuencia 2

Salidas:
    data/processed/grafo_swow_rp.pkl   grafo final (DiGraph)
    data/processed/aristas_swow_rp.csv aristas con frecuencia, p, costo_fa, costo_logp
    data/processed/nodos.txt           lista de nodos (para el bloque de corpus)
    reports/filtrado.json              resumen del pipeline de construcción
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import networkx as nx

from diccionario_inverso.config import DIR_RAW, DIR_REPORTES, RUTA_ARISTAS, RUTA_GRAFO, RUTA_NODOS
from diccionario_inverso.grafo import (
    OpcionesGrafo,
    construir_grafo,
    exportar_aristas,
    exportar_nodos,
    guardar_grafo,
    mayor_componente_fuerte,
)
from diccionario_inverso.swow import a_formato_largo, calcular_fuerzas, cargar_respuestas
from diccionario_inverso.topologia import guardar_json

logger = logging.getLogger("construir_grafo")


def localizar_entrada(ruta: Path | None) -> Path:
    if ruta is not None:
        return ruta
    candidatos = sorted(DIR_RAW.rglob("*R70*.csv"))
    if not candidatos:
        raise SystemExit(f"No se encontró *R70*.csv en {DIR_RAW}. Usa --entrada <ruta>.")
    if len(candidatos) > 1:
        logger.warning("Varios archivos R70; se usa %s", candidatos[-1])
    return candidatos[-1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--entrada", type=Path, help="CSV con columnas cue,R1,R2,R3")
    parser.add_argument("--min-frecuencia", type=int, default=1)
    parser.add_argument("--todas-las-respuestas", action="store_true",
                        help="No restringir respuestas a cues")
    parser.add_argument("--sin-filtro-cfc", action="store_true",
                        help="No reducir a la mayor componente fuertemente conexa")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    entrada = localizar_entrada(args.entrada)
    largo = a_formato_largo(cargar_respuestas(entrada))
    fuerzas = calcular_fuerzas(largo)

    opciones = OpcionesGrafo(min_frecuencia=args.min_frecuencia, solo_cues=not args.todas_las_respuestas)
    completo = construir_grafo(fuerzas, opciones)
    final = completo if args.sin_filtro_cfc else mayor_componente_fuerte(completo)
    final.graph["archivo_fuente"] = entrada.name

    guardar_grafo(final, RUTA_GRAFO)
    exportar_aristas(final, RUTA_ARISTAS)
    exportar_nodos(final, RUTA_NODOS)

    guardar_json(
        {
            "archivo_fuente": entrada.name,
            "opciones": vars(args) | {"entrada": str(entrada)},
            "respuestas_validas": len(largo),
            "cues": int(largo["cue"].nunique()),
            "pares_cue_respuesta": len(fuerzas),
            "grafo_completo": {
                "nodos": completo.number_of_nodes(),
                "aristas": completo.number_of_edges(),
                "componentes_debiles": nx.number_weakly_connected_components(completo),
                "componentes_fuertes": nx.number_strongly_connected_components(completo),
            },
            "grafo_final": {"nodos": final.number_of_nodes(), "aristas": final.number_of_edges()},
            "nodos_descartados": completo.number_of_nodes() - final.number_of_nodes(),
        },
        DIR_REPORTES / "filtrado.json",
    )
    logger.info("Listo. Siguiente paso: python scripts/caracterizar_grafo.py")


if __name__ == "__main__":
    main()
