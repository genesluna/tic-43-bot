"""Configurações do chatbot carregadas do ambiente."""

import logging
import os
import threading
from pathlib import Path
from typing import Any, Callable, TypeVar
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

MAX_MESSAGE_CONTENT_SIZE = 100_000

MAX_MESSAGE_LENGTH_UPPER = 100_000
MAX_HISTORY_SIZE_UPPER = 500

__all__ = ["Config", "ConfigurationError", "config", "MAX_MESSAGE_CONTENT_SIZE"]


class ConfigurationError(Exception):
    """Erro de configuração do chatbot."""


_T = TypeVar("_T")


class _ThreadSafeCachedProperty:
    """Descriptor que implementa cached_property com thread-safety.

    Usa um lock para garantir que a avaliação inicial seja atômica,
    evitando race conditions quando múltiplas threads acessam a
    propriedade pela primeira vez simultaneamente.
    """

    def __init__(self, func: Callable[[Any], _T]) -> None:
        self.func: Callable[[Any], _T] = func
        self.attr_name: str | None = None
        self.lock: threading.Lock = threading.Lock()

    def __set_name__(self, owner: type, name: str) -> None:
        self.attr_name = name

    def __get__(self, instance: Any, owner: type | None = None) -> _T:
        if instance is None:
            return self  # type: ignore[return-value]

        try:
            return instance.__dict__[self.attr_name]
        except KeyError:
            pass

        with self.lock:
            try:
                return instance.__dict__[self.attr_name]
            except KeyError:
                value = self.func(instance)
                instance.__dict__[self.attr_name] = value
                return value


class Config:
    """Classe de configuração do chatbot com avaliação lazy e thread-safe.

    Usa _ThreadSafeCachedProperty para garantir que a avaliação inicial
    de cada propriedade seja atômica, evitando race conditions.
    """

    def __repr__(self) -> str:
        return f"Config(model={self.OPENROUTER_MODEL})"

    EXIT_COMMANDS: tuple[str, ...] = ("sair", "exit", "quit")
    CLEAR_COMMANDS: tuple[str, ...] = ("/limpar", "/clear")
    SAVE_COMMANDS: tuple[str, ...] = ("/salvar", "/save")
    HELP_COMMANDS: tuple[str, ...] = ("/ajuda", "/help")
    MODEL_COMMANDS: tuple[str, ...] = ("/modelo", "/model")
    LOAD_COMMANDS: tuple[str, ...] = ("/carregar", "/load")
    LIST_COMMANDS: tuple[str, ...] = ("/listar", "/list")
    STREAM_COMMANDS: tuple[str, ...] = ("/streaming", "/stream")
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1/chat/completions"

    @_ThreadSafeCachedProperty
    def OPENROUTER_API_KEY(self) -> str:
        return os.getenv("OPENROUTER_API_KEY", "")

    @_ThreadSafeCachedProperty
    def OPENROUTER_MODEL(self) -> str:
        return os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")

    @_ThreadSafeCachedProperty
    def SYSTEM_PROMPT(self) -> str:
        return os.getenv(
            "SYSTEM_PROMPT",
            "Você é um assistente virtual útil e amigável.",
        )

    @_ThreadSafeCachedProperty
    def RESPONSE_LANGUAGE(self) -> str:
        return os.getenv("RESPONSE_LANGUAGE", "português")

    @_ThreadSafeCachedProperty
    def RESPONSE_LENGTH(self) -> str:
        return os.getenv("RESPONSE_LENGTH", "conciso")

    @_ThreadSafeCachedProperty
    def RESPONSE_TONE(self) -> str:
        return os.getenv("RESPONSE_TONE", "amigável")

    @_ThreadSafeCachedProperty
    def RESPONSE_FORMAT(self) -> str:
        return os.getenv("RESPONSE_FORMAT", "markdown")

    @_ThreadSafeCachedProperty
    def MAX_MESSAGE_LENGTH(self) -> int:
        """Limite de caracteres para entrada do usuário no prompt.

        Este limite é para UX no input. O limite técnico para mensagens
        armazenadas/enviadas à API é definido por MAX_MESSAGE_CONTENT_SIZE.
        """
        return self._get_int_env("MAX_MESSAGE_LENGTH", 10000, MAX_MESSAGE_LENGTH_UPPER)

    @_ThreadSafeCachedProperty
    def MAX_HISTORY_SIZE(self) -> int:
        """Número máximo de pares de mensagens (usuário + assistente) a manter.

        O histórico mantém o system prompt + até MAX_HISTORY_SIZE * 2 mensagens
        individuais, garantindo que pares completos de conversa sejam preservados.
        """
        return self._get_int_env("MAX_HISTORY_SIZE", 25, MAX_HISTORY_SIZE_UPPER)

    @_ThreadSafeCachedProperty
    def HISTORY_DIR(self) -> str:
        """Diretório para salvar histórico de conversas.

        Valida que o caminho está dentro ou abaixo do diretório de trabalho
        para evitar escrita em locais não autorizados.
        """
        path = os.getenv("HISTORY_DIR", "./history")
        try:
            resolved = Path(path).resolve()
            cwd = Path.cwd().resolve()
            resolved.relative_to(cwd)
            return path
        except ValueError:
            logger.warning(
                "HISTORY_DIR '%s' fora do diretório do projeto, usando padrão",
                path
            )
            return "./history"

    @_ThreadSafeCachedProperty
    def STREAM_RESPONSE(self) -> bool:
        """Se True, mostra resposta em streaming. Se False, mostra spinner com tokens."""
        return os.getenv("STREAM_RESPONSE", "true").lower() in ("true", "1", "yes")

    @_ThreadSafeCachedProperty
    def LOG_LEVEL(self) -> str:
        return os.getenv("LOG_LEVEL", "WARNING")

    @_ThreadSafeCachedProperty
    def LOG_FORMAT(self) -> str:
        return os.getenv("LOG_FORMAT", "console")

    @_ThreadSafeCachedProperty
    def LOG_FILE(self) -> str:
        return os.getenv("LOG_FILE", "")

    @_ThreadSafeCachedProperty
    def HTTP_CONNECT_TIMEOUT(self) -> float:
        return self._get_float_env("HTTP_CONNECT_TIMEOUT", 10.0)

    @_ThreadSafeCachedProperty
    def HTTP_READ_TIMEOUT(self) -> float:
        return self._get_float_env("HTTP_READ_TIMEOUT", 90.0)

    @_ThreadSafeCachedProperty
    def HTTP_WRITE_TIMEOUT(self) -> float:
        return self._get_float_env("HTTP_WRITE_TIMEOUT", 10.0)

    @_ThreadSafeCachedProperty
    def HTTP_POOL_TIMEOUT(self) -> float:
        return self._get_float_env("HTTP_POOL_TIMEOUT", 10.0)

    def _get_float_env(self, name: str, default: float) -> float:
        """Obtém variável de ambiente como float positivo com validação."""
        raw_value = os.getenv(name, str(default))
        try:
            value = float(raw_value)
        except (ValueError, TypeError):
            raise ConfigurationError(
                f"{name} deve ser um número válido, recebido: '{raw_value}'"
            )
        if value <= 0:
            raise ConfigurationError(
                f"{name} deve ser um número positivo, recebido: '{value}'"
            )
        return value

    def _get_int_env(self, name: str, default: int, max_value: int | None = None) -> int:
        """Obtém variável de ambiente como inteiro positivo com validação."""
        raw_value = os.getenv(name, str(default))
        try:
            value = int(raw_value)
        except ValueError:
            raise ConfigurationError(
                f"{name} deve ser um número inteiro, recebido: '{raw_value}'"
            )
        if value <= 0:
            raise ConfigurationError(
                f"{name} deve ser um inteiro positivo, recebido: '{value}'"
            )
        if max_value is not None and value > max_value:
            logger.warning(
                "%s=%d excede máximo permitido (%d), usando limite",
                name, value, max_value
            )
            return max_value
        return value

    def validate(self) -> None:
        """Valida as configurações obrigatórias.

        Acessa todas as propriedades numéricas para validação antecipada.
        """
        if not self.OPENROUTER_API_KEY:
            raise ConfigurationError(
                "OPENROUTER_API_KEY não configurada.\n"
                "Configure no arquivo .env ou como variável de ambiente."
            )
        # Valida todas as configs numéricas antecipadamente
        _ = self.MAX_MESSAGE_LENGTH
        _ = self.MAX_HISTORY_SIZE
        _ = self.HTTP_CONNECT_TIMEOUT
        _ = self.HTTP_READ_TIMEOUT
        _ = self.HTTP_WRITE_TIMEOUT
        _ = self.HTTP_POOL_TIMEOUT


config = Config()
