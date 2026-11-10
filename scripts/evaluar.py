"""Evalúa modelos registrados con p@1, p@3, p@5, MRR y cobertura.

Uso:
    python scripts/evaluar.py --listar
    python scripts/evaluar.py --particion desarrollo --muestra 300 --procesos 8
    python scripts/evaluar.py --particion prueba --modelos popularidad grado cercania_fa --procesos 8

Salidas (en reports/evaluacion/<particion>[_muestraN]/):
    <modelo>.json         métricas agregadas
    <modelo>_detalle.csv  rango del objetivo y top 5 por definición (análisis de errores)
    resumen.md            tabla comparativa de todos los modelos evaluados en esa carpeta
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from diccionario_inverso.config import DIR_EVALUACION, RUTA_GRAFO
from diccionario_inverso.evaluacion import (
    KS,
    PARTICIONES,
    cargar_ejemplos,
    evaluar_registrado,
    objetivos_fuera_del_grafo,
)
from diccionario_inverso.grafo import cargar_grafo
from diccionario_inverso.modelos.registro import modelos_disponibles
from diccionario_inverso.topologia import guardar_json

logger = logging.getLogger("evaluar")
COLUMNAS = ["n", *(f"p@{k}" for k in KS), "mrr", "cobertura_modelo", "cobertura_lexica",
            "rango_mediano_encontrados", "segundos_por_definicion"]


def escribir_tabla(directorio: Path) -> Path:
    resumenes = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(directorio.glob("*.json"))]
    resumenes.sort(key=lambda r: r.get("mrr", 0), reverse=True)

    def fmt(v) -> str:
        if v is None:
            return "—"
        return f"{v:,}" if isinstance(v, int) else f"{v:.4f}"

    lineas = [
        f"# Evaluación — {directorio.name}",
        "",
        "| modelo | " + " | ".join(COLUMNAS) + " |",
        "|---|" + "---|" * len(COLUMNAS),
        *(f"| {r['modelo']} | " + " | ".join(fmt(r.get(c)) for c in COLUMNAS) + " |" for r in resumenes),
        "",
        "p@k y mrr cuentan como fallo las definiciones sin lemas en el grafo o cuyo objetivo no aparece en el ranking.",
    ]
    ruta = directorio / "resumen.md"
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return ruta


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--listar", action="store_true", help="Muestra los modelos registrados")
    parser.add_argument("--modelos", nargs="+", help="Por defecto, todos los registrados")
    parser.add_argument("--particion", choices=PARTICIONES, default="desarrollo")
    parser.add_argument("--muestra", type=int, help="Evalúa una muestra aleatoria (pruebas rápidas)")
    parser.add_argument("--procesos", type=int, default=1)
    parser.add_argument("--semilla", type=int, default=42)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    if args.listar:
        print("\n".join(modelos_disponibles()))
        return

    modelos = args.modelos or modelos_disponibles()
    ejemplos = cargar_ejemplos(args.particion, muestra=args.muestra, semilla=args.semilla)
    G = cargar_grafo(RUTA_GRAFO)
    fuera = objetivos_fuera_del_grafo(ejemplos, G)
    if fuera:
        logger.warning("%d conceptos objetivo no son nodos del grafo (p. ej. %s)", len(fuera), fuera[:5])
    logger.info("%d definiciones de %s", len(ejemplos), args.particion)

    nombre_dir = args.particion + (f"_muestra{args.muestra}" if args.muestra else "")
    salida = DIR_EVALUACION / nombre_dir
    salida.mkdir(parents=True, exist_ok=True)

    for nombre in modelos:
        logger.info("Evaluando %s", nombre)
        detalle, resumen = evaluar_registrado(
            nombre, ejemplos, procesos=args.procesos, G=G if args.procesos <= 1 else None, ruta_grafo=RUTA_GRAFO
        )
        resumen.update(particion=args.particion, muestra=args.muestra, semilla=args.semilla)
        guardar_json(resumen, salida / f"{nombre}.json")
        detalle.to_csv(salida / f"{nombre}_detalle.csv", index=False, encoding="utf-8")
        logger.info("%s  p@1=%.4f  p@5=%.4f  mrr=%.4f", nombre, resumen["p@1"], resumen["p@5"], resumen["mrr"])

    print(escribir_tabla(salida).read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
