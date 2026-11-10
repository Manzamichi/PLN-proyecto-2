"""spaCy -> lemas útiles, nodos originales y palabras fuera de vocabulario."""

from dataclasses import asdict, dataclass
from functools import lru_cache

from .normalizacion import contiene_objetivo, contiene_secuencia, normalizar, palabras


def texto_para_nlp(texto: str) -> str:
    return normalizar(texto).replace("_", " ")


@dataclass
class Resultado:
    lemas: list[str]
    lemas_en_grafo: list[str]
    fuera_vocabulario: list[str]
    cobertura_lexica: float

    def como_dict(self) -> dict:
        return asdict(self)


class Preprocesador:
    def __init__(self, nodos, modelo: str = "es_core_news_md", *, nlp=None):
        import spacy

        self.nlp = nlp if nlp is not None else spacy.load(modelo, disable=["parser", "ner"])
        if self.nlp.lang != "es" or "lemmatizer" not in self.nlp.pipe_names:
            raise ValueError("Se necesita un modelo español con lematizador; no basta spacy.blank('es').")
        if isinstance(nodos, dict):
            self.nodos = dict(nodos)
        else:
            self.nodos = {}
            for nodo in nodos:
                clave = normalizar(nodo)
                if clave in self.nodos and self.nodos[clave] != nodo:
                    raise ValueError(f"Colisión de nodos al normalizar {nodo!r}.")
                self.nodos[clave] = nodo
        self.modelo = self.nlp.meta.get("name", modelo)
        self.version_modelo = self.nlp.meta.get("version", "desconocida")
        self.frases = {}
        for nodo in sorted(self.nodos):
            partes = tuple(palabras(nodo))
            if len(partes) > 1:
                self.frases.setdefault(partes[0], []).append((partes, nodo))
        for opciones in self.frases.values():
            opciones.sort(key=lambda x: (-len(x[0]), x[1]))

    def analizar_doc(self, doc) -> Resultado:
        # Los guiones bajos se convierten en espacios ANTES de pasar a spaCy.
        tokens = [t for t in doc if not t.is_space]
        lemas = []
        i = 0
        while i < len(tokens):
            t = tokens[i]
            superficie = normalizar(t.text)
            lema = normalizar(t.lemma_ or t.text)
            opciones = self.frases.get(superficie, []) + self.frases.get(lema, [])
            opciones = sorted(set(opciones), key=lambda x: (-len(x[0]), x[1]))
            encontrada = None
            for partes, nodo in opciones:
                tramo = tokens[i:i + len(partes)]
                # No unir frases separadas por puntuación ni saltarse stop words.
                if len(tramo) == len(partes) and all(
                    esperado in {normalizar(tok.text), normalizar(tok.lemma_ or tok.text)}
                    for esperado, tok in zip(partes, tramo)
                ):
                    encontrada = (nodo, len(partes))
                    break
            if encontrada:
                lemas.append(encontrada[0])
                i += encontrada[1]
            else:
                if t.is_alpha and not t.is_stop and not self.nlp.vocab[lema].is_stop:
                    lemas.append(lema)
                i += 1
        presentes = [self.nodos[x] for x in lemas if x in self.nodos]
        fuera = [x for x in lemas if x not in self.nodos]
        return Resultado(lemas, presentes, fuera, len(presentes) / len(lemas) if lemas else 0.0)

    def procesar(self, texto: str) -> Resultado:
        return self.analizar_doc(self.nlp(texto_para_nlp(texto)))

    def lemas_para_modelo(self, texto: str) -> list[str]:
        """Entrada común para rankear(lemas); conserva repeticiones y IDs del grafo."""
        return self.procesar(texto).lemas_en_grafo

    @lru_cache(maxsize=65536)
    def _lemas_objetivo(self, concepto: str) -> tuple[str, ...]:
        objetivo = self.nlp(texto_para_nlp(concepto))
        return tuple(normalizar(t.lemma_ or t.text) for t in objetivo if not t.is_space)

    def contiene_objetivo_lematizado(self, doc, concepto: str) -> bool:
        if contiene_objetivo(doc.text, concepto):
            return True
        # Mantener puntuación como barrera y stop words para objetivos multipalabra.
        secuencia = [normalizar(t.lemma_ or t.text) for t in doc if not t.is_space]
        variantes = [palabras(concepto), list(self._lemas_objetivo(concepto))]
        return any(contiene_secuencia(secuencia, v) for v in variantes)
