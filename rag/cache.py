"""Cache de respostas para perguntas equivalentes.

Duas perguntas raramente sao identicas ("dirigir sem cnh" x "dirigir sem
habilitacao"), entao a chave e' o conjunto de radicais (mesma tokenizacao do
indice) e o casamento usa Jaccard. Isso pega reformulacao sem servir resposta
errada para pergunta diferente - o limiar padrao (0,85) exige quase o mesmo
conjunto de termos.

Por que cache: a busca BM25 leva poucos milissegundos, mas a chamada de LLM
(opcional) leva segundos e custa dinheiro. O cache e' o unico jeito de baixar
custo por pergunta sem mexer no modelo.
"""
from __future__ import annotations

import time
from collections import OrderedDict

from .index import tokenizar

LIMIAR_PADRAO = 0.85


class CacheSemantico:
    def __init__(self, limite: int = 256, ttl_segundos: float = 3600.0, limiar: float = LIMIAR_PADRAO):
        self.limite = limite
        self.ttl = ttl_segundos
        self.limiar = limiar
        self._itens: OrderedDict[frozenset, tuple[float, dict]] = OrderedDict()
        self.acertos = 0
        self.erros = 0

    # ------------------------------------------------------------- interno
    def _chave(self, pergunta: str) -> frozenset:
        return frozenset(tokenizar(pergunta))

    @staticmethod
    def _jaccard(a: frozenset, b: frozenset) -> float:
        if not a or not b:
            return 0.0
        return len(a & b) / len(a | b)

    def _expirou(self, quando: float, agora: float) -> bool:
        return self.ttl > 0 and (agora - quando) > self.ttl

    def _limpar(self, agora: float) -> None:
        vencidos = [chave for chave, (quando, _) in self._itens.items() if self._expirou(quando, agora)]
        for chave in vencidos:
            del self._itens[chave]

    # -------------------------------------------------------------- publico
    def obter(self, pergunta: str) -> dict | None:
        agora = time.time()
        self._limpar(agora)
        chave = self._chave(pergunta)

        exato = self._itens.get(chave)
        if exato:
            self._itens.move_to_end(chave)
            self.acertos += 1
            return dict(exato[1], cache="exato")

        melhor: tuple[float, frozenset] | None = None
        for guardada in self._itens:
            semelhanca = self._jaccard(chave, guardada)
            if semelhanca >= self.limiar and (melhor is None or semelhanca > melhor[0]):
                melhor = (semelhanca, guardada)
        if melhor:
            self._itens.move_to_end(melhor[1])
            self.acertos += 1
            return dict(self._itens[melhor[1]][1], cache="aproximado")

        self.erros += 1
        return None

    def guardar(self, pergunta: str, resposta: dict) -> None:
        chave = self._chave(pergunta)
        if not chave:
            return
        self._itens[chave] = (time.time(), dict(resposta))
        self._itens.move_to_end(chave)
        while len(self._itens) > self.limite:
            self._itens.popitem(last=False)

    def limpar(self) -> None:
        self._itens.clear()
        self.acertos = self.erros = 0

    def estatisticas(self) -> dict:
        total = self.acertos + self.erros
        return {
            "itens": len(self._itens),
            "acertos": self.acertos,
            "erros": self.erros,
            "taxa_acerto": round(self.acertos / total, 3) if total else 0.0,
        }
