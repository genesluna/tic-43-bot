"""Configurações do chatbot carregadas do ambiente."""

import os
from functools import cached_property
from dotenv import load_dotenv

load_dotenv()


class ConfigurationError(Exception):
    """Erro de configuração do chatbot."""


class Config:
    """Classe de configuração do chatbot com avaliação lazy."""

    EXIT_COMMANDS: tuple[str, ...] = ("sair", "exit", "quit")
    CLEAR_COMMANDS: tuple[str, ...] = ("/limpar", "/clear")
    SAVE_COMMANDS: tuple[str, ...] = ("/salvar", "/save")
    HELP_COMMANDS: tuple[str, ...] = ("/ajuda", "/help")
    MODEL_COMMANDS: tuple[str, ...] = ("/modelo",)
    LOAD_COMMANDS: tuple[str, ...] = ("/carregar", "/load")
    LIST_COMMANDS: tuple[str, ...] = ("/listar", "/list")
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1/chat/completions"

    @cached_property
    def OPENROUTER_API_KEY(self) -> str:
        return os.getenv("OPENROUTER_API_KEY", "")

    @cached_property
    def OPENROUTER_MODEL(self) -> str:
        return os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")

    @cached_property
    def SYSTEM_PROMPT(self) -> str:
        return os.getenv(
            "SYSTEM_PROMPT",
            "Você é um assistente virtual útil e amigável.",
        )

    @cached_property
    def RESPONSE_LANGUAGE(self) -> str:
        return os.getenv("RESPONSE_LANGUAGE", "português")

    @cached_property
    def RESPONSE_LENGTH(self) -> str:
        return os.getenv("RESPONSE_LENGTH", "conciso")

    @cached_property
    def RESPONSE_TONE(self) -> str:
        return os.getenv("RESPONSE_TONE", "amigável")

    @cached_property
    def RESPONSE_FORMAT(self) -> str:
        return os.getenv("RESPONSE_FORMAT", "markdown")

    @cached_property
    def MAX_MESSAGE_LENGTH(self) -> int:
        return self._get_int_env("MAX_MESSAGE_LENGTH", 10000)

    @cached_property
    def MAX_HISTORY_SIZE(self) -> int:
        return self._get_int_env("MAX_HISTORY_SIZE", 50)

    @cached_property
    def HISTORY_DIR(self) -> str:
        return os.getenv("HISTORY_DIR", "./history")

    @cached_property
    def LOG_LEVEL(self) -> str:
        return os.getenv("LOG_LEVEL", "WARNING")

    @cached_property
    def LOG_FORMAT(self) -> str:
        return os.getenv("LOG_FORMAT", "console")

    @cached_property
    def LOG_FILE(self) -> str:
        return os.getenv("LOG_FILE", "")

    @cached_property
    def HTTP_CONNECT_TIMEOUT(self) -> float:
        return self._get_float_env("HTTP_CONNECT_TIMEOUT", 10.0)

    @cached_property
    def HTTP_READ_TIMEOUT(self) -> float:
        return self._get_float_env("HTTP_READ_TIMEOUT", 90.0)

    @cached_property
    def HTTP_WRITE_TIMEOUT(self) -> float:
        return self._get_float_env("HTTP_WRITE_TIMEOUT", 10.0)

    @cached_property
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
        """Valida as configurações obrigatórias."""
        if not self.OPENROUTER_API_KEY:
            raise ConfigurationError(
                "OPENROUTER_API_KEY não configurada.\n"
                "Configure no arquivo .env ou como variável de ambiente."
            )


config = Config()
