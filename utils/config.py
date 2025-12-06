"""Configurações do chatbot carregadas do ambiente."""

import os
from dotenv import load_dotenv

load_dotenv()


class ConfigurationError(Exception):
    """Erro de configuração do chatbot."""


class Config:
    """Classe de configuração do chatbot."""

    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1/chat/completions"
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")

    SYSTEM_PROMPT: str = os.getenv(
        "SYSTEM_PROMPT",
        "Você é um assistente virtual útil e amigável.",
    )

    RESPONSE_LANGUAGE: str = os.getenv("RESPONSE_LANGUAGE", "português")
    RESPONSE_LENGTH: str = os.getenv("RESPONSE_LENGTH", "conciso")
    RESPONSE_TONE: str = os.getenv("RESPONSE_TONE", "amigável")
    RESPONSE_FORMAT: str = os.getenv("RESPONSE_FORMAT", "markdown")

    EXIT_COMMANDS: tuple = ("sair", "exit", "quit")
    CLEAR_COMMANDS: tuple = ("/limpar", "/clear")
    SAVE_COMMANDS: tuple = ("/salvar", "/save")
    HELP_COMMANDS: tuple = ("/ajuda", "/help")
    MODEL_COMMANDS: tuple = ("/modelo",)

    MAX_MESSAGE_LENGTH: int = int(os.getenv("MAX_MESSAGE_LENGTH", "10000"))
    MAX_HISTORY_SIZE: int = int(os.getenv("MAX_HISTORY_SIZE", "50"))

    @classmethod
    def validate(cls) -> None:
        """Valida as configurações obrigatórias."""
        if not cls.OPENROUTER_API_KEY:
            raise ConfigurationError(
                "OPENROUTER_API_KEY não configurada.\n"
                "Configure no arquivo .env ou como variável de ambiente."
            )


config = Config()
