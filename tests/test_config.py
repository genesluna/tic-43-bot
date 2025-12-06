"""Testes para o módulo de configuração."""

import os
import pytest
from unittest.mock import patch

from utils.config import Config, ConfigurationError, config


class TestConfig:
    """Testes para a classe Config."""

    def test_exit_commands(self):
        """Verifica se os comandos de saída estão configurados."""
        assert "sair" in config.EXIT_COMMANDS
        assert "exit" in config.EXIT_COMMANDS
        assert "quit" in config.EXIT_COMMANDS

    def test_clear_commands(self):
        """Verifica se os comandos de limpar estão configurados."""
        assert "/limpar" in config.CLEAR_COMMANDS
        assert "/clear" in config.CLEAR_COMMANDS

    def test_save_commands(self):
        """Verifica se os comandos de salvar estão configurados."""
        assert "/salvar" in config.SAVE_COMMANDS
        assert "/save" in config.SAVE_COMMANDS

    def test_help_commands(self):
        """Verifica se os comandos de ajuda estão configurados."""
        assert "/ajuda" in config.HELP_COMMANDS
        assert "/help" in config.HELP_COMMANDS

    def test_model_commands(self):
        """Verifica se os comandos de modelo estão configurados."""
        assert "/modelo" in config.MODEL_COMMANDS

    def test_openrouter_base_url(self):
        """Verifica se a URL base da API está configurada."""
        assert config.OPENROUTER_BASE_URL == "https://openrouter.ai/api/v1/chat/completions"

    def test_default_model(self):
        """Verifica se o modelo padrão está configurado."""
        assert config.OPENROUTER_MODEL is not None
        assert len(config.OPENROUTER_MODEL) > 0

    def test_default_system_prompt(self):
        """Verifica se o system prompt padrão está configurado."""
        assert config.SYSTEM_PROMPT is not None
        assert len(config.SYSTEM_PROMPT) > 0


class TestConfigValidation:
    """Testes para validação de configurações."""

    def test_validate_missing_api_key(self):
        """API key vazia deve levantar ConfigurationError."""
        test_config = Config()
        test_config.__dict__["OPENROUTER_API_KEY"] = ""

        with pytest.raises(ConfigurationError) as exc_info:
            test_config.validate()

        assert "OPENROUTER_API_KEY" in str(exc_info.value)

    def test_validate_with_api_key(self):
        """API key presente não deve levantar erro."""
        test_config = Config()
        test_config.__dict__["OPENROUTER_API_KEY"] = "valid_key"

        test_config.validate()


class TestGetIntEnv:
    """Testes para o método _get_int_env."""

    def test_get_int_env_valid_value(self):
        """Valor inteiro válido deve ser retornado."""
        test_config = Config()

        with patch.dict(os.environ, {"TEST_INT": "42"}):
            result = test_config._get_int_env("TEST_INT", 10)
            assert result == 42

    def test_get_int_env_uses_default(self):
        """Valor ausente deve usar default."""
        test_config = Config()

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("TEST_MISSING", None)
            result = test_config._get_int_env("TEST_MISSING", 99)
            assert result == 99

    def test_get_int_env_invalid_value(self):
        """Valor não-numérico deve levantar ConfigurationError."""
        test_config = Config()

        with patch.dict(os.environ, {"TEST_INT": "not_a_number"}):
            with pytest.raises(ConfigurationError) as exc_info:
                test_config._get_int_env("TEST_INT", 10)

            assert "deve ser um número inteiro" in str(exc_info.value)
            assert "not_a_number" in str(exc_info.value)

    def test_get_int_env_negative_value(self):
        """Valor negativo deve levantar ConfigurationError."""
        test_config = Config()

        with patch.dict(os.environ, {"TEST_INT": "-5"}):
            with pytest.raises(ConfigurationError) as exc_info:
                test_config._get_int_env("TEST_INT", 10)

            assert "deve ser um inteiro positivo" in str(exc_info.value)

    def test_get_int_env_zero_value(self):
        """Valor zero deve levantar ConfigurationError."""
        test_config = Config()

        with patch.dict(os.environ, {"TEST_INT": "0"}):
            with pytest.raises(ConfigurationError) as exc_info:
                test_config._get_int_env("TEST_INT", 10)

            assert "deve ser um inteiro positivo" in str(exc_info.value)

    def test_get_int_env_float_value(self):
        """Valor float deve levantar ConfigurationError."""
        test_config = Config()

        with patch.dict(os.environ, {"TEST_INT": "3.14"}):
            with pytest.raises(ConfigurationError) as exc_info:
                test_config._get_int_env("TEST_INT", 10)

            assert "deve ser um número inteiro" in str(exc_info.value)


class TestGetFloatEnv:
    """Testes para o método _get_float_env."""

    def test_get_float_env_valid_value(self):
        """Valor float válido deve ser retornado."""
        test_config = Config()

        with patch.dict(os.environ, {"TEST_FLOAT": "15.5"}):
            result = test_config._get_float_env("TEST_FLOAT", 10.0)
            assert result == 15.5

    def test_get_float_env_valid_integer_string(self):
        """Valor inteiro como string deve ser convertido para float."""
        test_config = Config()

        with patch.dict(os.environ, {"TEST_FLOAT": "30"}):
            result = test_config._get_float_env("TEST_FLOAT", 10.0)
            assert result == 30.0

    def test_get_float_env_uses_default(self):
        """Valor ausente deve usar default."""
        test_config = Config()

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("TEST_MISSING_FLOAT", None)
            result = test_config._get_float_env("TEST_MISSING_FLOAT", 25.5)
            assert result == 25.5

    def test_get_float_env_invalid_value(self):
        """Valor não-numérico deve levantar ConfigurationError."""
        test_config = Config()

        with patch.dict(os.environ, {"TEST_FLOAT": "not_a_number"}):
            with pytest.raises(ConfigurationError) as exc_info:
                test_config._get_float_env("TEST_FLOAT", 10.0)

            assert "deve ser um número válido" in str(exc_info.value)
            assert "not_a_number" in str(exc_info.value)

    def test_get_float_env_negative_value(self):
        """Valor negativo deve levantar ConfigurationError."""
        test_config = Config()

        with patch.dict(os.environ, {"TEST_FLOAT": "-5.0"}):
            with pytest.raises(ConfigurationError) as exc_info:
                test_config._get_float_env("TEST_FLOAT", 10.0)

            assert "deve ser um número positivo" in str(exc_info.value)

    def test_get_float_env_zero_value(self):
        """Valor zero deve levantar ConfigurationError."""
        test_config = Config()

        with patch.dict(os.environ, {"TEST_FLOAT": "0"}):
            with pytest.raises(ConfigurationError) as exc_info:
                test_config._get_float_env("TEST_FLOAT", 10.0)

            assert "deve ser um número positivo" in str(exc_info.value)

    def test_get_float_env_empty_string(self):
        """String vazia deve levantar ConfigurationError."""
        test_config = Config()

        with patch.dict(os.environ, {"TEST_FLOAT": ""}):
            with pytest.raises(ConfigurationError) as exc_info:
                test_config._get_float_env("TEST_FLOAT", 10.0)

            assert "deve ser um número válido" in str(exc_info.value)


class TestLazyEvaluation:
    """Testes para avaliação lazy das configurações."""

    def test_config_properties_are_cached(self):
        """Propriedades devem ser cached após primeiro acesso."""
        test_config = Config()

        with patch.object(os, "getenv", return_value="test-model") as mock_getenv:
            first_access = test_config.OPENROUTER_MODEL
            second_access = test_config.OPENROUTER_MODEL
            third_access = test_config.OPENROUTER_MODEL

            assert first_access == "test-model"
            assert second_access == "test-model"
            assert third_access == "test-model"
            mock_getenv.assert_called_once()

    def test_cached_property_stored_in_instance_dict(self):
        """Valor cached deve ser armazenado no __dict__ da instância."""
        test_config = Config()

        assert "OPENROUTER_MODEL" not in test_config.__dict__

        _ = test_config.OPENROUTER_MODEL

        assert "OPENROUTER_MODEL" in test_config.__dict__

    def test_different_config_instances_are_independent(self):
        """Instâncias diferentes devem ter caches independentes."""
        config1 = Config()
        config2 = Config()

        config1.__dict__["OPENROUTER_API_KEY"] = "key1"
        config2.__dict__["OPENROUTER_API_KEY"] = "key2"

        assert config1.OPENROUTER_API_KEY == "key1"
        assert config2.OPENROUTER_API_KEY == "key2"
