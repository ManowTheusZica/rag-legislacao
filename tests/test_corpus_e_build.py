import json

from rag.corpus import carregar
from scripts.build_corpus import dividir_artigos, limpar


def test_carregar_jsonl(arquivo_corpus):
    artigos = carregar(arquivo_corpus)
    assert len(artigos) == 3
    assert artigos[0]["artigo"] == 65


def test_dividir_artigos_por_marcador():
    texto = limpar(
        "Art. 1 Considera-se trânsito a utilização das vias por pessoas, veículos e animais.\n"
        "Art. 2 O trânsito em condições seguras é um direito de todos e dever do Estado."
    )
    artigos = dividir_artigos(texto)
    assert [a["artigo"] for a in artigos] == [1, 2]
    assert "direito de todos" in artigos[1]["texto"]


def test_dividir_descarta_trecho_curto():
    assert dividir_artigos("Art. 9 curto") == []
