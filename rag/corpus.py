"""Carrega os artigos do CTB."""
from __future__ import annotations

import json
from pathlib import Path

CAMINHO_PADRAO = Path(__file__).resolve().parent.parent / "data" / "ctb_artigos.jsonl"


def carregar(caminho: Path | str | None = None) -> list[dict]:
    caminho = Path(caminho) if caminho else CAMINHO_PADRAO
    if not caminho.exists():
        raise FileNotFoundError(
            "corpus ausente: rode python scripts/build_corpus.py antes de consultar"
        )
    with caminho.open(encoding="utf-8") as arquivo:
        return [json.loads(linha) for linha in arquivo if linha.strip()]
