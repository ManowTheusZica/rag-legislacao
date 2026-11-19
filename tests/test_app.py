from fastapi.testclient import TestClient

import app as servico


def test_api_responde(indice, monkeypatch):
    monkeypatch.setattr(servico, "indice", lambda: indice)
    cliente = TestClient(servico.app)

    dados = cliente.get("/api/pergunta", params={"pergunta": "cinto de seguranca"}).json()
    assert dados["artigos"][0]["artigo"] == 65

    pagina = cliente.get("/", params={"pergunta": "cinto de seguranca"})
    assert pagina.status_code == 200
    assert "Art. 65" in pagina.text
