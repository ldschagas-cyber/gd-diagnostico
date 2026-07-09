"""Serviço de cache para respostas de IA (Fase 0).

Usa Redis quando disponível; caso contrário, cai para cache em memória
(dicionário simples) — útil em desenvolvimento sem Redis rodando.

O cache de diagnósticos é invalidado por evento (nova importação de CT-es)
e também por TTL, garantindo que respostas caras de IA sejam reaproveitadas.
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Cache híbrido: Redis se disponível, senão memória local."""

    def __init__(self) -> None:
        self._redis = None
        self._memoria: dict[str, tuple[float, str]] = {}
        self._tentar_conectar_redis()

    def _tentar_conectar_redis(self) -> None:
        try:
            import redis
            self._redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
            self._redis.ping()
            logger.info("Cache usando Redis.")
        except Exception as e:  # noqa: BLE001
            self._redis = None
            logger.info("Redis indisponível (%s). Cache em memória local.", e)

    def gerar_chave(self, *partes: Any) -> str:
        """Gera uma chave de cache determinística a partir de partes."""
        bruto = ":".join(str(p) for p in partes)
        return "gdai:" + hashlib.sha256(bruto.encode()).hexdigest()[:24]

    def get(self, chave: str) -> Optional[Any]:
        if self._redis:
            try:
                val = self._redis.get(chave)
                return json.loads(val) if val else None
            except Exception:  # noqa: BLE001
                return None
        # memória
        item = self._memoria.get(chave)
        if not item:
            return None
        expira, val = item
        if time.time() > expira:
            self._memoria.pop(chave, None)
            return None
        return json.loads(val)

    def set(self, chave: str, valor: Any, ttl: int = None) -> None:
        ttl = ttl or settings.AI_CACHE_TTL
        payload = json.dumps(valor, ensure_ascii=False, default=str)
        if self._redis:
            try:
                self._redis.setex(chave, ttl, payload)
                return
            except Exception:  # noqa: BLE001
                pass
        self._memoria[chave] = (time.time() + ttl, payload)

    def invalidar(self, padrao: str) -> None:
        """Invalida chaves que correspondem a um padrão (ex.: empresa)."""
        if self._redis:
            try:
                for k in self._redis.scan_iter(f"*{padrao}*"):
                    self._redis.delete(k)
                return
            except Exception:  # noqa: BLE001
                pass
        for k in list(self._memoria.keys()):
            if padrao in k:
                self._memoria.pop(k, None)


_cache: Optional[CacheService] = None


def get_cache() -> CacheService:
    global _cache
    if _cache is None:
        _cache = CacheService()
    return _cache
