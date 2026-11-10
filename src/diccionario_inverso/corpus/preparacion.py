"""Validación auditable contra los nodos activos que entregue Carlos."""

import csv
import json
from collections import Counter
from pathlib import Path

from .archivos import escribir_csv, escribir_json, leer_nodos, sha256
from .normalizacion import contiene_objetivo, normalizar
from .preprocesamiento import Preprocesador, texto_para_nlp


def preparar(origen: Path, ruta_nodos: Path, salida: Path, modelo: str = "es_core_news_md", minimo: int = 300) -> dict:
    if minimo < 1:
        raise ValueError("El mínimo debe ser positivo.")
    indice = leer_nodos(ruta_nodos)
    with origen.open(encoding="utf-8-sig", newline="") as archivo:
        reader = csv.DictReader(archivo)
        if not {"concepto", "definicion", "fuente"}.issubset(reader.fieldnames or []):
            raise ValueError("El corpus necesita concepto, definicion y fuente.")
        filas = list(reader)
        campos = list(reader.fieldnames)
    if "particion" not in campos:
        campos.append("particion")
    pre = Preprocesador(indice, modelo)
    auditoria, elegibles = [], []
    vistos = set()
    for fila in filas:
        concepto = normalizar(fila["concepto"])
        definicion = fila["definicion"].strip()
        razones = []
        if not concepto or not definicion or not fila["fuente"].strip():
            razones.append("campos_vacios")
        if concepto not in indice:
            razones.append("objetivo_fuera_grafo")
        if contiene_objetivo(definicion, concepto):
            razones.append("mencion_literal_objetivo")
        clave = (concepto, normalizar(definicion))
        if clave in vistos:
            razones.append("duplicada")
        vistos.add(clave)
        if razones:
            auditoria.append({**fila, "motivos": "|".join(razones)})
        else:
            fila["concepto"] = indice[concepto]
            fila["particion"] = fila.get("particion") or "pendiente"
            elegibles.append(fila)
    aceptadas, procesadas = [], []
    documentos = pre.nlp.pipe((texto_para_nlp(f["definicion"]) for f in elegibles), batch_size=64)
    for fila, doc in zip(elegibles, documentos):
        if pre.contiene_objetivo_lematizado(doc, fila["concepto"]):
            auditoria.append({**fila, "motivos": "mencion_lematizada_objetivo"})
            continue
        resultado = pre.analizar_doc(doc)
        aceptadas.append(fila)
        procesadas.append({**fila, **resultado.como_dict()})
    n = len(aceptadas)
    total_lemas = sum(len(f["lemas"]) for f in procesadas)
    total_presentes = sum(len(f["lemas_en_grafo"]) for f in procesadas)
    razones = Counter(r for fila in auditoria for r in fila["motivos"].split("|"))
    resumen = {
        "estado": "VALIDADO_CONTRA_LISTA_DE_NODOS" if n >= minimo else "INSUFICIENTE",
        "minimo_requerido": minimo, "cumple_minimo": n >= minimo,
        "definiciones_fuente": len(filas), "definiciones_aceptadas": n,
        "conceptos_aceptados": len({f["concepto"] for f in aceptadas}),
        "definiciones_descartadas": len(auditoria), "motivos_descarte": dict(razones),
        "nodos_activos_declarados": len(indice),
        "definiciones_con_lemas_en_grafo": sum(bool(f["lemas_en_grafo"]) for f in procesadas),
        "cobertura_definiciones": sum(bool(f["lemas_en_grafo"]) for f in procesadas) / n if n else 0.0,
        "promedio_lemas_en_grafo": total_presentes / n if n else 0.0,
        "promedio_lemas_unicos_en_grafo": sum(len(set(f["lemas_en_grafo"])) for f in procesadas) / n if n else 0.0,
        "cobertura_lexica_micro": total_presentes / total_lemas if total_lemas else 0.0,
        "cobertura_lexica_macro": sum(f["cobertura_lexica"] for f in procesadas) / n if n else 0.0,
        "sin_lemas_en_grafo": sum(not f["lemas_en_grafo"] for f in procesadas),
        "modelo": pre.modelo, "version_modelo": pre.version_modelo,
        "sha256_corpus_fuente": sha256(origen), "sha256_lista_nodos": sha256(ruta_nodos),
        "particiones": dict(Counter(f["particion"] for f in aceptadas)),
        "nota": "La lista debe proceder del grafo final. No se eliminan casos sin cobertura. Carlos asigna desarrollo/prueba.",
    }
    salida.mkdir(parents=True, exist_ok=True)
    escribir_csv(salida / "corpus.csv", aceptadas, campos)
    escribir_csv(salida / "descartadas.csv", auditoria, campos + ["motivos"])
    with (salida / "preprocesado.jsonl").open("w", encoding="utf-8") as archivo:
        for fila in procesadas:
            archivo.write(json.dumps(fila, ensure_ascii=False) + "\n")
    escribir_json(salida / "cobertura.json", resumen)
    return resumen
