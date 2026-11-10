"""Valida las fuerzas calculadas contra las oficiales de SWOW-RP (strength.SWOWRP.R123).

Uso:
    python scripts/validar_fuerzas.py
    python scripts/validar_fuerzas.py --respuestas data/raw/SWOWRP.R70.20220426.csv \
        --oficial data/raw/strength.SWOWRP.R123.20220426.csv

Salida:
    reports/validacion_fuerzas.json
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from diccionario_inverso.config import DIR_RAW, DIR_REPORTES
from diccionario_inverso.swow import (
    a_formato_largo,
    calcular_fuerzas,
    cargar_respuestas,
    detectar_separador,
    normalizar,
)
from diccionario_inverso.topologia import guardar_json

logger = logging.getLogger("validar_fuerzas")
TOLERANCIA = 1e-6


def localizar(patron: str, ruta: Path | None) -> Path:
    if ruta is not None:
        return ruta
    candidatos = sorted(DIR_RAW.rglob(patron))
    if not candidatos:
        raise SystemExit(f"No se encontró {patron} en {DIR_RAW}")
    return candidatos[-1]


def cargar_oficial(ruta: Path) -> pd.DataFrame:
    of = pd.read_csv(ruta, sep=detectar_separador(ruta), dtype={"cue": str, "response": str},
                     keep_default_na=False)
    faltantes = {"cue", "response", "R123", "N", "R123.Strength"} - set(of.columns)
    if faltantes:
        raise SystemExit(f"Faltan columnas {faltantes} en {ruta}")
    of["cue"] = normalizar(of["cue"]).astype(object)
    of["response"] = normalizar(of["response"]).astype(object)
    return of.rename(columns={"R123": "frecuencia_oficial", "N": "n_oficial", "R123.Strength": "p_oficial"})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--respuestas", type=Path)
    parser.add_argument("--oficial", type=Path)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    ruta_resp = localizar("*R70*.csv", args.respuestas)
    ruta_of = localizar("strength*R123*.csv", args.oficial)

    propias = calcular_fuerzas(a_formato_largo(cargar_respuestas(ruta_resp)))
    oficial = cargar_oficial(ruta_of)

    duplicados = int(oficial.duplicated(["cue", "response"]).sum())
    oficial = oficial.groupby(["cue", "response"], as_index=False).agg(
        frecuencia_oficial=("frecuencia_oficial", "sum"),
        n_oficial=("n_oficial", "first"),
        p_oficial=("p_oficial", "sum"),
    )
    oficial_sin_bucles = oficial[oficial["cue"] != oficial["response"]]

    union = propias.merge(oficial_sin_bucles, on=["cue", "response"], how="outer", indicator=True)
    comunes = union[union["_merge"] == "both"]
    dif_p = (comunes["p"] - comunes["p_oficial"]).abs().to_numpy()
    dif_f = (comunes["frecuencia"] - comunes["frecuencia_oficial"]).abs().to_numpy()
    dif_n = (comunes["total_cue"] - comunes["n_oficial"]).abs().to_numpy()

    resultado = {
        "archivo_respuestas": ruta_resp.name,
        "archivo_oficial": ruta_of.name,
        "pares_propios": len(propias),
        "pares_oficiales_sin_bucles": len(oficial_sin_bucles),
        "pares_oficiales_duplicados_tras_normalizar": duplicados,
        "pares_comunes": len(comunes),
        "solo_propios": int((union["_merge"] == "left_only").sum()),
        "solo_oficiales": int((union["_merge"] == "right_only").sum()),
        "frecuencia_identica_pct": float(100 * (dif_f == 0).mean()),
        "n_identico_pct": float(100 * (dif_n == 0).mean()),
        "p_identica_pct": float(100 * (dif_p <= TOLERANCIA).mean()),
        "p_dif_abs_max": float(dif_p.max()),
        "p_dif_abs_media": float(dif_p.mean()),
        "p_correlacion_pearson": float(np.corrcoef(comunes["p"], comunes["p_oficial"])[0, 1]),
        "ejemplos_discrepancia": (
            comunes.loc[dif_p > TOLERANCIA, ["cue", "response", "frecuencia", "frecuencia_oficial",
                                             "total_cue", "n_oficial", "p", "p_oficial"]]
            .head(10).to_dict(orient="records")
        ),
        "ejemplos_solo_propios": union.loc[union["_merge"] == "left_only", ["cue", "response", "frecuencia"]]
            .head(10).to_dict(orient="records"),
        "ejemplos_solo_oficiales": union.loc[union["_merge"] == "right_only", ["cue", "response", "frecuencia_oficial"]]
            .head(10).to_dict(orient="records"),
    }
    guardar_json(resultado, DIR_REPORTES / "validacion_fuerzas.json")
    for clave in ("pares_comunes", "solo_propios", "solo_oficiales", "frecuencia_identica_pct",
                  "n_identico_pct", "p_identica_pct", "p_dif_abs_max", "p_correlacion_pearson"):
        print(f"{clave:28s} {resultado[clave]}")


if __name__ == "__main__":
    main()