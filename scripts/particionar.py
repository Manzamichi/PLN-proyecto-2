"""Asigna desarrollo/prueba por concepto objetivo (sin fuga entre particiones).

Uso:
    python scripts/particionar.py                       # 30 % desarrollo, semilla 42
    python scripts/particionar.py --fraccion-desarrollo 0.3 --semilla 42 --forzar

Salidas:
    data/processed/corpus/particion.csv   id, concepto, particion
    reports/particion.json                resumen de la partición

La partición no se regenera si ya existe (para no invalidar el ajuste de
hiperparámetros hecho en desarrollo); usa --forzar solo si el corpus cambió.
"""

from __future__ import annotations

import argparse
import hashlib
import logging

from diccionario_inverso.config import DIR_REPORTES, RUTA_PARTICION, RUTA_PREPROCESADO
from diccionario_inverso.evaluacion import PARTICIONES, leer_preprocesado, particionar
from diccionario_inverso.topologia import guardar_json


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fraccion-desarrollo", type=float, default=0.3)
    parser.add_argument("--semilla", type=int, default=42)
    parser.add_argument("--forzar", action="store_true", help="Sobrescribe una partición existente")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    if RUTA_PARTICION.exists() and not args.forzar:
        raise SystemExit(f"{RUTA_PARTICION} ya existe. Usa --forzar solo si el corpus cambió.")

    df = leer_preprocesado(RUTA_PREPROCESADO)
    if df["id"].duplicated().any():
        raise SystemExit("Hay ids duplicados en el corpus preprocesado.")

    asignacion = particionar(df["concepto"], args.fraccion_desarrollo, args.semilla)
    df["particion"] = df["concepto"].map(asignacion)
    solapados = df.groupby("concepto")["particion"].nunique().gt(1).sum()
    assert solapados == 0, "Un concepto quedó en ambas particiones"

    RUTA_PARTICION.parent.mkdir(parents=True, exist_ok=True)
    df[["id", "concepto", "particion"]].sort_values("id").to_csv(RUTA_PARTICION, index=False, encoding="utf-8")

    resumen = {
        "semilla": args.semilla,
        "fraccion_desarrollo_conceptos": args.fraccion_desarrollo,
        "unidad_de_particion": "concepto",
        "sha256_preprocesado": hashlib.sha256(RUTA_PREPROCESADO.read_bytes()).hexdigest(),
        "conceptos_en_ambas_particiones": int(solapados),
        "particiones": {
            p: {
                "conceptos": int(df.loc[df["particion"] == p, "concepto"].nunique()),
                "definiciones": int((df["particion"] == p).sum()),
                "definiciones_sin_lemas": int(
                    df.loc[df["particion"] == p, "lemas_en_grafo"].map(len).eq(0).sum()
                ),
                "cobertura_lexica_media": float(df.loc[df["particion"] == p, "cobertura_lexica"].mean()),
            }
            for p in PARTICIONES
        },
    }
    guardar_json(resumen, DIR_REPORTES / "particion.json")
    for p, datos in resumen["particiones"].items():
        print(f"{p:11s} conceptos={datos['conceptos']:>5}  definiciones={datos['definiciones']:>6}")


if __name__ == "__main__":
    main()
