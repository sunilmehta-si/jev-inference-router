import math
import re
from collections import Counter
from importlib.resources import files

STOP = {"the", "a", "an", "is", "are", "to", "of", "in", "how", "do", "i", "this", "what"}


def terms(text):
    return Counter(w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOP)


class Knowledge:
    """Small, local lexical retriever; no embeddings or network ingestion."""

    def __init__(self):
        root = files("jev_router").joinpath("knowledge")
        self.documents = {p.name: p.read_text() for p in root.iterdir() if p.name.endswith(".md")}

    def search(self, question, limit=3):
        query = terms(question)
        results = []
        for name, text in self.documents.items():
            words = terms(text)
            dot = sum(v * words[k] for k, v in query.items())
            norm = math.sqrt(
                sum(v * v for v in query.values()) * sum(v * v for v in words.values())
            )
            score = dot / norm if norm else 0
            if score:
                results.append({"id": name, "text": text, "lexical_score": round(score, 4)})
        return sorted(results, key=lambda r: (-r["lexical_score"], r["id"]))[:limit]
