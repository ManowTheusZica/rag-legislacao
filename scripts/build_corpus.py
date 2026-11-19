"""Baixa/converte o CTB em artigos estruturados (JSONL).

Uso: python scripts/build_corpus.py [caminho_do_pdf]
Se o PDF nao existir, baixa do espelho publico da Prefeitura de Goiania.
"""
from __future__ import annotations

import json
import logging
import re
import sys
import urllib.request
from pathlib import Path

logging.getLogger("pypdf").setLevel(logging.ERROR)

URL_PDF = "https://www.goiania.go.gov.br/download/smt/CTB_Completo.pdf"
RAIZ = Path(__file__).resolve().parent.parent
PDF_PADRAO = RAIZ / "data" / "CTB_Completo.pdf"
SAIDA = RAIZ / "data" / "ctb_artigos.jsonl"

ARTIGO_RE = re.compile(r"(?:^|\n)\s*Art\.\s*(\d+)\s*[ºo°]?\s*[-–.]?\s*", re.MULTILINE)
TITULO_RE = re.compile(r"\n\s*((?:CAPÍTULO|CAPITULO|SEÇÃO|SECAO|TÍTULO|TITULO)[^\n]{0,120})")


def baixar(destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    print("baixando CTB de %s" % URL_PDF)
    requisicao = urllib.request.Request(URL_PDF, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(requisicao, timeout=120) as resposta:
        destino.write_bytes(resposta.read())
    print("salvo em %s (%d KB)" % (destino, destino.stat().st_size // 1024))


def texto_do_pdf(caminho: Path) -> str:
    from pypdf import PdfReader

    leitor = PdfReader(str(caminho))
    return "\n".join((pagina.extract_text() or "") for pagina in leitor.pages)


def limpar(texto: str) -> str:
    texto = texto.replace("\u00ad", "")
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n{2,}", "\n", texto)
    return texto.strip()


def dividir_artigos(texto: str) -> list[dict]:
    marcas = list(ARTIGO_RE.finditer(texto))
    artigos: list[dict] = []
    for indice, marca in enumerate(marcas):
        fim = marcas[indice + 1].start() if indice + 1 < len(marcas) else len(texto)
        corpo = limpar(texto[marca.end() : fim])
        if len(corpo) < 40:
            continue
        anterior = texto[: marca.start()][-400:]
        titulos = TITULO_RE.findall(anterior)
        artigos.append(
            {
                "artigo": int(marca.group(1)),
                "capitulo": limpar(titulos[-1]) if titulos else "",
                "texto": corpo[:4000],
            }
        )
    return artigos


def main() -> int:
    caminho = Path(sys.argv[1]) if len(sys.argv) > 1 else PDF_PADRAO
    if not caminho.exists():
        baixar(caminho)

    artigos = dividir_artigos(texto_do_pdf(caminho))
    unicos = {}
    for artigo in artigos:
        unicos.setdefault(artigo["artigo"], artigo)

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    with SAIDA.open("w", encoding="utf-8") as arquivo:
        for numero in sorted(unicos):
            arquivo.write(json.dumps(unicos[numero], ensure_ascii=False) + "\n")

    print("artigos extraidos: %d (unicos: %d)" % (len(artigos), len(unicos)))
    print("arquivo: %s (%d KB)" % (SAIDA, SAIDA.stat().st_size // 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())
