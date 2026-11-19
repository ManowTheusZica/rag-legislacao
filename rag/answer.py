"""Resposta extrativa com citacao obrigatoria do artigo.

Sem LLM por padrao: devolve o trecho do artigo mais relevante.
Se LLM_BASE_URL estiver definido, usa um endpoint compativel com OpenAI
para redigir a resposta — mas sempre citando os artigos recuperados.
"""
from __future__ import annotations

import json
import os
import urllib.request

from .index import Indice

SEM_RESPOSTA = (
    "Nao encontrei artigo do CTB que responda isso. Reformule usando termos da lei "
    "(por exemplo: 'cinto de seguranca', 'ultrapassagem', 'estacionar em local proibido')."
)


def _llm(pergunta: str, trechos: list[dict]) -> str | None:
    base = os.getenv("LLM_BASE_URL")
    chave = os.getenv("LLM_API_KEY")
    modelo = os.getenv("LLM_MODEL", "gpt-4o-mini")
    if not base or not chave:
        return None

    contexto = "\n\n".join(
        "Art. %d (%.0f%% de relevancia): %s" % (t["artigo"], t["score"] * 100, t["texto"][:900])
        for t in trechos
    )
    corpo = {
        "model": modelo,
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Voce responde sobre o Codigo de Transito Brasileiro. Use SOMENTE os "
                    "artigos fornecidos. Cite o numero do artigo em toda afirmacao. "
                    "Se os artigos nao responderem, diga que nao encontrou."
                ),
            },
            {"role": "user", "content": "Artigos:\n%s\n\nPergunta: %s" % (contexto, pergunta)},
        ],
    }
    requisicao = urllib.request.Request(
        base.rstrip("/") + "/chat/completions",
        data=json.dumps(corpo).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + chave},
    )
    try:
        with urllib.request.urlopen(requisicao, timeout=40) as resposta:
            dados = json.loads(resposta.read().decode())
        return dados["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


def responder(indice: Indice, pergunta: str, limite: int = 3) -> dict:
    achados = indice.consultar(pergunta, limite)
    if not achados:
        return {"resposta": SEM_RESPOSTA, "artigos": [], "fonte": "extrativo"}

    trechos = [
        {"artigo": documento["artigo"], "score": score, "texto": documento["texto"],
         "capitulo": documento.get("capitulo", "")}
        for score, documento in achados
    ]

    texto_llm = _llm(pergunta, trechos)
    if texto_llm:
        return {"resposta": texto_llm, "artigos": trechos, "fonte": "llm+rag"}

    principal = trechos[0]
    resposta = "Art. %d do CTB: %s" % (principal["artigo"], principal["texto"][:700])
    if len(trechos) > 1:
        resposta += "\n\nOutros artigos relacionados: " + ", ".join(
            "Art. %d" % t["artigo"] for t in trechos[1:]
        )
    return {"resposta": resposta, "artigos": trechos, "fonte": "extrativo"}
