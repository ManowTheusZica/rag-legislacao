# RAG sobre o Codigo de Transito Brasileiro

![CI](https://github.com/ManowTheusZica/rag-legislacao/actions/workflows/ci.yml/badge.svg) ![Python](https://img.shields.io/badge/python-3.12+-3776AB?logo=python&logoColor=white)


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

Medidos por `python -m scripts.benchmark` (detalhe em [docs/RESULTADOS.md](docs/RESULTADOS.md)):

- Corpus: **324 artigos** unicos, **726 trechos**, indice montado em **~70 ms**
- Gabarito: **18 perguntas** verificadas + **8 perguntas fora do escopo**
- Busca: **hit@1 = 83,3%**, **hit@3 = 100%**, **MRR = 0,907**
- **Citacao correta em 100%** das respostas (a resposta cita o artigo recuperado)
- **Abstencao = 87,5%** nas perguntas fora do CTB (limiar calibrado em 6,0)
- Latencia p50 **1,32 ms** / p95 **1,88 ms** (sem rede)
- Custo estimado: **US$ 0,000028 por pergunta** (~US$ 0,28 por 10 mil), so contexto
- Cache semantico: p50 cai para **0,03 ms** em pergunta repetida (66,7% de acerto)

```bash
python -m scripts.benchmark           # mede e reescreve docs/RESULTADOS.md
python -m scripts.benchmark --json    # so' imprime
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
5. `rag/avaliacao.py` mede hit@1, hit@3, MRR, **citacao**, **abstencao**, latencia e
   custo; `calibrar_limiar()` escolhe o corte de score com dado (18 boas x 8 fora do escopo).
6. `rag/cache.py` guarda resposta por conjunto de radicais (Jaccard >= 0,85): pega
   reformulacao da mesma pergunta e nao serve resposta de outro assunto.

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
  em vez de inventar artigo. O corte nao foi chutado: `calibrar_limiar()` varre 11
  limiares e escolhe o que retem as 18 boas e abste o maximo de negativas (6,0).
- **Cache por radicais, nao por string**: normalizar acento/plural/sufixo faz
  "dirigir sem cnh" e "penalidade para dirigir sem possuir cnh" virarem a mesma chave;
  Jaccard 0,85 impede que "sinalizacao de rodovia" pegue carona em "cinto de seguranca".
- **Custo medido, nao estimado no chute**: tokens de contexto contados por pergunta
  (189) x preco de referencia (US$ 0,15/1M) = US$ 0,28 por 10 mil perguntas. E' o
  numero que justifica ou nao ligar o LLM.

## Limitacoes

- Perguntas com sinonimos distantes ("bebida" vs "alcool") ainda dependem do vocabulario
  da lei; um dicionario de sinonimos ou embedding resolveria.
- O corpus e o texto consolidado do CTB; alteracoes recentes podem nao estar nele -
  rode `scripts/build_corpus.py` com um PDF atualizado.
- A resposta extrativa corta em 700 caracteres; para respostas longas, configure o LLM.
- Abstencao de 87,5% significa que 1 das 8 perguntas fora do escopo ainda recebe artigo:
  o score BM25 nao tem escala absoluta, entao o limiar precisa ser revalidado quando o
  corpus mudar. Esta documentado de proposito, em vez de esconder o falso positivo.
- Cache em memoria: reiniciar o processo limpa. Para varias replicas, trocar por Redis
  mantendo a mesma chave (frozenset de radicais).
