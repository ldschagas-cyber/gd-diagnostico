"""Configuração da sessão SQLAlchemy.

Suporta SQLite (desenvolvimento local) e PostgreSQL (Docker/produção).
A URL é configurada via variável de ambiente DATABASE_URL.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

# SQLite precisa de check_same_thread=False para rodar com threads do FastAPI.
# PostgreSQL não precisa e ignora esse parâmetro.
connect_args = (
    {"check_same_thread": False}
    if settings.DATABASE_URL.startswith("sqlite")
    else {}
)

# Pool settings: para PostgreSQL usa pool_size; SQLite ignora.
engine_kwargs = {
    "connect_args": connect_args,
    "pool_pre_ping": True,         # detecta conexões mortas antes de usar
    "echo": settings.DEBUG and not settings.is_production,
}

if settings.is_postgres:
    engine_kwargs["pool_size"] = 5
    engine_kwargs["max_overflow"] = 10
    engine_kwargs["pool_timeout"] = 30
    engine_kwargs["pool_recycle"] = 1800   # reconecta a cada 30min

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base declarativa para todos os modelos ORM."""
    pass


def get_db():
    """Dependency do FastAPI: fornece uma sessão por requisição."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
