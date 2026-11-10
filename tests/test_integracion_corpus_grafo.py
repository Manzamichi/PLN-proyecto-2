"""Contrato entre la exportación del grafo y el preprocesamiento del corpus."""

import json
import subprocess
import sys

import pandas as pd

from diccionario_inverso.corpus.archivos import escribir_csv, leer_nodos
from diccionario_inverso.corpus.preparacion import preparar
from diccionario_inverso.grafo import construir_grafo, exportar_nodos, mayor_componente_fuerte
from diccionario_inverso.swow import a_formato_largo, calcular_fuerzas


def test_cli_corpus_instalado_fuera_de_la_raiz(tmp_path):
    resultado = subprocess.run(
        [sys.executable, "-m", "diccionario_inverso.corpus", "--help"],
        cwd=tmp_path, capture_output=True, text=True,
    )
    assert resultado.returncode == 0, resultado.stderr
    assert "preparar" in resultado.stdout


def test_corpus_con_nodos_exportados_y_multipalabras(tmp_path):
    # Asociaciones y frases sintéticas: solo comprueban software, no son SWOW-RP.
    respuestas = pd.DataFrame([
        ("frío", "muñeco de nieve", "hielo", ""),
        ("muñeco de nieve", "frío", "hielo", ""),
        ("hielo", "frío", "muñeco de nieve", ""),
        ("aislado", "descartado", "", ""),
    ], columns=["cue", "R1", "R2", "R3"])
    fuerzas = calcular_fuerzas(a_formato_largo(respuestas))
    grafo = mayor_componente_fuerte(construir_grafo(fuerzas))
    nodos = tmp_path / "nodos.txt"
    exportar_nodos(grafo, nodos)
    assert set(leer_nodos(nodos).values()) == set(grafo)
    assert "aislado" not in grafo

    fuente = tmp_path / "corpus.csv"
    escribir_csv(fuente, [
        {"concepto": "hielo", "definicion": "Muñecos de nieve muy fríos.", "fuente": "fixture"},
        {"concepto": "muñeco_de_nieve", "definicion": "Material frío que se encuentra congelado.", "fuente": "fixture"},
        {"concepto": "aislado", "definicion": "Material frío que se encuentra congelado.", "fuente": "fixture"},
    ], ["concepto", "definicion", "fuente"])

    salida = tmp_path / "salida"
    resumen = preparar(fuente, nodos, salida, minimo=2)
    assert resumen["cumple_minimo"]
    assert resumen["definiciones_aceptadas"] == 2
    assert resumen["motivos_descarte"] == {"objetivo_fuera_grafo": 1}
    procesadas = [json.loads(linea) for linea in (salida / "preprocesado.jsonl").read_text(encoding="utf-8").splitlines()]
    assert {fila["concepto"] for fila in procesadas} == {"hielo", "muñeco de nieve"}
    assert procesadas[0]["lemas_en_grafo"] == ["muñeco de nieve", "frío"]
    assert all(nodo in grafo for fila in procesadas for nodo in fila["lemas_en_grafo"])
