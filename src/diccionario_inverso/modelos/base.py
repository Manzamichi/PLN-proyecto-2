"""Interfaz común acordada para todos los modelos (centralidades y node2vec).

El script de evaluación solo depende de este contrato.
"""

from __future__ import annotations

from typing import Protocol, Sequence, runtime_checkable


@runtime_checkable
class ModeloBusqueda(Protocol):
    nombre: str

    def rankear(self, lemas: Sequence[str], k: int | None = None) -> list[str]:
        """Recibe los lemas útiles de una definición (ya preprocesados y presentes
        en el grafo) y devuelve candidatos ordenados de mejor a peor.
        No debe incluir los lemas de entrada. k=None devuelve el ranking completo.
        """
        ...
