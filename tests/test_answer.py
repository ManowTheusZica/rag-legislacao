from rag.answer import SEM_RESPOSTA, responder


def test_resposta_cita_o_artigo(indice):
    resultado = responder(indice, "preciso usar cinto de seguranca?")
    assert resultado["artigos"]
    assert resultado["artigos"][0]["artigo"] == 65
    assert "Art. 65" in resultado["resposta"]
    assert resultado["fonte"] == "extrativo"


def test_pergunta_sem_relacao_com_o_corpus(indice):
    resultado = responder(indice, "qual a capital da Australia")
    assert resultado == {"resposta": SEM_RESPOSTA, "artigos": [], "fonte": "extrativo"}


def test_fallback_quando_llm_nao_configurada(indice, monkeypatch):
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    resultado = responder(indice, "alcool ao volante")
    assert resultado["fonte"] == "extrativo"
