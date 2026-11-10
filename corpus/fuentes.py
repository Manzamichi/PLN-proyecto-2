"""Descarga y extracción reproducible de la edición ESPAÑOLA de Wikcionario."""

import gzip
import hashlib
import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

from .archivos import escribir_csv, escribir_json, sha256
from .normalizacion import contiene_objetivo, normalizar, palabras

URL_KAIKKI = "https://kaikki.org/dictionary/downloads/es/es-extract.jsonl.gz"
CAMPOS_FUENTE = ["id", "concepto", "definicion", "fuente", "particion", "pos", "acepcion", "licencia"]


def descargar(destino: Path, url: str = URL_KAIKKI) -> None:
    if destino.exists():
        raise ValueError(f"Ya existe {destino}; reutilízalo o elige otra ruta.")
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporal = destino.with_suffix(destino.suffix + ".part")
    peticion = Request(url, headers={"User-Agent": "PLN-proyecto-2/1.0 (academic corpus)"})
    with urlopen(peticion, timeout=60) as respuesta, temporal.open("wb") as archivo:
        shutil.copyfileobj(respuesta, archivo)
    temporal.replace(destino)
    escribir_json(destino.with_suffix(destino.suffix + ".json"), {
        "url": url, "descarga_utc": datetime.now(timezone.utc).isoformat(),
        "sha256": sha256(destino), "bytes": destino.stat().st_size,
    })


def extraer(origen: Path, destino: Path, max_por_concepto: int = 3) -> dict:
    """Guarda glosas reales sin reescribirlas. No valida pertenencia a SWOW.

    Conserva todas las palabras elegibles (sin muestreo alfabético). El límite por
    concepto evita que las voces polisémicas dominen el banco fuente.
    """
    if max_por_concepto < 1:
        raise ValueError("max_por_concepto debe ser positivo.")
    contadores = Counter()
    por_concepto = Counter()
    vistos = set()
    filas = []
    menciones = []
    abrir = gzip.open if origen.suffix == ".gz" else open
    with abrir(origen, "rt", encoding="utf-8") as archivo:
        for linea in archivo:
            entrada = json.loads(linea)
            contadores["entradas_leidas"] += 1
            if entrada.get("lang_code") != "es" or entrada.get("pos") not in {"noun", "verb", "adj"}:
                continue
            # Las categorías españolas distinguen lemas de formas flexivas.
            if "ES:Lemas" not in entrada.get("categories", []):
                contadores["entradas_sin_marca_lema"] += 1
                continue
            concepto = normalizar(entrada.get("word", ""))
            if not concepto or not all(p.isalpha() for p in concepto.split("_")):
                continue
            for numero, sentido in enumerate(entrada.get("senses", []), 1):
                if sentido.get("form_of") or "form-of" in sentido.get("tags", []):
                    contadores["formas_flexivas"] += 1
                    continue
                glosas = sentido.get("glosses", [])
                if not glosas:
                    continue
                # Si hay glosas jerárquicas, usar solo la más específica.
                definicion = " ".join(glosas[-1].split())
                contadores["glosas_consideradas"] += 1
                if not 4 <= len(palabras(definicion)) <= 100:
                    contadores["longitud_fuera_de_rango"] += 1
                    continue
                if contiene_objetivo(definicion, concepto):
                    contadores["mencion_literal_objetivo"] += 1
                    menciones.append({
                        "concepto": concepto, "definicion": definicion,
                        "fuente": "https://es.wiktionary.org/wiki/" + quote(entrada["word"].replace(" ", "_"), safe=""),
                        "motivo": "mencion_literal_objetivo", "licencia": "CC-BY-SA-4.0",
                    })
                    continue
                clave = (concepto, normalizar(definicion))
                if clave in vistos:
                    contadores["duplicadas"] += 1
                    continue
                vistos.add(clave)
                if por_concepto[concepto] >= max_por_concepto:
                    contadores["limite_por_concepto"] += 1
                    continue
                por_concepto[concepto] += 1
                identificador = hashlib.sha256((concepto + "\n" + definicion).encode()).hexdigest()[:20]
                filas.append({
                    "id": identificador, "concepto": concepto, "definicion": definicion,
                    "fuente": "https://es.wiktionary.org/wiki/" + quote(entrada["word"].replace(" ", "_"), safe=""),
                    "particion": "pendiente", "pos": entrada["pos"],
                    "acepcion": sentido.get("sense_index", str(numero)), "licencia": "CC-BY-SA-4.0",
                })
    filas.sort(key=lambda fila: (fila["concepto"], fila["id"]))
    escribir_csv(destino, filas, CAMPOS_FUENTE)
    ruta_menciones = destino.with_name(destino.stem + "_menciones.csv")
    escribir_csv(ruta_menciones, menciones, ["concepto", "definicion", "fuente", "motivo", "licencia"])
    manifiesto = {
        "estado": "FUENTE_SIN_VALIDAR_CONTRA_GRAFO", "url_descarga": URL_KAIKKI,
        "edicion": "eswiktionary", "idioma_palabra": "es", "idioma_definicion": "es",
        "sha256_origen": sha256(origen), "sha256_csv": sha256(destino),
        "definiciones": len(filas), "conceptos": len(por_concepto),
        "max_por_concepto": max_por_concepto, "conteos": dict(contadores),
        "archivo_menciones_descartadas": ruta_menciones.name,
        "nota": "No constituye todavía el corpus de evaluación SWOW-RP. No hay definiciones generadas por IA.",
    }
    escribir_json(destino.with_suffix(".json"), manifiesto)
    return manifiesto

