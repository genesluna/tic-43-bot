"""Configurações do chatbot carregadas do ambiente."""

import os
import threading
from dotenv import load_dotenv

load_dotenv()

# Limite máximo de caracteres por mensagem armazenada/enviada à API.
# Diferente de MAX_MESSAGE_LENGTH (limite de entrada do usuário para UX).
MAX_MESSAGE_CONTENT_SIZE = 100_000

__all__ = ["Config", "ConfigurationError", "config", "MAX_MESSAGE_CONTENT_SIZE"]


class ConfigurationError(Exception):
    """Erro de configuração do chatbot."""


class _ThreadSafeCachedProperty:
    """Descriptor que implementa cached_property com thread-safety.

    Usa um lock para garantir que a avaliação inicial seja atômica,
    evitando race conditions quando múltiplas threads acessam a
    propriedade pela primeira vez simultaneamente.
    """

    def __init__(self, func):
        self.func = func
        self.attr_name = None
        self.lock = threading.Lock()

    def __set_name__(self, owner, name):
        self.attr_name = name

    def __get__(self, instance, owner=None):
        if instance is None:
            return self

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
    MODEL_COMMANDS: tuple[str, ...] = ("/modelo",)
    LOAD_COMMANDS: tuple[str, ...] = ("/carregar", "/load")
    LIST_COMMANDS: tuple[str, ...] = ("/listar", "/list")
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
        return self._get_int_env("MAX_MESSAGE_LENGTH", 10000)

    @_ThreadSafeCachedProperty
    def MAX_HISTORY_SIZE(self) -> int:
        """Número máximo de pares de mensagens (usuário + assistente) a manter.

        O histórico mantém o system prompt + até MAX_HISTORY_SIZE * 2 mensagens
        individuais, garantindo que pares completos de conversa sejam preservados.
        """
        return self._get_int_env("MAX_HISTORY_SIZE", 25)

    @_ThreadSafeCachedProperty
    def HISTORY_DIR(self) -> str:
        return os.getenv("HISTORY_DIR", "./history")

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

    def _get_int_env(self, name: str, default: int) -> int:
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
