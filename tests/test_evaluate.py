from rag.evaluate import avaliar


def test_avaliar_conta_acertos(indice):
    gabarito = [
        ("uso do cinto de seguranca", 65),
        ("dirigir sem habilitacao", 162),
        ("pergunta que nao existe no corpus sobre astronomia", 999),
    ]
    resultado = avaliar(indice, gabarito)
    assert resultado["total"] == 3
    assert resultado["hit@1"] == round(2 / 3, 3)
    assert resultado["hit@3"] == round(2 / 3, 3)
    assert resultado["detalhes"][2]["posicao"] == 0
