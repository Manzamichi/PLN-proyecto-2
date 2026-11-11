"""Copia la partición de particion.csv al conjunto de evaluación versionado.

Actualiza la columna `particion` de corpus.csv y preprocesado.jsonl, y el conteo
de particiones de cobertura.json. Volver a ejecutarlo si se regenera el corpus
(el comando `preparar` de corpus reinicia la columna a "pendiente").

Uso:
    python scripts/sincronizar_particion.py
"""

from __future__ import annotations

import csv
import json
from collections import Counter

from diccionario_inverso.config import DIR_CORPUS, RUTA_PARTICION, RUTA_PREPROCESADO

RUTA_CORPUS = DIR_CORPUS / "corpus.csv"
RUTA_COBERTURA = DIR_CORPUS / "cobertura.json"


def leer_asignacion() -> dict[str, str]:
    with RUTA_PARTICION.open(encoding="utf-8", newline="") as f:
        return {fila["id"]: fila["particion"] for fila in csv.DictReader(f)}


def main() -> None:
    asignacion = leer_asignacion()

    with RUTA_CORPUS.open(encoding="utf-8", newline="") as f:
        lector = csv.DictReader(f)
        campos, filas = lector.fieldnames, list(lector)
    faltantes = [fila["id"] for fila in filas if fila["id"] not in asignacion]
    if faltantes:
        raise SystemExit(f"{len(faltantes)} ids del corpus sin partición. Ejecuta scripts/particionar.py --forzar")
    for fila in filas:
        fila["particion"] = asignacion[fila["id"]]
    with RUTA_CORPUS.open("w", encoding="utf-8", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=campos, lineterminator="\n")
        escritor.writeheader()
        escritor.writerows(filas)

    lineas = []
    with RUTA_PREPROCESADO.open(encoding="utf-8") as f:
        for linea in f:
            if linea.strip():
                registro = json.loads(linea)
                registro["particion"] = asignacion[registro["id"]]
                lineas.append(json.dumps(registro, ensure_ascii=False))
    RUTA_PREPROCESADO.write_text("\n".join(lineas) + "\n", encoding="utf-8")

    conteo = dict(sorted(Counter(fila["particion"] for fila in filas).items()))
    if RUTA_COBERTURA.is_file():
        cobertura = json.loads(RUTA_COBERTURA.read_text(encoding="utf-8"))
        cobertura["particiones"] = conteo
        RUTA_COBERTURA.write_text(json.dumps(cobertura, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Partición sincronizada en {len(filas)} definiciones: {conteo}")


if __name__ == "__main__":
    main()
