"""Testes para o módulo de configuração."""

import os
import threading
import pytest
from unittest.mock import patch

from utils.config import Config, ConfigurationError, config, _ThreadSafeCachedProperty


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


class TestThreadSafeCachedProperty:
    """Testes para o descriptor _ThreadSafeCachedProperty."""

    def test_thread_safe_initial_evaluation(self):
        """Avaliação inicial deve ser thread-safe."""
        call_count = 0
        call_lock = threading.Lock()

        class TestClass:
            @_ThreadSafeCachedProperty
            def expensive_prop(self):
                nonlocal call_count
                with call_lock:
                    call_count += 1
                return "value"

        instance = TestClass()
        results = []
        errors = []

        def access_property():
            try:
                results.append(instance.expensive_prop)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=access_property) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert call_count == 1
        assert all(r == "value" for r in results)

    def test_descriptor_returns_self_on_class_access(self):
        """Acesso via classe deve retornar o descriptor."""

        class TestClass:
            @_ThreadSafeCachedProperty
            def prop(self):
                return "value"

        assert isinstance(TestClass.prop, _ThreadSafeCachedProperty)

    def test_concurrent_access_different_instances(self):
        """Instâncias diferentes devem ter caches independentes."""
        call_counts = {}
        call_lock = threading.Lock()

        class TestClass:
            def __init__(self, name):
                self.name = name

            @_ThreadSafeCachedProperty
            def prop(self):
                with call_lock:
                    call_counts[self.name] = call_counts.get(self.name, 0) + 1
                return f"value_{self.name}"

        instances = [TestClass(f"inst_{i}") for i in range(5)]
        results = []
        errors = []

        def access_all():
            try:
                for inst in instances:
                    results.append((inst.name, inst.prop))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=access_all) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        for name in call_counts:
            assert call_counts[name] == 1

    def test_set_name_called(self):
        """__set_name__ deve ser chamado com o nome do atributo."""

        class TestClass:
            @_ThreadSafeCachedProperty
            def my_property(self):
                return "value"

        prop = TestClass.__dict__["my_property"]
        assert prop.attr_name == "my_property"


class TestConfigUpperBounds:
    """Testes para limites superiores de configuração."""

    def test_max_message_length_respects_upper_bound(self, monkeypatch):
        """MAX_MESSAGE_LENGTH é limitado ao máximo permitido."""
        from utils.config import Config, MAX_MESSAGE_LENGTH_UPPER

        monkeypatch.setenv("MAX_MESSAGE_LENGTH", str(MAX_MESSAGE_LENGTH_UPPER + 1000))
        cfg = Config()

        assert cfg.MAX_MESSAGE_LENGTH == MAX_MESSAGE_LENGTH_UPPER

    def test_max_history_size_respects_upper_bound(self, monkeypatch):
        """MAX_HISTORY_SIZE é limitado ao máximo permitido."""
        from utils.config import Config, MAX_HISTORY_SIZE_UPPER

        monkeypatch.setenv("MAX_HISTORY_SIZE", str(MAX_HISTORY_SIZE_UPPER + 100))
        cfg = Config()

        assert cfg.MAX_HISTORY_SIZE == MAX_HISTORY_SIZE_UPPER

    def test_max_message_length_within_bound_unchanged(self, monkeypatch):
        """MAX_MESSAGE_LENGTH dentro do limite não é alterado."""
        from utils.config import Config

        monkeypatch.setenv("MAX_MESSAGE_LENGTH", "5000")
        cfg = Config()

        assert cfg.MAX_MESSAGE_LENGTH == 5000

    def test_max_history_size_within_bound_unchanged(self, monkeypatch):
        """MAX_HISTORY_SIZE dentro do limite não é alterado."""
        from utils.config import Config

        monkeypatch.setenv("MAX_HISTORY_SIZE", "100")
        cfg = Config()

        assert cfg.MAX_HISTORY_SIZE == 100


class TestHistoryDirValidation:
    """Testes para validação do HISTORY_DIR."""

    def test_history_dir_default_value(self, monkeypatch):
        """HISTORY_DIR padrão deve ser ./history."""
        from utils.config import Config

        monkeypatch.delenv("HISTORY_DIR", raising=False)
        cfg = Config()

        assert cfg.HISTORY_DIR == "./history"

    def test_history_dir_relative_path_accepted(self, tmp_path, monkeypatch):
        """Caminho relativo dentro do projeto é aceito."""
        from utils.config import Config

        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HISTORY_DIR", "./custom_history")
        cfg = Config()

        assert cfg.HISTORY_DIR == "./custom_history"

    def test_history_dir_subdirectory_accepted(self, tmp_path, monkeypatch):
        """Subdiretório dentro do projeto é aceito."""
        from utils.config import Config

        monkeypatch.chdir(tmp_path)
        subdir = tmp_path / "data" / "history"
        subdir.mkdir(parents=True)
        monkeypatch.setenv("HISTORY_DIR", str(subdir))
        cfg = Config()

        assert cfg.HISTORY_DIR == str(subdir)

    def test_history_dir_absolute_path_outside_rejected(self, tmp_path, monkeypatch):
        """Caminho absoluto fora do projeto é rejeitado."""
        from utils.config import Config

        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HISTORY_DIR", "/tmp/malicious_history")
        cfg = Config()

        assert cfg.HISTORY_DIR == "./history"

    def test_history_dir_parent_traversal_rejected(self, tmp_path, monkeypatch):
        """Tentativa de path traversal com .. é rejeitada."""
        from utils.config import Config

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        monkeypatch.chdir(project_dir)
        monkeypatch.setenv("HISTORY_DIR", "../outside_project")
        cfg = Config()

        assert cfg.HISTORY_DIR == "./history"

    def test_history_dir_logs_warning_on_rejection(self, tmp_path, monkeypatch, caplog):
        """Warning é logado quando HISTORY_DIR é rejeitado."""
        import logging
        from utils.config import Config

        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HISTORY_DIR", "/etc/passwd")

        with caplog.at_level(logging.WARNING):
            cfg = Config()
            _ = cfg.HISTORY_DIR

        assert any("fora do diretório do projeto" in record.message for record in caplog.records)
