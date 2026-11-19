# RAG sobre o Codigo de Transito Brasileiro

Sistema de perguntas e respostas sobre a Lei 9.503/1997 (CTB). Toda resposta vem com
o numero do artigo que a sustenta. Busca propria (BM25), sem serviço externo, com
avaliacao medida em gabarito verificado.

## Rodando

```bash
pip install -r requirements.txt
python scripts/build_corpus.py          # baixa o CTB e gera data/ctb_artigos.jsonl
uvicorn app:app --port 8020             # http://localhost:8020
```

## Numeros reais

- Corpus: **324 artigos** unicos, quebrados em **726 trechos** de ~320 caracteres
- Gabarito: **18 perguntas**, cada resposta conferida lendo o texto do artigo
- Resultado da busca: **hit@1 = 83,3%**, **hit@3 = 100%**, **MRR = 0,907**

```
python -c "from rag.corpus import carregar; from rag.index import Indice; \
from rag.evaluate import avaliar; print(avaliar(Indice(carregar())))"
```

## Exemplo

Pergunta: `pode transportar crianca na motocicleta`

Resposta: Art. 244 do CTB - "Conduzir motocicleta, motoneta e ciclomotor: ... transportando
crianca menor de sete anos ou que nao possa cuidar de si mesma..." com o trecho e o score.

## Como funciona

1. `scripts/build_corpus.py` extrai o texto do PDF, corta por `Art. N` e guarda JSONL
   com numero do artigo + capitulo + texto.
2. `rag/index.py` quebra cada artigo em trechos (caput, paragrafos, incisos) e indexa
   com **BM25** (k1=1.5, b=0.75).
3. Radical leve de portugues: sem acento, plural para singular, corte de sufixo verbal.
   Assim `dirige`, `dirigir` e `dirigindo` caem no mesmo token.
4. `rag/answer.py` devolve resposta extrativa sempre citando o artigo. Se `LLM_BASE_URL`
   e `LLM_API_KEY` estiverem definidos, usa um endpoint compativel com OpenAI para
   redigir - mas so com os artigos recuperados no contexto (RAG de verdade, sem alucinar).
5. `rag/evaluate.py` mede hit@1, hit@3 e MRR no gabarito.

## Decisoes que valem explicar em entrevista

- **Trecho, nao artigo inteiro**: indexar o artigo completo diluia o score e derrubava
  o hit@1 para 6,7%. Quebrar em trechos e ranquear por trecho subiu para 83,3%.
- **BM25 em vez de TF-IDF**: BM25 satura frequencia e penaliza documento longo, o que
  importa quando um artigo tem 20 incisos e outro tem uma linha.
- **Radical em vez de embedding**: embedding custa API, nao roda offline e nao explica
  por que acertou. BM25 + radical roda em 40 ms, e o resultado e auditavel.
- **Gabarito verificado**: cada par pergunta/artigo foi conferido no texto do corpus.
  Gabarito chutado produz metrica bonita e falsa.
- **Sem resposta honesta**: quando nada passa do corte, o sistema diz que nao encontrou
  em vez de inventar artigo.

## Limitacoes

- Perguntas com sinonimos distantes ("bebida" vs "alcool") ainda dependem do vocabulario
  da lei; um dicionario de sinonimos ou embedding resolveria.
- O corpus e o texto consolidado do CTB; alteracoes recentes podem nao estar nele -
  rode `scripts/build_corpus.py` com um PDF atualizado.
- A resposta extrativa corta em 700 caracteres; para respostas longas, configure o LLM.
