"""Configurações do chatbot carregadas do ambiente."""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Classe de configuração do chatbot."""

    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1/chat/completions"
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")

    SYSTEM_PROMPT: str = os.getenv(
        "SYSTEM_PROMPT",
        "Você é um assistente virtual útil e amigável. Responda de forma clara e concisa.",
    )

    EXIT_COMMANDS: tuple = ("sair", "exit", "quit")
    CLEAR_COMMANDS: tuple = ("/limpar", "/clear")
    SAVE_COMMANDS: tuple = ("/salvar", "/save")
    HELP_COMMANDS: tuple = ("/ajuda", "/help")
    MODEL_COMMANDS: tuple = ("/modelo",)


config = Config()
