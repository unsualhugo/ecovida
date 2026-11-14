"""EcoVida Local - MVP. Teste local: uvicorn main:app (usa SQLite). Produção: defina DATABASE_URL (PostgreSQL) e JWT_SECRET."""
import os, datetime as dt
from enum import Enum
import bcrypt, jwt
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from sqlalchemy import create_engine, String, Integer, Float, ForeignKey, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session

SECRET = os.environ.get("JWT_SECRET", "chave-local-de-teste-ecovida-2026-xyz")
engine = create_engine(os.environ.get("DATABASE_URL", "sqlite:///ecovida.db"), pool_pre_ping=True)
SessionLocal = sessionmaker(engine)

class Base(DeclarativeBase): pass

class Perfil(str, Enum):
    gerador = "gerador"
    coordenadora = "coordenadora"

class Status(str, Enum):
    pendente = "pendente"
    agendada = "agendada"
    coletada = "coletada"

class Material(str, Enum):
    papel = "papel"; plastico = "plástico"; vidro = "vidro"; metal = "metal"; outro = "outro"

class User(Base):
    __tablename__ = "usuarios"
    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    senha_hash: Mapped[str] = mapped_column(String(80))
    perfil: Mapped[str] = mapped_column(String(20), default=Perfil.gerador.value)

class Coleta(Base):
    __tablename__ = "coletas"
    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    material: Mapped[str] = mapped_column(String(20))
    volume_kg: Mapped[float] = mapped_column(Float)
    endereco: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default=Status.pendente.value)
    criado_em: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

Base.metadata.create_all(engine)

class Cadastro(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    email: EmailStr
    senha: str = Field(min_length=8, max_length=72)

class Login(BaseModel):
    email: EmailStr
    senha: str

class ColetaIn(BaseModel):
    material: Material
    volume_kg: float = Field(gt=0, le=1000)
    endereco: str = Field(min_length=5, max_length=200)

class ColetaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; material: str; volume_kg: float; endereco: str; status: str
    criado_em: dt.datetime

class StatusIn(BaseModel):
    status: Status

def db():
    with SessionLocal() as s:
        yield s

def hash_(p: str) -> str: return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()

def token(u: User) -> str:
    exp = dt.datetime.utcnow() + dt.timedelta(hours=12)
    return jwt.encode({"sub": str(u.id), "perfil": u.perfil, "exp": exp}, SECRET, "HS256")

bearer = HTTPBearer()
def atual(c: HTTPAuthorizationCredentials = Depends(bearer), s: Session = Depends(db)) -> User:
    try:
        uid = int(jwt.decode(c.credentials, SECRET, ["HS256"])["sub"])
    except Exception:
        raise HTTPException(401, "Sessão expirada. Entre novamente.")
    u = s.get(User, uid)
    if not u: raise HTTPException(401, "Usuário não encontrado.")
    return u

def so_coordenadora(u: User = Depends(atual)) -> User:
    if u.perfil != Perfil.coordenadora.value:
        raise HTTPException(403, "Apenas a coordenadora pode fazer isso.")
    return u

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(_):
    seed()
    yield

app = FastAPI(title="EcoVida Local", lifespan=lifespan)

def seed():
    """Cria a coordenadora a partir de variáveis de ambiente, se ainda não existir."""
    email, senha = os.environ.get("COORD_EMAIL"), os.environ.get("COORD_SENHA")
    if not (email and senha): return
    with SessionLocal() as s:
        if not s.query(User).filter_by(email=email).first():
            s.add(User(nome="Maria Helena dos Santos", email=email, senha_hash=hash_(senha),
                       perfil=Perfil.coordenadora.value)); s.commit()

def resposta_login(u: User): return {"token": token(u), "perfil": u.perfil, "nome": u.nome}

@app.post("/api/cadastro", status_code=201)
def cadastro(d: Cadastro, s: Session = Depends(db)):
    if s.query(User).filter_by(email=d.email.lower()).first():
        raise HTTPException(409, "Este e-mail já tem cadastro.")
    u = User(nome=d.nome, email=d.email.lower(), senha_hash=hash_(d.senha)); s.add(u); s.commit()
    return resposta_login(u)

@app.post("/api/login")
def login(d: Login, s: Session = Depends(db)):
    u = s.query(User).filter_by(email=d.email.lower()).first()
    if not u or not bcrypt.checkpw(d.senha.encode(), u.senha_hash.encode()):
        raise HTTPException(401, "E-mail ou senha incorretos.")
    return resposta_login(u)

@app.post("/api/coletas", response_model=ColetaOut, status_code=201)
def criar(d: ColetaIn, u: User = Depends(atual), s: Session = Depends(db)):
    c = Coleta(usuario_id=u.id, material=d.material.value, volume_kg=d.volume_kg, endereco=d.endereco)
    s.add(c); s.commit(); s.refresh(c); return c

@app.get("/api/coletas", response_model=list[ColetaOut])
def listar(u: User = Depends(atual), s: Session = Depends(db)):
    q = s.query(Coleta)
    if u.perfil != Perfil.coordenadora.value: q = q.filter_by(usuario_id=u.id)
    return q.order_by(Coleta.criado_em.desc()).limit(200).all()

@app.patch("/api/coletas/{cid}/status", response_model=ColetaOut)
def mudar_status(cid: int, d: StatusIn, _: User = Depends(so_coordenadora), s: Session = Depends(db)):
    c = s.get(Coleta, cid)
    if not c: raise HTTPException(404, "Solicitação não encontrada.")
    c.status = d.status.value; s.commit(); s.refresh(c); return c

app.mount("/", StaticFiles(directory="static", html=True), name="static")
