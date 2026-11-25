"""Testes do cache semantico e da avaliacao completa."""
from __future__ import annotations

from rag.answer import SEM_RESPOSTA, responder
from rag.avaliacao import avaliar_completo, calibrar_limiar, formatar_markdown
from rag.cache import CacheSemantico


# ------------------------------------------------------------------- cache
def test_cache_acerta_pergunta_identica():
    cache = CacheSemantico()
    cache.guardar("dirigir sem cnh", {"resposta": "Art. 162", "artigos": []})
    achado = cache.obter("dirigir sem cnh")
    assert achado["resposta"] == "Art. 162"
    assert achado["cache"] == "exato"


def test_cache_aceita_reformulacao_parecida():
    cache = CacheSemantico()
    cache.guardar(
        "penalidade para dirigir sem possuir cnh",
        {"resposta": "Art. 162", "artigos": []},
    )
    achado = cache.obter("penalidade para dirigir sem possuir cnh?")
    assert achado is not None
    assert achado["cache"] in ("exato", "aproximado")


def test_cache_recusa_pergunta_diferente():
    cache = CacheSemantico()
    cache.guardar("penalidade para dirigir sem cnh", {"resposta": "Art. 162", "artigos": []})
    assert cache.obter("sinalizacao de transito em rodovia") is None


def test_cache_respeita_limite_de_itens():
    cache = CacheSemantico(limite=2)
    for i in range(5):
        cache.guardar("pergunta %d sobre transito" % i, {"resposta": str(i), "artigos": []})
    assert cache.estatisticas()["itens"] <= 2


def test_cache_expira_por_ttl(monkeypatch):
    cache = CacheSemantico(ttl_segundos=10)
    cache.guardar("cinto de seguranca", {"resposta": "Art. 65", "artigos": []})
    agora = 1_000_000.0
    monkeypatch.setattr("rag.cache.time.time", lambda: agora)
    cache.guardar("cinto de seguranca", {"resposta": "Art. 65", "artigos": []})
    monkeypatch.setattr("rag.cache.time.time", lambda: agora + 11)
    assert cache.obter("cinto de seguranca") is None


def test_cache_estatisticas():
    cache = CacheSemantico()
    cache.obter("nao existe")
    cache.guardar("cinto", {"resposta": "x", "artigos": []})
    cache.obter("cinto")
    stats = cache.estatisticas()
    assert stats["acertos"] == 1
    assert stats["erros"] == 1
    assert stats["taxa_acerto"] == 0.5


# ---------------------------------------------------------------- resposta
def test_responder_abstem_abaixo_do_limiar(indice):
    resultado = responder(indice, "receita de bolo de cenoura", score_minimo=999.0)
    assert resultado["resposta"] == SEM_RESPOSTA
    # sem nenhum termo em comum nao ha nem candidato; com match parcial, o limiar barra
    assert resultado["fonte"] in ("abaixo_do_limiar", "sem_resultado")


def test_responder_cita_artigo(indice):
    resultado = responder(indice, "uso do cinto de seguranca", score_minimo=0.0)
    assert "Art. 65" in resultado["resposta"]
    assert resultado["artigos"][0]["artigo"] == 65


def test_responder_usa_cache_na_segunda_chamada(indice):
    cache = CacheSemantico()
    primeira = responder(indice, "dirigir sem habilitacao", score_minimo=0.0, cache=cache)
    segunda = responder(indice, "dirigir sem habilitacao", score_minimo=0.0, cache=cache)
    assert primeira["resposta"] == segunda["resposta"]
    assert segunda["cache"] == "exato"
    assert cache.estatisticas()["acertos"] == 1


# --------------------------------------------------------------- avaliacao
def test_calibrar_limiar_devolve_limiar_e_contagens(indice):
    gabarito = [("uso do cinto de seguranca", 65), ("dirigir sem habilitacao", 162)]
    negativas = ["receita de bolo de cenoura"]
    calibracao = calibrar_limiar(indice, gabarito, negativas)
    assert calibracao["total_positivas"] == 2
    assert calibracao["total_negativas"] == 1
    assert calibracao["retidos"] >= 1
    assert calibracao["limiar"] >= 0.0


def test_avaliar_completo_mede_tudo(indice):
    gabarito = [("uso do cinto de seguranca", 65), ("dirigir sem habilitacao", 162)]
    negativo = ["receita de bolo de cenoura"]
    resultado = avaliar_completo(indice, limiar=0.0, gabarito=gabarito, negativas=negativo)
    assert resultado["total"] == 2
    assert resultado["hit@1"] == 1.0
    assert resultado["citacao_correta"] == 1.0
    assert resultado["latencia_ms"]["p95"] >= 0
    assert resultado["custo"]["tokens_contexto_por_pergunta"] > 0
    assert 0.0 <= resultado["abstencao"] <= 1.0


def test_avaliar_completo_com_repeticao_usa_cache(indice):
    gabarito = [("uso do cinto de seguranca", 65)]
    resultado = avaliar_completo(indice, limiar=0.0, gabarito=gabarito, negativas=["x"], repetir=3)
    assert resultado["cache"]["acertos"] == 2       # 3 repeticoes, 1 vai no indice
    assert resultado["total"] == 3


def test_markdown_tem_as_metricas(indice):
    gabarito = [("uso do cinto de seguranca", 65)]
    resultado = avaliar_completo(indice, limiar=0.0, gabarito=gabarito, negativas=["x"])
    texto = formatar_markdown(resultado, calibrar_limiar(indice, gabarito, ["x"]))
    for esperado in ("hit@1", "hit@3", "MRR", "abstencao", "latencia p95", "custo por pergunta"):
        assert esperado in texto
