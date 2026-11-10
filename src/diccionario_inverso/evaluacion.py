"""Partición desarrollo/prueba y evaluación de modelos de búsqueda léxica.

Métricas (por definición, se promedian sobre la partición):
    p@k               1 si el concepto objetivo está en las primeras k posiciones
    mrr               1 / rango del objetivo (0 si no aparece en el ranking)
    cobertura_modelo  fracción de definiciones cuyo ranking contiene al objetivo
    cobertura_lexica  promedio de la cobertura léxica calculada en el preprocesamiento

Uso desde otros bloques (p. ej. ajuste de node2vec en desarrollo):
    from diccionario_inverso.evaluacion import cargar_ejemplos, evaluar_modelo
    ejemplos = cargar_ejemplos("desarrollo")
    detalle, resumen = evaluar_modelo(mi_modelo, ejemplos)
"""

from __future__ import annotations

import json
import logging
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import networkx as nx
import numpy as np
import pandas as pd

from .config import RUTA_GRAFO, RUTA_PARTICION, RUTA_PREPROCESADO
from .grafo import cargar_grafo
from .modelos.base import ModeloBusqueda

logger = logging.getLogger(__name__)

PARTICIONES = ("desarrollo", "prueba")
KS = (1, 3, 5)


@dataclass(frozen=True)
class Ejemplo:
    id: str
    concepto: str
    lemas: tuple[str, ...]
    cobertura_lexica: float


# --------------------------------------------------------------------------- datos

def leer_preprocesado(ruta: Path = RUTA_PREPROCESADO) -> pd.DataFrame:
    if not ruta.is_file():
        raise FileNotFoundError(f"{ruta} no existe. Ejecuta el preprocesamiento del corpus.")
    with ruta.open(encoding="utf-8") as f:
        return pd.DataFrame([json.loads(linea) for linea in f if linea.strip()])


def particionar(conceptos: Iterable[str], fraccion_desarrollo: float = 0.3, semilla: int = 42) -> dict[str, str]:
    """Asigna cada concepto a una partición. Todas las definiciones de un mismo
    concepto quedan juntas, para que el ajuste en desarrollo no vea objetivos de prueba."""
    if not 0 < fraccion_desarrollo < 1:
        raise ValueError("fraccion_desarrollo debe estar en (0, 1)")
    unicos = sorted(set(conceptos))
    orden = np.random.default_rng(semilla).permutation(len(unicos))
    n_desarrollo = round(fraccion_desarrollo * len(unicos))
    return {
        unicos[i]: ("desarrollo" if posicion < n_desarrollo else "prueba")
        for posicion, i in enumerate(orden)
    }


def cargar_ejemplos(
    particion: str,
    *,
    ruta_preprocesado: Path = RUTA_PREPROCESADO,
    ruta_particion: Path = RUTA_PARTICION,
    muestra: int | None = None,
    semilla: int = 42,
) -> list[Ejemplo]:
    if particion not in PARTICIONES:
        raise ValueError(f"particion debe ser una de {PARTICIONES}")
    if not ruta_particion.is_file():
        raise FileNotFoundError(f"{ruta_particion} no existe. Ejecuta scripts/particionar.py")

    df = leer_preprocesado(ruta_preprocesado).drop(columns=["particion"], errors="ignore")
    asignacion = pd.read_csv(ruta_particion, dtype=str, keep_default_na=False)
    df = df.merge(asignacion[["id", "particion"]], on="id", how="left")
    sin_asignar = int(df["particion"].isna().sum())
    if sin_asignar:
        raise ValueError(
            f"{sin_asignar} definiciones sin partición: el corpus cambió. "
            "Vuelve a ejecutar scripts/particionar.py --forzar"
        )

    df = df[df["particion"] == particion]
    if muestra is not None and muestra < len(df):
        df = df.sample(n=muestra, random_state=semilla).sort_values("id")

    return [
        Ejemplo(
            id=fila.id,
            concepto=fila.concepto,
            lemas=tuple(dict.fromkeys(fila.lemas_en_grafo)),
            cobertura_lexica=float(fila.cobertura_lexica),
        )
        for fila in df.itertuples(index=False)
    ]


# ------------------------------------------------------------------------ métricas

def rango(ranking: Sequence[str], objetivo: str) -> int | None:
    """Posición (desde 1) del objetivo en el ranking, o None si no aparece."""
    for posicion, candidato in enumerate(ranking, start=1):
        if candidato == objetivo:
            return posicion
    return None


def resumir(rangos: Sequence[int | None], ks: Sequence[int] = KS) -> dict[str, float | int | None]:
    n = len(rangos)
    if n == 0:
        return {"n": 0}
    r = np.array([np.inf if x is None else x for x in rangos], dtype=float)
    encontrados = np.isfinite(r)
    resumen: dict[str, float | int | None] = {"n": n}
    for k in ks:
        resumen[f"p@{k}"] = float(np.mean(r <= k))
    resumen["mrr"] = float(np.mean(1.0 / r))
    resumen["cobertura_modelo"] = float(encontrados.mean())
    resumen["rango_mediano_encontrados"] = float(np.median(r[encontrados])) if encontrados.any() else None
    return resumen


# ---------------------------------------------------------------------- evaluación

_MODELO: ModeloBusqueda | None = None


def _iniciar_proceso(nombre: str, ruta_grafo: Path) -> None:
    from .modelos.registro import construir_modelo

    global _MODELO
    _MODELO = construir_modelo(nombre, cargar_grafo(ruta_grafo))


def _evaluar_ejemplo(ejemplo: Ejemplo) -> dict:
    assert _MODELO is not None
    inicio = time.perf_counter()
    ranking = _MODELO.rankear(list(ejemplo.lemas)) if ejemplo.lemas else []
    return {
        "id": ejemplo.id,
        "concepto": ejemplo.concepto,
        "n_lemas": len(ejemplo.lemas),
        "cobertura_lexica": ejemplo.cobertura_lexica,
        "rango": rango(ranking, ejemplo.concepto),
        "tam_ranking": len(ranking),
        "top5": "|".join(ranking[:5]),
        "segundos": time.perf_counter() - inicio,
    }


def _resultado(filas: list[dict], nombre: str, ks: Sequence[int]) -> tuple[pd.DataFrame, dict]:
    columnas = ["id", "concepto", "n_lemas", "cobertura_lexica", "rango", "tam_ranking", "top5", "segundos"]
    detalle = pd.DataFrame(filas, columns=columnas).astype({"rango": "Int64"})
    resumen = {"modelo": nombre, **resumir(
        [None if pd.isna(x) else int(x) for x in detalle["rango"]], ks
    )}
    resumen["cobertura_lexica"] = float(detalle["cobertura_lexica"].mean()) if len(detalle) else None
    resumen["definiciones_sin_lemas"] = int((detalle["n_lemas"] == 0).sum()) if len(detalle) else 0
    resumen["segundos_por_definicion"] = float(detalle["segundos"].mean()) if len(detalle) else None
    return detalle, resumen


def evaluar_modelo(
    modelo: ModeloBusqueda, ejemplos: Sequence[Ejemplo], ks: Sequence[int] = KS
) -> tuple[pd.DataFrame, dict]:
    """Evalúa una instancia ya construida, en el proceso actual."""
    global _MODELO
    _MODELO = modelo
    try:
        filas = [_evaluar_ejemplo(e) for e in ejemplos]
    finally:
        _MODELO = None
    return _resultado(filas, getattr(modelo, "nombre", type(modelo).__name__), ks)


def evaluar_registrado(
    nombre: str,
    ejemplos: Sequence[Ejemplo],
    *,
    procesos: int = 1,
    G: nx.DiGraph | None = None,
    ruta_grafo: Path = RUTA_GRAFO,
    ks: Sequence[int] = KS,
) -> tuple[pd.DataFrame, dict]:
    """Evalúa un modelo del registro, opcionalmente en paralelo (cada proceso carga el grafo)."""
    from .modelos.registro import construir_modelo

    if procesos <= 1:
        modelo = construir_modelo(nombre, G if G is not None else cargar_grafo(ruta_grafo))
        detalle, resumen = evaluar_modelo(modelo, ejemplos, ks)
        resumen["modelo"] = nombre
        return detalle, resumen

    filas: list[dict] = []
    paso = max(1, len(ejemplos) // 10)
    with ProcessPoolExecutor(procesos, initializer=_iniciar_proceso, initargs=(nombre, ruta_grafo)) as pool:
        for i, fila in enumerate(pool.map(_evaluar_ejemplo, ejemplos, chunksize=20), start=1):
            filas.append(fila)
            if i % paso == 0:
                logger.info("%s: %d/%d definiciones", nombre, i, len(ejemplos))
    return _resultado(filas, nombre, ks)


def objetivos_fuera_del_grafo(ejemplos: Iterable[Ejemplo], G: nx.DiGraph) -> list[str]:
    return sorted({e.concepto for e in ejemplos if e.concepto not in G})
