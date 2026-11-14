# EcoVida Local

PWA de gestão de coleta seletiva: moradores pedem recolhimento de recicláveis e a coordenadora acompanha e atualiza o status. Backend FastAPI + PostgreSQL, autenticação JWT com bcrypt, frontend estático acessível (WCAG AA).

## Rodar localmente
```
pip install -r requirements.txt
COORD_EMAIL=maria@ecovida.org COORD_SENHA=maria12345 uvicorn main:app --port 8000
```
No PowerShell, defina as variáveis com `$env:NOME="valor"` antes do uvicorn. Abra http://localhost:8000 (não abra o index.html direto do disco). Sem DATABASE_URL o app usa SQLite local, só para teste.

## Variáveis de ambiente
Veja `.env.example`. Em produção use PostgreSQL em `DATABASE_URL`, um `JWT_SECRET` longo e aleatório e uma senha forte para a coordenadora.

## Testes
```
pip install pytest httpx
pytest
```

## Estrutura
`main.py` API e regras de acesso; `static/` PWA (login, pedido de coleta, painel); `roteiro_teste.md` roteiro do teste de usabilidade de 20/11/2026.

## Endpoints
POST /api/cadastro, POST /api/login, POST /api/coletas, GET /api/coletas, PATCH /api/coletas/{id}/status (só coordenadora).
