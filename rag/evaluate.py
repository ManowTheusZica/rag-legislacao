"""Avaliacao com gabarito: hit@1, hit@3 e MRR. Numero real, sem enfeite."""
from __future__ import annotations

from .index import Indice

GABARITO = [
    # Cada par foi conferido lendo o texto do artigo dentro do corpus.
    ("quais as penalidades de dirigir sem possuir CNH", 162),
    ("dirigir sob influencia de alcool acima de seis decigramas", 165),
    ("conduzir motocicleta sem capacete de seguranca", 244),
    ("dirigir usando telefone celular", 252),
    ("disputar corrida racha em via publica", 173),
    ("transpor bloqueio viario policial", 210),
    ("dirigir ameacando pedestres que atravessam", 170),
    ("concentracao de alcool no sangue comprova impedimento", 276),
    ("crime de transito dirigir bebado expondo dano", 306),
    ("uso obrigatorio do cinto de seguranca", 65),
    ("penalidade para quem deixa de usar cinto de seguranca", 167),
    ("transporte de carga em veiculo de passageiros", 109),
    ("transportar crianca sem as normas de seguranca", 168),
    ("velocidade maxima permitida na via", 61),
    ("estacionar o veiculo em desacordo com a sinalizacao", 181),
    ("circulacao de veiculos pelo lado direito da pista", 29),
    ("pedestre atravessando na faixa tem prioridade de passagem", 70),
    ("equipamentos obrigatorios dos veiculos", 105),
]


def avaliar(indice: Indice, gabarito: list[tuple[str, int]] | None = None) -> dict:
    gabarito = gabarito or GABARITO
    acertos_1 = acertos_3 = 0
    soma_rr = 0.0
    detalhes = []

    for pergunta, esperado in gabarito:
        achados = indice.consultar(pergunta, limite=3)
        numeros = [documento["artigo"] for _, documento in achados]
        posicao = numeros.index(esperado) + 1 if esperado in numeros else 0

        acertos_1 += 1 if posicao == 1 else 0
        acertos_3 += 1 if posicao else 0
        soma_rr += (1 / posicao) if posicao else 0.0
        detalhes.append(
            {"pergunta": pergunta, "esperado": esperado, "top3": numeros, "posicao": posicao}
        )

    total = len(gabarito)
    return {
        "total": total,
        "hit@1": round(acertos_1 / total, 3),
        "hit@3": round(acertos_3 / total, 3),
        "mrr": round(soma_rr / total, 3),
        "detalhes": detalhes,
    }
