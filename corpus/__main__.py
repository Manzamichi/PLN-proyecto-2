import argparse
import json
from pathlib import Path

from .fuentes import descargar, extraer


def main() -> int:
    parser = argparse.ArgumentParser(description="Bloque de David: corpus y preprocesamiento.")
    sub = parser.add_subparsers(dest="comando", required=True)
    descarga = sub.add_parser("descargar", help="Descargar la edición española de Kaikki.")
    descarga.add_argument("--salida", type=Path, default=Path("data/raw/es-extract.jsonl.gz"))
    extraccion = sub.add_parser("extraer", help="Crear banco fuente, todavía sin validar contra SWOW.")
    extraccion.add_argument("--entrada", type=Path, default=Path("data/raw/es-extract.jsonl.gz"))
    extraccion.add_argument("--salida", type=Path, default=Path("data/corpus_fuente.csv"))
    extraccion.add_argument("--max-por-concepto", type=int, default=3)
    preparacion = sub.add_parser("preparar", help="Filtrar y preprocesar con los nodos activos reales.")
    preparacion.add_argument("--entrada", type=Path, default=Path("data/corpus_fuente.csv"))
    preparacion.add_argument("--nodos", type=Path, required=True)
    preparacion.add_argument("--salida", type=Path, default=Path("data/processed"))
    preparacion.add_argument("--modelo", default="es_core_news_md")
    preparacion.add_argument("--minimo", type=int, default=300)
    args = parser.parse_args()
    try:
        if args.comando == "descargar":
            descargar(args.salida)
            print(f"Descarga guardada en {args.salida}")
        elif args.comando == "extraer":
            print(json.dumps(extraer(args.entrada, args.salida, args.max_por_concepto), ensure_ascii=False, indent=2))
        else:
            from .preparacion import preparar

            resumen = preparar(args.entrada, args.nodos, args.salida, args.modelo, args.minimo)
            print(json.dumps(resumen, ensure_ascii=False, indent=2))
            if not resumen["cumple_minimo"]:
                return 2
    except (ValueError, OSError) as error:
        parser.exit(1, f"Error: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
