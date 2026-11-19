from rag.index import Indice, chunkar, radical, sem_acento, tokenizar


def test_radical_une_flexoes():
    assert radical("dirigir") == radical("dirige") == radical("dirigindo")
    assert radical("habilitacao") == radical("habilitacoes") == "habilitac"
    assert radical("seguranca") == radical("segurancas")


def test_tokenizar_remove_acento_e_stopword():
    tokens = tokenizar("É obrigatório o uso do cinto de segurança")
    assert "obrigatori" in tokens or "obrigator" in tokens
    assert "cinto" in tokens
    assert "o" not in tokens


def test_sem_acento():
    assert sem_acento("Habilitação") == "habilitacao"


def test_chunkar_respeita_limite_e_preserva_artigo(artigos):
    artigos[1]["texto"] = " ".join(["Dirigir veículo sem CNH."] * 40)
    trechos = chunkar(artigos[1], alvo=120)
    assert len(trechos) > 1
    assert all(t["artigo"] == 162 for t in trechos)
    assert all(len(t["texto"]) <= 400 for t in trechos)


def test_consulta_ordena_e_nao_repete_artigo(indice):
    achados = indice.consultar("dirigir sem habilitacao alcool", limite=3)
    numeros = [documento["artigo"] for _, documento in achados]
    assert len(numeros) == len(set(numeros))
    assert 162 in numeros
    assert achados[0][0] >= achados[-1][0]


def test_consulta_vazia_nao_explode(indice):
    assert indice.consultar("") == []
    assert indice.consultar("de a o") == []
