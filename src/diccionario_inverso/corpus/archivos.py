import csv
import hashlib
import json
from pathlib import Path

from .normalizacion import normalizar


def sha256(ruta: Path) -> str:
    digest = hashlib.sha256()
    with ruta.open("rb") as archivo:
        for bloque in iter(lambda: archivo.read(1024 * 1024), b""):
            digest.update(bloque)
    return digest.hexdigest()


def escribir_json(ruta: Path, objeto) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(objeto, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def escribir_csv(ruta: Path, filas, campos: list[str]) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8", newline="") as archivo:
        writer = csv.DictWriter(archivo, fieldnames=campos, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(filas)


def leer_nodos(ruta: Path) -> dict[str, str]:
    """Índice normalizado -> identificador ORIGINAL que recibirán los modelos.

    TXT: un nodo activo por línea. JSON: lista de cadenas. CSV: nodo[,grado].
    Si se informa grado, se excluyen los aislados. No se ejecutan archivos pickle.
    """
    if ruta.suffix.lower() == ".json":
        nodos = json.loads(ruta.read_text(encoding="utf-8-sig"))
        if not isinstance(nodos, list) or not all(isinstance(x, str) for x in nodos):
            raise ValueError("El JSON de nodos debe ser una lista de cadenas.")
    elif ruta.suffix.lower() == ".csv":
        with ruta.open(encoding="utf-8-sig", newline="") as archivo:
            reader = csv.DictReader(archivo)
            if "nodo" not in (reader.fieldnames or []):
                raise ValueError("El CSV de nodos necesita la columna nodo (grado es opcional).")
            nodos = []
            for fila in reader:
                if "grado" in fila:
                    grado = float(fila["grado"])
                    if not grado >= 0:
                        raise ValueError("El grado debe ser un número no negativo.")
                    if grado == 0:
                        continue
                nodos.append(fila["nodo"])
    else:
        nodos = ruta.read_text(encoding="utf-8-sig").splitlines()
    indice = {}
    for nodo in nodos:
        nodo = nodo.strip()
        clave = normalizar(nodo)
        if not clave:
            continue
        if clave in indice and indice[clave] != nodo:
            raise ValueError(f"Nodos ambiguos tras normalizar: {indice[clave]!r}, {nodo!r}.")
        indice[clave] = nodo
    if not indice:
        raise ValueError("La lista no contiene nodos activos.")
    return indice
