"""Busca BM25 sobre trechos do CTB. Implementacao propria, sem dependencias externas.

Decisoes que importam:
- Artigos sao longos (caput + paragrafos + incisos). Indexar o artigo inteiro
  dilui a pontuacao, entao cada paragrafo vira um trecho independente que
  aponta para o numero do artigo.
- Portugues tem muita flexao: radical leve (sem acento, sem plural, sem sufixo
  verbal) faz "dirige", "dirigir" e "dirigindo" cairem no mesmo token.
- BM25 penaliza documento longo, ao contrario do TF-IDF puro.
"""
from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter

STOPWORDS = set(
    """a o as os um uma de do da dos das em no na nos nas por para com sem que se
    e ou ao aos a as pelo pela pelos pelas seu sua seus suas como mais menos nao
    ser esta estao foi sao tem ter sobre entre quando qual quais onde lhe lhes
    ja nem tambem apenas cada todos todas outro outra mesmo assim apos ate isso
    este esta esse essa aquele aquela eu voce ele ela nos vos eles elas meu minha""".split()
)

TOKEN_RE = re.compile(r"[a-z0-9]{3,}")
SUFIXOS = ("mente", "cao", "ando", "endo", "indo", "ado", "ada", "ido", "ida", "ar", "er", "ir")
VOGAIS = "aeiou"


def sem_acento(texto: str) -> str:
    normalizado = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in normalizado if not unicodedata.combining(c))


def radical(palavra: str) -> str:
    """Radical leve de portugues: suficiente para casar flexoes comuns."""
    if len(palavra) <= 4:
        return palavra
    # plural para singular antes de cortar sufixo (habilitacoes -> habilitacao)
    if palavra.endswith("coes"):
        palavra = palavra[:-4] + "cao"
    elif palavra.endswith("oes"):
        palavra = palavra[:-3] + "ao"
    elif palavra.endswith("aes"):
        palavra = palavra[:-3] + "ao"
    elif palavra.endswith("s") and not palavra.endswith("ss"):
        palavra = palavra[:-1]
    for sufixo in SUFIXOS:
        if palavra.endswith(sufixo) and len(palavra) - len(sufixo) >= 4:
            base = palavra[: -len(sufixo)]
            return base + "c" if sufixo == "cao" else base
    if len(palavra) > 5 and palavra[-1] in VOGAIS:
        return palavra[:-1]
    return palavra


def tokenizar(texto: str) -> list[str]:
    return [
        radical(token)
        for token in TOKEN_RE.findall(sem_acento(texto))
        if token not in STOPWORDS
    ]


def chunkar(artigo: dict, alvo: int = 320) -> list[dict]:
    """Quebra um artigo em trechos com contexto, sem cortar no meio de uma frase."""
    pedacos = [p.strip() for p in re.split(r"\n|(?<=[.;])\s+(?=[A-Z§])", artigo["texto"]) if p.strip()]
    trechos: list[str] = []
    atual = ""
    for pedaco in pedacos:
        if atual and len(atual) + len(pedaco) > alvo:
            trechos.append(atual.strip())
            atual = pedaco
        else:
            atual = (atual + " " + pedaco).strip() if atual else pedaco
    if atual.strip():
        trechos.append(atual.strip())

    return [
        {
            "artigo": artigo["artigo"],
            "capitulo": artigo.get("capitulo", ""),
            "texto": trecho,
            "trecho_id": "%d-%d" % (artigo["artigo"], posicao),
        }
        for posicao, trecho in enumerate(trechos)
        if len(trecho) >= 25
    ]


class Indice:
    """BM25 (k1=1.5, b=0.75) sobre trechos."""

    k1 = 1.5
    b = 0.75

    def __init__(self, artigos: list[dict]):
        self.artigos = artigos
        self.trechos: list[dict] = []
        for artigo in artigos:
            self.trechos.extend(chunkar(artigo))

        self.tf: list[Counter] = [Counter(tokenizar(t["texto"])) for t in self.trechos]
        self.tamanhos = [sum(contagem.values()) for contagem in self.tf]
        self.medio = (sum(self.tamanhos) / len(self.tamanhos)) if self.tamanhos else 0.0

        frequencia_documentos: Counter = Counter()
        for contagem in self.tf:
            frequencia_documentos.update(set(contagem))
        total = len(self.trechos)
        self.idf = {
            termo: math.log(1 + (total - freq + 0.5) / (freq + 0.5))
            for termo, freq in frequencia_documentos.items()
        }

    def pontuar(self, termos: list[str], posicao: int) -> float:
        contagem = self.tf[posicao]
        tamanho = self.tamanhos[posicao] or 1
        total = 0.0
        for termo in termos:
            freq = contagem.get(termo)
            if not freq:
                continue
            idf = self.idf.get(termo, 0.0)
            total += idf * (freq * (self.k1 + 1)) / (
                freq + self.k1 * (1 - self.b + self.b * tamanho / (self.medio or 1))
            )
        return total

    def consultar(self, pergunta: str, limite: int = 5) -> list[tuple[float, dict]]:
        termos = tokenizar(pergunta)
        if not termos:
            return []
        pontuacoes = []
        for posicao, trecho in enumerate(self.trechos):
            valor = self.pontuar(termos, posicao)
            if valor > 0:
                pontuacoes.append((valor, trecho))
        pontuacoes.sort(key=lambda item: item[0], reverse=True)

        # Melhor trecho por artigo: o mesmo artigo nao ocupa 5 posicoes.
        vistos: set[int] = set()
        saida: list[tuple[float, dict]] = []
        for valor, trecho in pontuacoes:
            if trecho["artigo"] in vistos:
                continue
            vistos.add(trecho["artigo"])
            saida.append((round(valor, 3), trecho))
            if len(saida) >= limite:
                break
        return saida
