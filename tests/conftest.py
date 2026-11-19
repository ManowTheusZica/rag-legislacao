import json

import pytest

from rag.index import Indice

ARTIGOS = [
    {
        "artigo": 65,
        "capitulo": "CAPÍTULO III",
        "texto": "É obrigatório o uso do cinto de segurança para condutor e passageiros em todas as vias do território nacional.",
    },
    {
        "artigo": 162,
        "capitulo": "CAPÍTULO XV",
        "texto": "Dirigir veículo sem possuir Carteira Nacional de Habilitação ou Permissão para Dirigir: Infração gravíssima; Penalidade multa três vezes e retenção do veículo.",
    },
    {
        "artigo": 165,
        "capitulo": "CAPÍTULO XV",
        "texto": "Dirigir sob a influência de álcool em nível superior a seis decigramas por litro de sangue: Infração gravíssima, multa e suspensão do direito de dirigir.",
    },
]


@pytest.fixture()
def artigos():
    return [dict(artigo) for artigo in ARTIGOS]


@pytest.fixture()
def indice(artigos):
    return Indice(artigos)


@pytest.fixture()
def arquivo_corpus(tmp_path, artigos):
    caminho = tmp_path / "corpus.jsonl"
    with caminho.open("w", encoding="utf-8") as arquivo:
        for artigo in artigos:
            arquivo.write(json.dumps(artigo, ensure_ascii=False) + "\n")
    return caminho
