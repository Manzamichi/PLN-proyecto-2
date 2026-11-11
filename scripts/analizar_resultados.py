"""Análisis comparativo de los resultados de prueba para la discusión.

Lee los CSV de detalle de reports/evaluacion/prueba/ y el corpus, y calcula:
    - pruebas de McNemar (aciertos en p@1 y p@5) entre pares de modelos
    - comparación por definición entre la mejor centralidad y node2vec,
      desglosada por categoría gramatical y número de lemas
    - p@5 del oráculo que elige, por definición, el mejor de ambos modelos

Uso:
    python scripts/analizar_resultados.py

Salida:
    reports/analisis_resultados.json
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from diccionario_inverso.config import DIR_CORPUS, DIR_EVALUACION, DIR_REPORTES
from diccionario_inverso.topologia import guardar_json

DIR_PRUEBA = DIR_EVALUACION / "prueba"
CENTRALIDAD = "grado"
EMBEDDINGS = "node2vec_suma_idf"
COMPARACIONES = [
    ("cercania_fa", "cercania_logp"),
    ("intermediacion_fa", "intermediacion_logp"),
    ("cercania_fa", "intermediacion_fa"),
    ("cercania_logp", "intermediacion_logp"),
    ("node2vec_suma", "node2vec_suma_idf"),
    (CENTRALIDAD, EMBEDDINGS),
]


def cargar_rangos(modelo: str) -> pd.Series:
    df = pd.read_csv(DIR_PRUEBA / f"{modelo}_detalle.csv", dtype={"id": str})
    return df.set_index("id")["rango"].astype("float")  # NaN = objetivo ausente del ranking


def mcnemar(aciertos_a: pd.Series, aciertos_b: pd.Series) -> dict:
    """Prueba de McNemar con corrección de continuidad sobre aciertos pareados."""
    b = int((aciertos_a & ~aciertos_b).sum())
    c = int((~aciertos_a & aciertos_b).sum())
    if b + c == 0:
        return {"solo_a": b, "solo_b": c, "p_valor": 1.0}
    chi2 = (abs(b - c) - 1) ** 2 / (b + c)
    return {"solo_a": b, "solo_b": c, "p_valor": math.erfc(math.sqrt(chi2 / 2))}


def acierto(rangos: pd.Series, k: int) -> pd.Series:
    return rangos.le(k).fillna(False)


def rr(rangos: pd.Series) -> pd.Series:
    return (1.0 / rangos).fillna(0.0)


def main() -> None:
    modelos = sorted({m for par in COMPARACIONES for m in par})
    rangos = pd.DataFrame({m: cargar_rangos(m) for m in modelos})

    pruebas = {}
    for a, b in COMPARACIONES:
        pruebas[f"{a} vs {b}"] = {
            f"p@{k}": {"a": float(acierto(rangos[a], k).mean()), "b": float(acierto(rangos[b], k).mean()),
                       **mcnemar(acierto(rangos[a], k), acierto(rangos[b], k))}
            for k in (1, 5)
        }

    corpus = pd.read_csv(DIR_CORPUS / "corpus.csv", dtype=str, keep_default_na=False).set_index("id")
    detalle = pd.read_csv(DIR_PRUEBA / f"{EMBEDDINGS}_detalle.csv", dtype={"id": str}).set_index("id")
    comp = pd.DataFrame({
        "rr_c": rr(rangos[CENTRALIDAD]), "rr_e": rr(rangos[EMBEDDINGS]),
        "top5_c": acierto(rangos[CENTRALIDAD], 5), "top5_e": acierto(rangos[EMBEDDINGS], 5),
        "pos": corpus["pos"].reindex(rangos.index),
        "n_lemas": detalle["n_lemas"].reindex(rangos.index),
    })
    comp["ganador"] = np.select(
        [comp.rr_c > comp.rr_e, comp.rr_c < comp.rr_e], [CENTRALIDAD, EMBEDDINGS], "empate"
    )
    comp["grupo_lemas"] = pd.cut(comp.n_lemas, [-1, 0, 2, 5, 9, np.inf], labels=["0", "1-2", "3-5", "6-9", "10+"])

    def desglose(columna: str) -> dict:
        tabla = {}
        for valor, g in comp.groupby(columna, observed=True):
            tabla[str(valor)] = {
                "definiciones": len(g),
                f"p@5_{CENTRALIDAD}": float(g.top5_c.mean()),
                f"p@5_{EMBEDDINGS}": float(g.top5_e.mean()),
                f"mrr_{CENTRALIDAD}": float(g.rr_c.mean()),
                f"mrr_{EMBEDDINGS}": float(g.rr_e.mean()),
                f"gana_{CENTRALIDAD}_pct": float(100 * (g.ganador == CENTRALIDAD).mean()),
                f"gana_{EMBEDDINGS}_pct": float(100 * (g.ganador == EMBEDDINGS).mean()),
            }
        return tabla

    resultado = {
        "pruebas_mcnemar": pruebas,
        "centralidad_vs_embeddings": {
            "modelos": [CENTRALIDAD, EMBEDDINGS],
            "ganador_pct": {k: float(100 * v) for k, v in comp.ganador.value_counts(normalize=True).items()},
            "aciertos_top5": {
                "solo_centralidad": int((comp.top5_c & ~comp.top5_e).sum()),
                "solo_embeddings": int((~comp.top5_c & comp.top5_e).sum()),
                "ambos": int((comp.top5_c & comp.top5_e).sum()),
            },
            "p@5_oraculo": float((comp.top5_c | comp.top5_e).mean()),
            "por_categoria": desglose("pos"),
            "por_numero_de_lemas": desglose("grupo_lemas"),
        },
    }
    guardar_json(resultado, DIR_REPORTES / "analisis_resultados.json")

    for nombre, datos in pruebas.items():
        print(nombre, {k: (round(v["a"], 4), round(v["b"], 4), f"p={v['p_valor']:.3g}") for k, v in datos.items()})
    cve = resultado["centralidad_vs_embeddings"]
    print("ganador %:", {k: round(v, 1) for k, v in cve["ganador_pct"].items()})
    print("top5:", cve["aciertos_top5"], "oráculo p@5:", round(cve["p@5_oraculo"], 4))
    for clave in ("por_categoria", "por_numero_de_lemas"):
        print(clave)
        for valor, fila in cve[clave].items():
            print("  ", valor, {k: round(v, 3) if isinstance(v, float) else v for k, v in fila.items()})


if __name__ == "__main__":
    main()
