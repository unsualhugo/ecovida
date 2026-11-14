import os, tempfile
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tempfile.mkdtemp(), "t.db")
os.environ["COORD_EMAIL"], os.environ["COORD_SENHA"] = "maria@ecovida.org", "maria12345"
from fastapi.testclient import TestClient
import main

COLETA = {"material": "plástico", "volume_kg": 5, "endereco": "Rua A, 10"}

def auth(t): return {"Authorization": "Bearer " + t}

def test_fluxo_completo():
    with TestClient(main.app) as c:
        g = c.post("/api/cadastro", json={"nome": "Victor", "email": "v@x.com", "senha": "12345678"})
        assert g.status_code == 201 and g.json()["perfil"] == "gerador"
        h = auth(g.json()["token"])
        assert c.post("/api/cadastro", json={"nome": "Victor", "email": "v@x.com", "senha": "12345678"}).status_code == 409
        r = c.post("/api/coletas", json=COLETA, headers=h); assert r.status_code == 201
        assert c.patch(f"/api/coletas/{r.json()['id']}/status", json={"status": "agendada"}, headers=h).status_code == 403
        m = c.post("/api/login", json={"email": "maria@ecovida.org", "senha": "maria12345"}).json()
        assert m["perfil"] == "coordenadora"
        hm = auth(m["token"])
        assert c.patch(f"/api/coletas/{r.json()['id']}/status", json={"status": "coletada"}, headers=hm).json()["status"] == "coletada"
        assert len(c.get("/api/coletas", headers=hm).json()) == 1

def test_validacao_e_seguranca():
    with TestClient(main.app) as c:
        assert c.post("/api/login", json={"email": "a@b.com", "senha": "errada123"}).status_code == 401
        assert c.get("/api/coletas").status_code in (401, 403)
        t = c.post("/api/login", json={"email": "maria@ecovida.org", "senha": "maria12345"}).json()["token"]
        assert c.post("/api/coletas", json={**COLETA, "volume_kg": -1}, headers=auth(t)).status_code == 422
        assert c.post("/api/coletas", json={**COLETA, "material": "lixo"}, headers=auth(t)).status_code == 422
