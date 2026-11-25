"""Roda a avaliacao completa e escreve docs/RESULTADOS.md com numeros reais.

  python -m scripts.benchmark            # calibra limiar e mede tudo
  python -m scripts.benchmark --repetir 3  # repete o gabarito (mede cache)
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from rag.avaliacao import avaliar_completo, calibrar_limiar, formatar_markdown
from rag.cache import CacheSemantico
from rag.corpus import carregar
from rag.index import Indice

RAIZ = Path(__file__).resolve().parent.parent
DOC = RAIZ / "docs" / "RESULTADOS.md"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repetir", type=int, default=1, help="repeticoes do gabarito (mede cache)")
    parser.add_argument("--json", action="store_true", help="imprime o resultado em JSON")
    args = parser.parse_args(argv)

    artigos = carregar()
    comeco = time.perf_counter()
    indice = Indice(artigos)
    tempo_indice = time.perf_counter() - comeco

    calibracao = calibrar_limiar(indice)
    cache = CacheSemantico()
    resultado = avaliar_completo(
        indice, limiar=calibracao["limiar"], cache=cache, repetir=args.repetir
    )
    resultado["indice"] = {
        "artigos": len(artigos),
        "trechos": len(indice.trechos),
        "tempo_construcao_ms": round(tempo_indice * 1000, 1),
        "memoria_idf_termos": len(indice.idf),
    }

    if args.json:
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
    else:
        print("artigos: %d | trechos: %d | indice montado em %.1f ms"
              % (len(artigos), len(indice.trechos), tempo_indice * 1000))
        print("limiar calibrado: %.1f (retem %d/%d boas, abste %d/%d negativas)"
              % (calibracao["limiar"], calibracao["retidos"], calibracao["total_positivas"],
                 calibracao["abstidos"], calibracao["total_negativas"]))
        print("hit@1 %.1f%% | hit@3 %.1f%% | MRR %.3f | citacao %.1f%% | abstencao %.1f%%"
              % (100 * resultado["hit@1"], 100 * resultado["hit@3"], resultado["mrr"],
                 100 * resultado["citacao_correta"], 100 * resultado["abstencao"]))
        print("latencia p50 %.2f ms | p95 %.2f ms | cache %s"
              % (resultado["latencia_ms"]["p50"], resultado["latencia_ms"]["p95"], resultado["cache"]))

    DOC.parent.mkdir(parents=True, exist_ok=True)
    conteudo = [
        "# Resultados medidos",
        "",
        "Gerado por `python -m scripts.benchmark` em %s." % time.strftime("%Y-%m-%d %H:%M"),
        "",
        "Corpus: **%d artigos**, **%d trechos**, indice BM25 montado em **%.1f ms**."
        % (len(artigos), len(indice.trechos), tempo_indice * 1000),
        "",
        formatar_markdown(resultado, calibracao),
        "### O que cada numero significa",
        "",
        "- **hit@1 / hit@3**: o artigo certo veio em 1o / entre os 3 primeiros. "
        "Gabarito conferido lendo o texto dentro do corpus.",
        "- **MRR**: media do inverso da posicao. 1,0 = sempre em primeiro.",
        "- **citacao correta**: a resposta textual cita o numero do artigo recuperado.",
        "- **abstencao**: pergunta fora do CTB virou \"nao encontrei\" em vez de artigo aleatorio.",
        "- **latencia**: mede busca + montagem da resposta, sem rede (o LLM opcional nao entra).",
        "- **custo**: apenas tokens de contexto x preco de referencia; nao inclui a pergunta.",
        "",
    ]
    DOC.write_text("\n".join(conteudo), encoding="utf-8")
    print("escrito:", DOC)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
