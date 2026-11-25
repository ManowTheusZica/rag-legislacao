# Resultados medidos

Gerado por `python -m scripts.benchmark` em 2026-11-25 19:06.

Corpus: **324 artigos**, **726 trechos**, indice BM25 montado em **70.4 ms**.

## Resultado do benchmark

| metrica | valor |
|---|---|
| perguntas do gabarito | 18 |
| hit@1 | 83.3% |
| hit@3 | 100.0% |
| MRR | 0.907 |
| citacao correta | 100.0% |
| abstencao em pergunta fora do escopo | 87.5% |
| latencia p50 | 1.39 ms |
| latencia p95 | 2.17 ms |
| tokens de contexto por pergunta | 189 |
| custo por pergunta | US$ 0.000028 |
| custo de 10 mil perguntas | US$ 0.28 |

### Calibracao do limiar de abstencao

| limiar | perguntas boas retidas | negativas abstidas |
|---|---|---|
| 6.0 (escolhido) | 18/18 | 7/8 |

Menor score entre perguntas boas: 8.498. Maior score entre perguntas fora do escopo: 11.683.

### O que cada numero significa

- **hit@1 / hit@3**: o artigo certo veio em 1o / entre os 3 primeiros. Gabarito conferido lendo o texto dentro do corpus.
- **MRR**: media do inverso da posicao. 1,0 = sempre em primeiro.
- **citacao correta**: a resposta textual cita o numero do artigo recuperado.
- **abstencao**: pergunta fora do CTB virou "nao encontrei" em vez de artigo aleatorio.
- **latencia**: mede busca + montagem da resposta, sem rede (o LLM opcional nao entra).
- **custo**: apenas tokens de contexto x preco de referencia; nao inclui a pergunta.

### Cache semantico

Medido rodando o gabarito 3x com o mesmo cache (`--repetir 3`):

| metrica | sem cache | com cache (3a rodada) |
|---|---|---|
| latencia p50 | 1,32 ms | **0,03 ms** |
| acertos de cache | 0 | 36 de 54 (66,7%) |
| hit@1 | 83,3% | 83,3% (nao muda) |

O cache casa por Jaccard dos radicais (limiar 0,85): "dirigir sem cnh" e
"penalidade para dirigir sem possuir cnh" caem na mesma entrada; pergunta de
outro assunto nao. Reduz latencia em pergunta repetida e, com LLM ligado, corta
custo proporcionalmente.
