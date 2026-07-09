"""Configuração de logging — RNF002: todas as operações registradas em log."""
import logging
import sys

from app.core.config import settings


def setup_logging() -> None:
    level = logging.DEBUG if settings.DEBUG else logging.INFO
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root = logging.getLogger()
    root.setLevel(level)
    # Evita handlers duplicados em reload
    if not root.handlers:
        root.addHandler(handler)

    # Silencia logs de terceiros excessivamente verbosos em modo DEBUG.
    for ruidoso in ("python_multipart", "multipart"):
        logging.getLogger(ruidoso).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
