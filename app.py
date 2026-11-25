"""Interface web: busca por pergunta no CTB."""
from __future__ import annotations

import os
from functools import lru_cache

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from rag.answer import responder
from rag.cache import CacheSemantico
from rag.corpus import carregar
from rag.index import Indice

app = FastAPI(title="RAG - Codigo de Transito Brasileiro")

# limiar calibrado em scripts/benchmark.py (docs/RESULTADOS.md)
LIMIAR = float(os.getenv("RAG_SCORE_MINIMO", "6.0"))
CACHE = CacheSemantico(limite=int(os.getenv("RAG_CACHE_ITENS", "512")))


@lru_cache(maxsize=1)
def indice() -> Indice:
    return Indice(carregar())


@app.get("/api/pergunta")
def api(pergunta: str):
    return responder(indice(), pergunta, score_minimo=LIMIAR, cache=CACHE)


@app.get("/api/cache")
def cache_stats():
    return CACHE.estatisticas()


@app.get("/", response_class=HTMLResponse)
def pagina(pergunta: str = ""):
    resultado = (
        responder(indice(), pergunta, score_minimo=LIMIAR, cache=CACHE)
        if pergunta.strip()
        else None
    )
    artigos = "".join(
        '<article><h3>Art. %d <span class="score">%.0f%%</span></h3>'
        "<p>%s</p></article>"
        % (t["artigo"], t["score"] * 100, t["texto"][:1200])
        for t in (resultado["artigos"] if resultado else [])
    )
    resposta = resultado["resposta"] if resultado else ""
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<title>CTB - perguntas e respostas</title>
<style>
 body{{font-family:system-ui,sans-serif;background:#0f172a;color:#e2e8f0;margin:0;padding:40px 20px}}
 .wrap{{max-width:820px;margin:0 auto}}
 h1{{font-size:24px;margin-bottom:6px}}
 .sub{{color:#94a3b8;margin-bottom:24px;font-size:14px}}
 form{{display:flex;gap:8px;margin-bottom:24px}}
 input{{flex:1;padding:14px 16px;border-radius:10px;border:1px solid #334155;
        background:#1e293b;color:#e2e8f0;font-size:15px}}
 button{{padding:14px 22px;border-radius:10px;border:0;background:#2563eb;color:#fff;
         font-size:15px;cursor:pointer}}
 .resposta{{background:#1e293b;border-left:4px solid #2563eb;padding:16px 18px;
            border-radius:8px;margin-bottom:20px;white-space:pre-wrap;line-height:1.55}}
 article{{background:#1e293b;padding:14px 16px;border-radius:10px;margin-bottom:12px}}
 article h3{{margin:0 0 8px;font-size:15px;color:#93c5fd}}
 article p{{margin:0;font-size:14px;color:#cbd5e1;line-height:1.5}}
 .score{{color:#64748b;font-weight:400;font-size:12px}}
 footer{{color:#64748b;font-size:12px;margin-top:24px}}
</style></head><body><div class="wrap">
<h1>Codigo de Transito Brasileiro</h1>
<div class="sub">Pergunte em portugues. A resposta vem sempre com o artigo que a sustenta.</div>
<form method="get"><input name="pergunta" placeholder="ex: pode transportar crianca na moto?"
 value="{pergunta}" autofocus><button>Perguntar</button></form>
<div class="resposta">{resposta or "Faca uma pergunta para comecar."}</div>
{artigos}
<footer>Corpus: Lei 9.503/1997 (CTB). Busca BM25 propria, sem servico externo. Limiar de abstencao calibrado com gabarito.</footer>
</div></body></html>"""
