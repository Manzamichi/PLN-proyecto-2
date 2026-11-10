"""Rutas del proyecto. Se pueden sobrescribir con la variable de entorno PLN_DATA_DIR."""

from __future__ import annotations

import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DIR_DATOS = Path(os.environ.get("PLN_DATA_DIR", RAIZ / "data"))
DIR_RAW = DIR_DATOS / "raw"
DIR_PROCESADOS = DIR_DATOS / "processed"
DIR_REPORTES = RAIZ / "reports"
DIR_FIGURAS = DIR_REPORTES / "figuras"

RUTA_GRAFO = DIR_PROCESADOS / "grafo_swow_rp.pkl"
RUTA_ARISTAS = DIR_PROCESADOS / "aristas_swow_rp.csv"
RUTA_NODOS = DIR_PROCESADOS / "nodos.txt"
