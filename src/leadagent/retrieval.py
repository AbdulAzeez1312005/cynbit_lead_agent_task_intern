"""Tiny dependency-free TF-IDF retriever over the Cynbit knowledge base.

The KB is ~10 short documents, so a vector database would be over-engineering for the PoC.
The `Retriever` interface is deliberately small so it can be swapped for Pinecone
(already in Cynbit's stack) once the KB grows to hundreds of case studies and proposals.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

from .schema import KBMatch

KB_PATH = Path(__file__).resolve().parents[2] / "data" / "cynbit_kb.json"
_STOP = set(
    "a an the and or of for to in on with is are we our you your i it this that be as at by from "
    "need want looking build make have has can will would like us".split()
)


def _tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in _STOP and len(t) > 1]


class Retriever:
    def __init__(self, kb_path: Path = KB_PATH):
        self.docs = json.loads(Path(kb_path).read_text(encoding="utf-8"))
        corpus = [_tokens(d["name"] + " " + d["name"] + " " + d["text"]) for d in self.docs]
        n = len(corpus)
        df = Counter(t for doc in corpus for t in set(doc))
        self.idf = {t: math.log((1 + n) / (1 + c)) + 1 for t, c in df.items()}
        self.vecs = [self._vec(doc) for doc in corpus]

    def _vec(self, toks: list[str]) -> dict[str, float]:
        tf = Counter(toks)
        v = {t: c * self.idf.get(t, 0.0) for t, c in tf.items() if t in self.idf}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {t: x / norm for t, x in v.items()}

    def search(self, query: str, k: int = 3) -> list[KBMatch]:
        q = self._vec(_tokens(query))
        scored = []
        for d, v in zip(self.docs, self.vecs):
            s = sum(w * v.get(t, 0.0) for t, w in q.items())
            scored.append((s, d))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            KBMatch(id=d["id"], name=d["name"], type=d["type"], url=d["url"], score=round(s, 3))
            for s, d in scored[:k]
            if s > 0
        ]
