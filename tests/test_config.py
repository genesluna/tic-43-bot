"""Testes para o módulo de configuração."""

import os
import pytest
from unittest.mock import patch


class TestConfig:
    """Testes para a classe Config."""

    def test_exit_commands(self):
        """Verifica se os comandos de saída estão configurados."""
        from utils.config import config

        assert "sair" in config.EXIT_COMMANDS
        assert "exit" in config.EXIT_COMMANDS
        assert "quit" in config.EXIT_COMMANDS

    def test_clear_commands(self):
        """Verifica se os comandos de limpar estão configurados."""
        from utils.config import config

        assert "/limpar" in config.CLEAR_COMMANDS
        assert "/clear" in config.CLEAR_COMMANDS

    def test_save_commands(self):
        """Verifica se os comandos de salvar estão configurados."""
        from utils.config import config

        assert "/salvar" in config.SAVE_COMMANDS
        assert "/save" in config.SAVE_COMMANDS

    def test_help_commands(self):
        """Verifica se os comandos de ajuda estão configurados."""
        from utils.config import config

        assert "/ajuda" in config.HELP_COMMANDS
        assert "/help" in config.HELP_COMMANDS

    def test_model_commands(self):
        """Verifica se os comandos de modelo estão configurados."""
        from utils.config import config

        assert "/modelo" in config.MODEL_COMMANDS

    def test_openrouter_base_url(self):
        """Verifica se a URL base da API está configurada."""
        from utils.config import config

        assert config.OPENROUTER_BASE_URL == "https://openrouter.ai/api/v1/chat/completions"

    def test_default_model(self):
        """Verifica se o modelo padrão está configurado."""
        from utils.config import config

        assert config.OPENROUTER_MODEL is not None
        assert len(config.OPENROUTER_MODEL) > 0

    def test_default_system_prompt(self):
        """Verifica se o system prompt padrão está configurado."""
        from utils.config import config

        assert config.SYSTEM_PROMPT is not None
        assert len(config.SYSTEM_PROMPT) > 0
