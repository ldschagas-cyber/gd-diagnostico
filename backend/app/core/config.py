"""Configurações da aplicação carregadas a partir de variáveis de ambiente."""
from functools import lru_cache
from typing import Annotated, List

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Ambiente
    ENVIRONMENT: str = "development"          # development | production

    # Aplicação
    PROJECT_NAME: str = "GD Diagnóstico Logístico"
    API_V1_PREFIX: str = "/api/v1"
    VERSION: str = "6.17.0"
    DEBUG: bool = True

    # Banco de dados — SQLite (dev local) ou PostgreSQL (Docker/produção)
    DATABASE_URL: str = "sqlite:///./gd_frete.db"

    # Segurança / JWT
    SECRET_KEY: str = "troque-esta-chave-em-producao-use-openssl-rand-hex-32"
    ALGORITHM: str = "HS256"
    # R-05/R-06: access token curto reduz a janela de abuso de um token vazado.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30          # 30 min (antes: 8h)
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7             # refresh token de longa duração

    # CORS
    # NoDecode: impede o pydantic-settings de tentar json.loads() na variável de
    # ambiente antes do validator. Assim aceitamos tanto lista JSON quanto texto
    # separado por vírgula no .env, sem quebrar a subida da aplicação.
    BACKEND_CORS_ORIGINS: Annotated[List[str], NoDecode] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost",
        "http://localhost:8080",
    ]

    # Usuário administrador inicial (seed)
    FIRST_SUPERUSER_EMAIL: str = "admin@gdconecta.com.br"
    FIRST_SUPERUSER_PASSWORD: str = "admin123"          # sobrescreva em produção via .env
    FIRST_SUPERUSER_NAME: str = "Administrador GD Conecta"

    # Importação (RNF006)
    MAX_CTE_BATCH: int = 10000

    # ─────────────── V4 — Inteligência Logística com IA ───────────────
    # Modo simulado: quando True, a IA retorna respostas mock (sem custo de API).
    # Plugue as chaves reais e mude para False para ativar os modelos.
    AI_SIMULATION_MODE: bool = True

    # Chaves de API (preencha no .env quando obtiver)
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # Modelos
    AI_MODEL_PRINCIPAL: str = "gpt-4.1"            # diagnóstico, relatórios, análise
    AI_MODEL_VOLUME: str = "claude-haiku-4-5"      # sumarizações, chat simples

    # Câmbio USD→BRL para registrar custo estimado em reais
    USD_TO_BRL: float = 5.90

    # Redis (Celery broker + cache) — sobe via Docker na Fase 0
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # Cache de diagnósticos (TTL em segundos; invalida também por evento)
    AI_CACHE_TTL: int = 60 * 60 * 24  # 24h

    # RAG / pgvector — só funciona em PostgreSQL
    RAG_ENABLED: bool = True
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIM: int = 1536

    @property
    def ai_ativa(self) -> bool:
        """True se há pelo menos uma chave configurada e o modo simulado está off."""
        return not self.AI_SIMULATION_MODE and bool(
            self.OPENAI_API_KEY or self.ANTHROPIC_API_KEY
        )

    @property
    def rag_disponivel(self) -> bool:
        """RAG exige PostgreSQL (pgvector). Em SQLite fica desabilitado."""
        return self.RAG_ENABLED and self.DATABASE_URL.startswith("postgresql")

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        """Aceita a lista de origens em qualquer formato comum, sem quebrar:
        - lista JSON:  ["http://a","http://b"]
        - vírgula:     http://a,http://b
        - já uma lista Python (valor padrão)
        - vazio/None:  vira lista vazia
        """
        if v is None or v == "":
            return []
        if isinstance(v, str):
            s = v.strip()
            if s.startswith("["):
                import json
                try:
                    return json.loads(s)
                except Exception:  # noqa: BLE001 — cai para o split por vírgula
                    pass
            return [item.strip() for item in s.split(",") if item.strip()]
        return v

    # Valores inseguros que NÃO podem ir para produção (R-02).
    _SECRET_DEFAULT = "troque-esta-chave-em-producao-use-openssl-rand-hex-32"
    _SENHAS_FRACAS = {"admin123", "Admin@123456", "changeme", "123456"}

    @model_validator(mode="after")
    def _validar_seguranca_producao(self):
        """Falha a inicialização em produção se os segredos forem inseguros (R-02)."""
        if self.is_production:
            problemas = []
            if not self.SECRET_KEY or self.SECRET_KEY == self._SECRET_DEFAULT:
                problemas.append("SECRET_KEY usa o valor padrão; gere uma única com 'openssl rand -hex 32'.")
            if len(self.SECRET_KEY) < 32:
                problemas.append("SECRET_KEY deve ter ao menos 32 caracteres.")
            if self.FIRST_SUPERUSER_PASSWORD in self._SENHAS_FRACAS:
                problemas.append("FIRST_SUPERUSER_PASSWORD é fraca/padrão; defina uma senha forte no .env.")
            if self.DEBUG:
                problemas.append("DEBUG deve ser False em produção.")
            if problemas:
                raise ValueError(
                    "Configuração insegura para produção:\n- " + "\n- ".join(problemas)
                )
        return self

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def secret_key_insegura(self) -> bool:
        """True se a SECRET_KEY ainda é o placeholder (usado para avisar em dev)."""
        return self.SECRET_KEY == self._SECRET_DEFAULT

    @property
    def is_postgres(self) -> bool:
        return self.DATABASE_URL.startswith("postgresql")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
