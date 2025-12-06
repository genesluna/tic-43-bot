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


class TestConfigValidation:
    """Testes para validação de configurações."""

    def test_validate_missing_api_key(self):
        """API key vazia deve levantar ConfigurationError."""
        from utils.config import Config, ConfigurationError

        with patch.object(Config, "OPENROUTER_API_KEY", ""):
            with pytest.raises(ConfigurationError) as exc_info:
                Config.validate()

            assert "OPENROUTER_API_KEY" in str(exc_info.value)

    def test_validate_with_api_key(self):
        """API key presente não deve levantar erro."""
        from utils.config import Config

        with patch.object(Config, "OPENROUTER_API_KEY", "valid_key"):
            Config.validate()


class TestGetIntEnv:
    """Testes para a função _get_int_env."""

    def test_get_int_env_valid_value(self):
        """Valor inteiro válido deve ser retornado."""
        from utils.config import _get_int_env

        with patch.dict(os.environ, {"TEST_INT": "42"}):
            result = _get_int_env("TEST_INT", 10)
            assert result == 42

    def test_get_int_env_uses_default(self):
        """Valor ausente deve usar default."""
        from utils.config import _get_int_env

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("TEST_MISSING", None)
            result = _get_int_env("TEST_MISSING", 99)
            assert result == 99

    def test_get_int_env_invalid_value(self):
        """Valor não-numérico deve levantar ConfigurationError."""
        from utils.config import _get_int_env, ConfigurationError

        with patch.dict(os.environ, {"TEST_INT": "not_a_number"}):
            with pytest.raises(ConfigurationError) as exc_info:
                _get_int_env("TEST_INT", 10)

            assert "deve ser um número inteiro" in str(exc_info.value)
            assert "not_a_number" in str(exc_info.value)

    def test_get_int_env_negative_value(self):
        """Valor negativo deve levantar ConfigurationError."""
        from utils.config import _get_int_env, ConfigurationError

        with patch.dict(os.environ, {"TEST_INT": "-5"}):
            with pytest.raises(ConfigurationError) as exc_info:
                _get_int_env("TEST_INT", 10)

            assert "deve ser um inteiro positivo" in str(exc_info.value)

    def test_get_int_env_zero_value(self):
        """Valor zero deve levantar ConfigurationError."""
        from utils.config import _get_int_env, ConfigurationError

        with patch.dict(os.environ, {"TEST_INT": "0"}):
            with pytest.raises(ConfigurationError) as exc_info:
                _get_int_env("TEST_INT", 10)

            assert "deve ser um inteiro positivo" in str(exc_info.value)

    def test_get_int_env_float_value(self):
        """Valor float deve levantar ConfigurationError."""
        from utils.config import _get_int_env, ConfigurationError

        with patch.dict(os.environ, {"TEST_INT": "3.14"}):
            with pytest.raises(ConfigurationError) as exc_info:
                _get_int_env("TEST_INT", 10)

            assert "deve ser um número inteiro" in str(exc_info.value)
