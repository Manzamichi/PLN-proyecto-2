"""Convenciones compartidas; se conservan acentos y la letra ñ."""

import re
import unicodedata


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKC", texto).casefold().strip()
    return re.sub(r"[\s_]+", "_", texto)


def palabras(texto: str) -> list[str]:
    return re.findall(r"[^\W\d_]+", normalizar(texto), flags=re.UNICODE)


def contiene_secuencia(secuencia: list[str], buscada: list[str]) -> bool:
    return bool(buscada) and any(
        secuencia[i:i + len(buscada)] == buscada
        for i in range(len(secuencia) - len(buscada) + 1)
    )


def contiene_objetivo(definicion: str, concepto: str) -> bool:
    # No confundir sol con soldado; espacios y guiones bajos son equivalentes.
    return contiene_secuencia(palabras(definicion), palabras(concepto))

