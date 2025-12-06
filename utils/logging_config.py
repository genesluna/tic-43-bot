"""Configuração de logging estruturado para o chatbot."""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

__all__ = ["StructuredFormatter", "ConsoleFormatter", "setup_logging"]


class StructuredFormatter(logging.Formatter):
    """Formatter que produz logs em formato JSON estruturado."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        if hasattr(record, "extra_data"):
            log_data["data"] = record.extra_data

        return json.dumps(log_data, ensure_ascii=False)


class ConsoleFormatter(logging.Formatter):
    """Formatter colorido para console (desenvolvimento)."""

    COLORS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[35m",
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        timestamp = datetime.now().strftime("%H:%M:%S")
        return (
            f"{color}[{timestamp}] {record.levelname:<8}{self.RESET} "
            f"{record.name}: {record.getMessage()}"
        )


def setup_logging(
    log_level: str | None = None,
    log_file: str | None = None,
    log_format: str | None = None
) -> None:
    """Configura o sistema de logging.

    Args:
        log_level: Nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL).
                   Se None, usa variável de ambiente LOG_LEVEL ou WARNING.
        log_file: Caminho do arquivo de log. Se None, usa LOG_FILE do ambiente.
        log_format: Formato do log ('console' ou 'json').
                    Se None, usa LOG_FORMAT do ambiente ou 'console'.

    Note:
        Parâmetros explícitos têm precedência sobre variáveis de ambiente.
        Isso evita mutação de os.environ e é thread-safe.
    """
    # Track if logging was explicitly requested (param or env var)
    log_level_requested = log_level is not None or os.getenv("LOG_LEVEL") is not None

    log_level = (log_level or os.getenv("LOG_LEVEL", "WARNING")).upper()
    log_format = (log_format or os.getenv("LOG_FORMAT", "console")).lower()
    log_file = log_file if log_file is not None else os.getenv("LOG_FILE", "")

    numeric_level = getattr(logging, log_level, logging.WARNING)

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    if log_format == "json":
        formatter = StructuredFormatter()
    else:
        formatter = ConsoleFormatter()

    # Only add console handler if logging was explicitly requested
    if log_level_requested:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(numeric_level)
        root_logger.addHandler(console_handler)

    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(StructuredFormatter())
        file_handler.setLevel(numeric_level)
        root_logger.addHandler(file_handler)

    if not root_logger.handlers:
        root_logger.addHandler(logging.NullHandler())

    active_handlers = [h for h in root_logger.handlers if not isinstance(h, logging.NullHandler)]
    if active_handlers:
        logger = logging.getLogger(__name__)
        logger.info(
            "Logging configurado: level=%s, format=%s, file=%s",
            log_level, log_format, log_file or 'none'
        )


