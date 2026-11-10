"""Caracterización topológica del grafo y generación de reportes."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import networkx as nx
import numpy as np

logger = logging.getLogger(__name__)


def _estadisticos(valores: np.ndarray) -> dict[str, float]:
    if valores.size == 0:
        return {}
    return {
        "media": float(valores.mean()),
        "mediana": float(np.median(valores)),
        "desv_est": float(valores.std()),
        "min": float(valores.min()),
        "max": float(valores.max()),
    }


def caracterizar(
    G: nx.DiGraph,
    *,
    clustering_exacto: bool = False,
    muestras_clustering: int = 20_000,
    semilla: int = 42,
) -> dict[str, Any]:
    """Nodos, aristas, grados, componentes, reciprocidad, clustering y pesos.

    El clustering se calcula sobre la proyección no dirigida sin pesos. Por
    defecto se aproxima por muestreo (nx.approximation.average_clustering);
    con clustering_exacto=True se usa nx.average_clustering.
    """
    n, m = G.number_of_nodes(), G.number_of_edges()
    grado_salida = np.fromiter((d for _, d in G.out_degree()), dtype=float, count=n)
    grado_entrada = np.fromiter((d for _, d in G.in_degree()), dtype=float, count=n)

    U = nx.Graph()
    U.add_nodes_from(G)
    U.add_edges_from(G.edges())
    grado_no_dirigido = np.fromiter((d for _, d in U.degree()), dtype=float, count=n)

    debiles = sorted((len(c) for c in nx.weakly_connected_components(G)), reverse=True)
    fuertes = sorted((len(c) for c in nx.strongly_connected_components(G)), reverse=True)

    logger.info("Calculando clustering (%s)...", "exacto" if clustering_exacto else "aproximado")
    if clustering_exacto:
        clustering = nx.average_clustering(U)
    else:
        clustering = nx.approximation.average_clustering(U, trials=muestras_clustering, seed=semilla)

    atributos = {
        a: np.fromiter((d[a] for _, _, d in G.edges(data=True)), dtype=float, count=m)
        for a in ("p", "costo_fa", "costo_logp")
    }

    return {
        "nodos": n,
        "aristas_dirigidas": m,
        "aristas_no_dirigidas": U.number_of_edges(),
        "densidad": nx.density(G),
        "reciprocidad": nx.reciprocity(G) if m else 0.0,
        "grado_medio_salida": float(grado_salida.mean()),
        "grado_medio_entrada": float(grado_entrada.mean()),
        "grado_medio_no_dirigido": float(grado_no_dirigido.mean()),
        "grado_salida": _estadisticos(grado_salida),
        "grado_entrada": _estadisticos(grado_entrada),
        "componentes_debiles": len(debiles),
        "mayor_componente_debil": debiles[0] if debiles else 0,
        "componentes_fuertes": len(fuertes),
        "mayor_componente_fuerte": fuertes[0] if fuertes else 0,
        "nodos_aislados": nx.number_of_isolates(G),
        "clustering_promedio": float(clustering),
        "clustering_metodo": "exacto" if clustering_exacto else f"aproximado ({muestras_clustering} muestras)",
        "pesos": {a: _estadisticos(v) for a, v in atributos.items()},
        "parametros_construccion": dict(G.graph),
    }


def guardar_json(datos: dict[str, Any], ruta: Path) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def guardar_markdown(secciones: dict[str, dict[str, Any]], ruta: Path) -> None:
    """Tabla comparativa de métricas escalares (una columna por grafo)."""
    nombres = list(secciones)
    claves = [
        k for k, v in secciones[nombres[0]].items() if isinstance(v, (int, float)) and not isinstance(v, bool)
    ]

    def fmt(v: Any) -> str:
        if isinstance(v, float):
            return f"{v:.4f}"
        if isinstance(v, int):
            return f"{v:,}"
        return "—"

    lineas = [
        "# Caracterización topológica — SWOW-RP",
        "",
        "| Métrica | " + " | ".join(nombres) + " |",
        "|---|" + "---|" * len(nombres),
    ]
    lineas += [f"| {k} | " + " | ".join(fmt(secciones[n].get(k)) for n in nombres) + " |" for k in claves]
    lineas += ["", "Clustering: " + "; ".join(f"{n}: {secciones[n]['clustering_metodo']}" for n in nombres)]
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")


def graficar_distribucion_grado(G: nx.DiGraph, ruta: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ejes = plt.subplots(1, 2, figsize=(10, 4))
    for eje, (titulo, grados) in zip(
        ejes, (("Grado de entrada", G.in_degree()), ("Grado de salida", G.out_degree()))
    ):
        valores = np.array([d for _, d in grados if d > 0])
        k, cuenta = np.unique(valores, return_counts=True)
        eje.loglog(k, cuenta / cuenta.sum(), "o", markersize=3, alpha=0.7)
        eje.set(title=titulo, xlabel="k", ylabel="P(k)")
        eje.grid(True, which="both", alpha=0.3)
    fig.tight_layout()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(ruta, dpi=150)
    plt.close(fig)
