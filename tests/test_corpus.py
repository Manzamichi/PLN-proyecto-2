"""Pruebas de fugas, multipalabras, cobertura y contrato con el grafo."""

import csv
import gzip
import json
from pathlib import Path
import tempfile
import unittest

from diccionario_inverso.corpus.archivos import leer_nodos, escribir_csv
from diccionario_inverso.corpus.fuentes import extraer
from diccionario_inverso.corpus.normalizacion import contiene_objetivo, normalizar
from diccionario_inverso.corpus.preparacion import preparar
from diccionario_inverso.corpus.preprocesamiento import Preprocesador

TEMP_PRUEBAS = Path(__file__).resolve().parents[1] / "tmp" / "tests"
TEMP_PRUEBAS.mkdir(parents=True, exist_ok=True)


class NormalizacionTests(unittest.TestCase):
    def test_acentos_y_unicode(self):
        self.assertEqual(normalizar("  MUÑECO de NIEVE  "), "muñeco_de_nieve")
        self.assertEqual(normalizar("cafe\u0301"), "café")
        self.assertNotEqual(normalizar("año"), normalizar("ano"))

    def test_mencion_por_palabras_completas(self):
        self.assertFalse(contiene_objetivo("Soldado en la sombra", "sol"))
        self.assertTrue(contiene_objetivo("Es un SOL brillante.", "sol"))
        self.assertTrue(contiene_objetivo("Un muñeco de nieve blanco.", "muñeco_de_nieve"))

    def test_nodos_activos_y_colisiones(self):
        with tempfile.TemporaryDirectory(dir=TEMP_PRUEBAS) as temporal:
            p = Path(temporal) / "nodos.csv"
            p.write_text("nodo,grado\nCasa,4\naisladó,0\n", encoding="utf-8")
            self.assertEqual(leer_nodos(p), {"casa": "Casa"})
            p.write_text("nodo\nCasa\ncasa\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                leer_nodos(p)

    def test_esquema_json_invalido(self):
        with tempfile.TemporaryDirectory(dir=TEMP_PRUEBAS) as temporal:
            p = Path(temporal) / "nodos.json"
            p.write_text('{"nodos": ["casa"]}', encoding="utf-8")
            with self.assertRaises(ValueError):
                leer_nodos(p)


class FuenteTests(unittest.TestCase):
    def test_solo_lemas_espanoles_y_glosas_no_filtradas_por_alfabeto(self):
        def entrada(word, gloss, **extra):
            return {"word": word, "lang_code": "es", "pos": "noun", "categories": ["ES:Lemas"],
                    "senses": [{"glosses": [gloss]}], **extra}
        filas = [
            entrada("perro", "Mamífero doméstico de la familia de los cánidos."),
            entrada("perro", "Mamífero doméstico de la familia de los cánidos."),
            entrada("sol", "El sol es una estrella muy brillante."),
            entrada("casa", "Building used by a family as a home.", lang_code="en"),
            entrada("casas", "Forma plural del sustantivo casa.", categories=["ES:Formas flexivas"]),
            entrada("zapato", "Prenda que protege el pie durante la marcha."),
        ]
        with tempfile.TemporaryDirectory(dir=TEMP_PRUEBAS) as temporal:
            origen, destino = Path(temporal) / "fuente.gz", Path(temporal) / "corpus.csv"
            with gzip.open(origen, "wt", encoding="utf-8") as archivo:
                for fila in filas:
                    archivo.write(json.dumps(fila) + "\n")
            resumen = extraer(origen, destino)
            self.assertEqual(resumen["definiciones"], 2)
            self.assertEqual(resumen["conteos"]["duplicadas"], 1)
            self.assertEqual(resumen["conteos"]["mencion_literal_objetivo"], 1)
            with destino.open(encoding="utf-8", newline="") as archivo:
                self.assertEqual({r["concepto"] for r in csv.DictReader(archivo)}, {"perro", "zapato"})
            self.assertIn("sol", destino.with_name("corpus_menciones.csv").read_text(encoding="utf-8"))


class SpacyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import spacy
        cls.nlp = spacy.load("es_core_news_md", disable=["parser", "ner"])

    def pre(self, nodos):
        return Preprocesador(nodos, nlp=self.nlp)

    def test_modelo_lematiza_y_conserva_ids_originales(self):
        r = self.pre(["Perro", "correr"]).procesar("Los perros corren.")
        self.assertEqual(r.lemas_en_grafo, ["Perro", "correr"])
        self.assertEqual(r.cobertura_lexica, 1.0)

    def test_multipalabras_antes_de_stop_words(self):
        pre = self.pre(["muñeco", "nieve", "muñeco_de_nieve"])
        self.assertEqual(pre.lemas_para_modelo("Muñecos de nieve."), ["muñeco_de_nieve"])
        self.assertEqual(pre.lemas_para_modelo("Muñecos_de_nieve."), ["muñeco_de_nieve"])
        self.assertEqual(pre.lemas_para_modelo("Muñeco, de nieve."), ["muñeco", "nieve"])

    def test_frase_mas_larga(self):
        pre = self.pre(["oso", "oso_polar", "oso_polar_blanco"])
        self.assertEqual(pre.lemas_para_modelo("Oso polar blanco."), ["oso_polar_blanco"])

    def test_menciones_lematizadas(self):
        pre = self.pre(["perro"])
        self.assertTrue(pre.contiene_objetivo_lematizado(self.nlp("Los perros son animales."), "perro"))
        self.assertFalse(pre.contiene_objetivo_lematizado(self.nlp("El soldado camina."), "sol"))

    def test_cobertura_cero_y_repeticiones(self):
        pre = self.pre(["perro"])
        self.assertEqual(pre.procesar("y de la").cobertura_lexica, 0.0)
        r = pre.procesar("Perro perro xilitol.")
        self.assertEqual(r.lemas_en_grafo, ["perro", "perro"])
        self.assertEqual(r.fuera_vocabulario, ["xilitol"])
        self.assertAlmostEqual(r.cobertura_lexica, 2 / 3)

    def test_rechaza_pipeline_sin_lematizador(self):
        import spacy
        with self.assertRaises(ValueError):
            Preprocesador(["casa"], nlp=spacy.blank("es"))

    def test_preparacion_auditoria_y_denominador(self):
        # Estos son datos sintéticos para pruebas de software, no de evaluación.
        filas = [
            {"concepto": "casa", "definicion": "El perro duerme.", "fuente": "prueba"},
            {"concepto": "perro", "definicion": "Los perros son animales.", "fuente": "prueba"},
            {"concepto": "sol", "definicion": "Xilitol xilitol.", "fuente": "prueba"},
            {"concepto": "luna", "definicion": "Un satélite natural.", "fuente": "prueba"},
            {"concepto": "casa", "definicion": "El perro duerme.", "fuente": "prueba"},
        ]
        with tempfile.TemporaryDirectory(dir=TEMP_PRUEBAS) as temporal:
            base = Path(temporal)
            origen, nodos, salida = base / "fuente.csv", base / "nodos.txt", base / "salida"
            escribir_csv(origen, filas, ["concepto", "definicion", "fuente"])
            nodos.write_text("casa\nperro\nsol\n", encoding="utf-8")
            r = preparar(origen, nodos, salida, minimo=3)
            self.assertFalse(r["cumple_minimo"])
            self.assertEqual(r["definiciones_aceptadas"], 2)
            self.assertEqual(r["definiciones_descartadas"], 3)
            self.assertEqual(r["cobertura_definiciones"], 0.5)
            self.assertEqual(r["sin_lemas_en_grafo"], 1)
            self.assertEqual(r["motivos_descarte"]["mencion_lematizada_objetivo"], 1)
            self.assertEqual(r["particiones"], {"pendiente": 2})
            procesado = [json.loads(s) for s in (salida / "preprocesado.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(procesado), 2)
            self.assertTrue(all(x in {"casa", "perro", "sol"} for f in procesado for x in f["lemas_en_grafo"]))


if __name__ == "__main__":
    unittest.main()
