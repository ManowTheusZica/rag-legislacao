"""Avaliacao completa: acerto, abstencao, citacao, latencia e custo.

O `evaluate.py` original so' media hit@1/hit@3. Aqui entra o que quebra em
producao de verdade:

1. **Abstencao** - pergunta fora do CTB tem que virar "nao encontrei", nao o
   artigo menos pior. O limiar de score e' calibrado com dado, nao chutado.
2. **Citacao** - a resposta precisa citar o artigo que o indice recuperou.
   RAG que responde certo sem citar e' inauditavel.
3. **Latencia** - p50/p95 da busca, porque chatbot acima de 1s perde usuario.
4. **Custo** - estimativa em dolar por pergunta (tokens de contexto x preco),
   para saber quanto custa 10 mil perguntas no mes.
"""
from __future__ import annotations

import statistics
import time

from .answer import SEM_RESPOSTA, responder
from .cache import CacheSemantico
from .evaluate import GABARITO
from .index import Indice

# Perguntas que NAO sao do CTB. Deve abster, nao inventar artigo.
FORA_DO_ESCOPO = [
    "qual a receita de bolo de cenoura com cobertura",
    "quem descobriu o brasil em 1500",
    "como configurar impressora wifi no windows",
    "qual o resultado do jogo de ontem do flamengo",
    "como declarar imposto de renda pessoa fisica",
    "qual a capital da australia",
    "melhor forma de investir em acoes hoje",
    "como fazer arroz soltinho",
]

CANDIDATOS_LIMIAR = (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0)

# Preco de referencia (gpt-4o-mini, jan/2026): US$ 0,15 / 1M tokens de entrada.
PRECO_POR_TOKEN = 0.15 / 1_000_000


def _top_score(indice: Indice, pergunta: str) -> float:
    achados = indice.consultar(pergunta, limite=1)
    return achados[0][0] if achados else 0.0


def calibrar_limiar(indice: Indice, gabarito=None, negativas=None) -> dict:
    """Escolhe o limiar que maximiza acerto no gabarito + abstencao nas negativas."""
    gabarito = gabarito or GABARITO
    negativas = negativas or FORA_DO_ESCOPO

    positivas = [_top_score(indice, pergunta) for pergunta, _ in gabarito]
    scores_negativos = [_top_score(indice, pergunta) for pergunta in negativas]

    melhor = {"limiar": 0.0, "pontuacao": -1.0, "retidos": 0, "abstidos": 0}
    for limiar in CANDIDATOS_LIMIAR:
        retidos = sum(1 for score in positivas if score >= limiar)
        abstidos = sum(1 for score in scores_negativos if score < limiar)
        # falso negativo (perder pergunta boa) pesa 2x: usuario odeia "nao sei"
        pontuacao = retidos - 2 * (len(negativas) - abstidos)
        if pontuacao > melhor["pontuacao"]:
            melhor = {
                "limiar": limiar,
                "pontuacao": pontuacao,
                "retidos": retidos,
                "abstidos": abstidos,
            }
    melhor["total_positivas"] = len(positivas)
    melhor["total_negativas"] = len(negativas)
    melhor["menor_score_positivo"] = round(min(positivas), 3) if positivas else 0.0
    melhor["maior_score_negativo"] = round(max(scores_negativos), 3) if scores_negativos else 0.0
    return melhor


def _citou_artigo(resposta: str, artigo: int) -> bool:
    texto = resposta.replace("Art. ", "Art.").replace("artigo ", "Art.")
    return ("Art.%d" % artigo) in texto.replace(" ", "")


def avaliar_completo(
    indice: Indice,
    limiar: float = 2.0,
    gabarito=None,
    negativas=None,
    cache: CacheSemantico | None = None,
    repetir: int = 1,
) -> dict:
    gabarito = gabarito or GABARITO
    negativas = negativas or FORA_DO_ESCOPO
    cache = cache if cache is not None else CacheSemantico()

    tempos: list[float] = []
    acertos_1 = acertos_3 = 0
    soma_rr = 0.0
    citacoes_ok = 0
    tokens_contexto = 0
    detalhes = []

    for _ in range(max(1, repetir)):
        for pergunta, esperado in gabarito:
            comeco = time.perf_counter()
            guardado = cache.obter(pergunta)
            if guardado is not None:
                achados = [(t["score"], t) for t in guardado["artigos"]]
                resultado = guardado
            else:
                achados = indice.consultar(pergunta, limite=3)
                resultado = responder(indice, pergunta, limite=3, score_minimo=limiar, cache=None)
                cache.guardar(pergunta, resultado)
            tempos.append(time.perf_counter() - comeco)

            numeros = [documento["artigo"] for _, documento in achados]
            posicao = numeros.index(esperado) + 1 if esperado in numeros else 0
            acertos_1 += 1 if posicao == 1 else 0
            acertos_3 += 1 if posicao else 0
            soma_rr += (1 / posicao) if posicao else 0.0
            if posicao and _citou_artigo(resultado["resposta"], numeros[0]):
                citacoes_ok += 1
            tokens_contexto += sum(len(t.get("texto", "")) for t in resultado.get("artigos", [])) / 4

            if repetir == 1:
                detalhes.append(
                    {"pergunta": pergunta, "esperado": esperado, "top3": numeros, "posicao": posicao}
                )

    abstidos = 0
    for pergunta in negativas:
        resultado = responder(indice, pergunta, limite=1, score_minimo=limiar, cache=None)
        if resultado["resposta"] == SEM_RESPOSTA:
            abstidos += 1

    total = len(gabarito) * max(1, repetir)
    tempos.sort()

    def percentil(p: float) -> float:
        posicao = min(len(tempos) - 1, int(round((p / 100.0) * (len(tempos) - 1))))
        return round(tempos[posicao] * 1000, 2)

    return {
        "total": total,
        "limiar": limiar,
        "hit@1": round(acertos_1 / total, 3),
        "hit@3": round(acertos_3 / total, 3),
        "mrr": round(soma_rr / total, 3),
        "citacao_correta": round(citacoes_ok / total, 3),
        "abstencao": round(abstidos / len(negativas), 3),
        "latencia_ms": {
            "media": round(statistics.mean(tempos) * 1000, 2),
            "p50": percentil(50),
            "p95": percentil(95),
            "max": round(tempos[-1] * 1000, 2),
        },
        "cache": cache.estatisticas(),
        "custo": {
            "tokens_contexto_por_pergunta": int(tokens_contexto / max(1, total)),
            "usd_por_pergunta": round((tokens_contexto / max(1, total)) * PRECO_POR_TOKEN, 6),
            "usd_10k_perguntas": round((tokens_contexto / max(1, total)) * PRECO_POR_TOKEN * 10_000, 2),
        },
        "detalhes": detalhes,
    }


def formatar_markdown(resultado: dict, calibracao: dict | None = None) -> str:
    linhas = [
        "## Resultado do benchmark",
        "",
        "| metrica | valor |",
        "|---|---|",
        "| perguntas do gabarito | %d |" % resultado["total"],
        "| hit@1 | %.1f%% |" % (100 * resultado["hit@1"]),
        "| hit@3 | %.1f%% |" % (100 * resultado["hit@3"]),
        "| MRR | %.3f |" % resultado["mrr"],
        "| citacao correta | %.1f%% |" % (100 * resultado["citacao_correta"]),
        "| abstencao em pergunta fora do escopo | %.1f%% |" % (100 * resultado["abstencao"]),
        "| latencia p50 | %.2f ms |" % resultado["latencia_ms"]["p50"],
        "| latencia p95 | %.2f ms |" % resultado["latencia_ms"]["p95"],
        "| tokens de contexto por pergunta | %d |" % resultado["custo"]["tokens_contexto_por_pergunta"],
        "| custo por pergunta | US$ %.6f |" % resultado["custo"]["usd_por_pergunta"],
        "| custo de 10 mil perguntas | US$ %.2f |" % resultado["custo"]["usd_10k_perguntas"],
        "",
    ]
    if calibracao:
        linhas += [
            "### Calibracao do limiar de abstencao",
            "",
            "| limiar | perguntas boas retidas | negativas abstidas |",
            "|---|---|---|",
            "| %.1f (escolhido) | %d/%d | %d/%d |"
            % (
                calibracao["limiar"],
                calibracao["retidos"],
                calibracao["total_positivas"],
                calibracao["abstidos"],
                calibracao["total_negativas"],
            ),
            "",
            "Menor score entre perguntas boas: %.3f. Maior score entre perguntas fora do "
            "escopo: %.3f." % (calibracao["menor_score_positivo"], calibracao["maior_score_negativo"]),
            "",
        ]
    return "\n".join(linhas)
