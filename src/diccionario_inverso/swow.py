"""Carga de SWOW-RP y cálculo de fuerzas de asociación.

Entrada: CSV de respuestas (p. ej. SWOW-RP.R70.<version>.csv) con columnas
cue, R1, R2, R3 (mayúsculas/minúsculas indistintas; columnas extra se ignoran).

Definiciones (por par cue -> respuesta, usando R1+R2+R3):
    frecuencia  número de veces que la respuesta aparece para el cue
    total_cue   respuestas válidas del cue (sin vacíos), denominador de p
    p           frecuencia / total_cue            (fuerza de asociación)
    fa          100 * p                           (fuerza en porcentaje)
    costo_fa    100 - fa                          (esquema 1)
    costo_logp  -log(p)                           (esquema 2)
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

COLUMNA_CUE = "cue"
COLUMNAS_RESPUESTA = ("R1", "R2", "R3")
MARCADORES_VACIOS = frozenset(
    {"", "na", "nan", "null", "none", "no more responses", "unknown word", "#missing"}
)
_SEPARADORES = (",", "\t", ";")


def detectar_separador(ruta: Path) -> str:
    """Detecta el separador a partir de la cabecera."""
    with ruta.open(encoding="utf-8", newline="") as f:
        cabecera = f.readline()
    conteos = {sep: cabecera.count(sep) for sep in _SEPARADORES}
    sep = max(conteos, key=conteos.__getitem__)
    if conteos[sep] == 0:
        raise ValueError(f"No se pudo detectar el separador de {ruta}")
    return sep


def normalizar(serie: pd.Series) -> pd.Series:
    """Minúsculas, NFC, sin espacios extremos y espacios internos colapsados.

    Se conservan acentos y ñ. Las expresiones multipalabra quedan separadas
    por un solo espacio (p. ej. "fin de semana").
    """
    return (
        serie.astype("string")
        .str.normalize("NFC")
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", " ", regex=True)
    )


def cargar_respuestas(ruta: Path) -> pd.DataFrame:
    """Lee el CSV de respuestas y devuelve las columnas cue, R1, R2, R3."""
    if not ruta.is_file():
        raise FileNotFoundError(ruta)
    sep = detectar_separador(ruta)
    df = pd.read_csv(
        ruta,
        sep=sep,
        dtype=str,
        keep_default_na=False,
        encoding="utf-8",
        on_bad_lines="warn",
    )
    mapa = {c.strip().lower(): c for c in df.columns}
    requeridas = [COLUMNA_CUE, *(c.lower() for c in COLUMNAS_RESPUESTA)]
    faltantes = [c for c in requeridas if c not in mapa]
    if faltantes:
        raise ValueError(f"Faltan columnas {faltantes} en {ruta}. Columnas: {list(df.columns)}")
    df = df[[mapa[c] for c in requeridas]]
    df.columns = [COLUMNA_CUE, *COLUMNAS_RESPUESTA]
    logger.info("Leídas %d filas (%d cues) de %s", len(df), df[COLUMNA_CUE].nunique(), ruta.name)
    return df


def a_formato_largo(df: pd.DataFrame) -> pd.DataFrame:
    """Convierte a una fila por respuesta válida: columnas cue, response."""
    largo = df.melt(
        id_vars=COLUMNA_CUE, value_vars=list(COLUMNAS_RESPUESTA), value_name="response"
    )
    largo = pd.DataFrame(
        {"cue": normalizar(largo[COLUMNA_CUE]), "response": normalizar(largo["response"])}
    )
    validas = (
        largo.notna().all(axis=1)
        & ~largo["cue"].isin(MARCADORES_VACIOS)
        & ~largo["response"].isin(MARCADORES_VACIOS)
    )
    descartadas = int((~validas).sum())
    logger.info("Respuestas válidas: %d (descartadas por vacías: %d)", int(validas.sum()), descartadas)
    return largo.loc[validas].reset_index(drop=True)


def calcular_fuerzas(largo: pd.DataFrame) -> pd.DataFrame:
    """Calcula frecuencia, p, fa y los dos costos por par (cue, response).

    El denominador de p incluye todas las respuestas válidas del cue; los
    bucles (respuesta == cue) se eliminan después de calcularlo.
    """
    total = largo.groupby("cue").size().rename("total_cue")
    sin_bucles = largo[largo["cue"] != largo["response"]]
    fuerzas = (
        sin_bucles.groupby(["cue", "response"]).size().rename("frecuencia").reset_index()
    )
    fuerzas = fuerzas.join(total, on="cue")
    fuerzas["p"] = fuerzas["frecuencia"] / fuerzas["total_cue"]
    fuerzas["fa"] = 100.0 * fuerzas["p"]
    fuerzas["costo_fa"] = 100.0 - fuerzas["fa"]
    fuerzas["costo_logp"] = -np.log(fuerzas["p"])
    fuerzas = fuerzas.astype({"cue": object, "response": object})
    return fuerzas.sort_values(
        ["cue", "frecuencia", "response"], ascending=[True, False, True], ignore_index=True
    )
