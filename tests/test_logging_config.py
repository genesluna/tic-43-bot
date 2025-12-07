"""Testes para o módulo de configuração de logging."""

import json
import logging
import os
import tempfile
from unittest.mock import patch

from utils.logging_config import (
    ConsoleFormatter,
    StructuredFormatter,
    setup_logging,
)


class TestStructuredFormatter:
    """Testes para o StructuredFormatter."""

    def test_format_basic_record(self):
        """Verifica formatação básica de um log record."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        data = json.loads(result)

        assert data["level"] == "INFO"
        assert data["logger"] == "test.logger"
        assert data["message"] == "Test message"
        assert data["line"] == 42
        assert "timestamp" in data
        assert data["timestamp"].endswith("+00:00")

    def test_format_with_exception(self):
        """Verifica formatação com exceção."""
        formatter = StructuredFormatter()
        try:
            raise ValueError("Test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=10,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        result = formatter.format(record)
        data = json.loads(result)

        assert "exception" in data
        assert "ValueError" in data["exception"]
        assert "Test error" in data["exception"]

    def test_format_with_extra_data(self):
        """Verifica formatação com dados extras."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.extra_data = {"key": "value"}

        result = formatter.format(record)
        data = json.loads(result)

        assert data["data"] == {"key": "value"}

    def test_format_with_message_args(self):
        """Verifica formatação com argumentos na mensagem."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Value: %s",
            args=("test",),
            exc_info=None,
        )

        result = formatter.format(record)
        data = json.loads(result)

        assert data["message"] == "Value: test"


class TestConsoleFormatter:
    """Testes para o ConsoleFormatter."""

    def test_format_info(self):
        """Verifica formatação de log INFO."""
        formatter = ConsoleFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)

        assert "INFO" in result
        assert "test.logger" in result
        assert "Test message" in result
        assert "\033[32m" in result

    def test_format_error(self):
        """Verifica formatação de log ERROR."""
        formatter = ConsoleFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)

        assert "ERROR" in result
        assert "\033[31m" in result

    def test_format_warning(self):
        """Verifica formatação de log WARNING."""
        formatter = ConsoleFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.WARNING,
            pathname="test.py",
            lineno=1,
            msg="Warning message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)

        assert "WARNING" in result
        assert "\033[33m" in result

    def test_format_debug(self):
        """Verifica formatação de log DEBUG."""
        formatter = ConsoleFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.DEBUG,
            pathname="test.py",
            lineno=1,
            msg="Debug message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)

        assert "DEBUG" in result
        assert "\033[36m" in result


class TestSetupLogging:
    """Testes para a função setup_logging."""

    def teardown_method(self):
        """Limpa handlers após cada teste."""
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            handler.close()
            root_logger.removeHandler(handler)

    def test_setup_default_no_handlers(self):
        """Verifica que sem LOG_LEVEL definido, apenas NullHandler é adicionado."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("LOG_LEVEL", None)
            os.environ.pop("LOG_FILE", None)

            setup_logging()

            root_logger = logging.getLogger()
            assert len(root_logger.handlers) == 1
            assert isinstance(root_logger.handlers[0], logging.NullHandler)

    def test_setup_with_log_level(self):
        """Verifica que com LOG_LEVEL definido, console handler é adicionado."""
        with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}, clear=True):
            setup_logging()

            root_logger = logging.getLogger()
            handlers = [h for h in root_logger.handlers if not isinstance(h, logging.NullHandler)]
            assert len(handlers) == 1
            assert isinstance(handlers[0], logging.StreamHandler)

    def test_setup_with_log_file(self):
        """Verifica que com LOG_FILE definido, file handler é adicionado."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            log_file = f.name

        try:
            with patch.dict(os.environ, {"LOG_FILE": log_file}, clear=True):
                setup_logging()

                root_logger = logging.getLogger()
                file_handlers = [h for h in root_logger.handlers if isinstance(h, logging.FileHandler)]
                assert len(file_handlers) == 1
        finally:
            os.unlink(log_file)

    def test_setup_json_format(self):
        """Verifica que LOG_FORMAT=json usa StructuredFormatter."""
        with patch.dict(os.environ, {"LOG_LEVEL": "INFO", "LOG_FORMAT": "json"}, clear=True):
            setup_logging()

            root_logger = logging.getLogger()
            handlers = [h for h in root_logger.handlers if isinstance(h, logging.StreamHandler)]
            assert len(handlers) == 1
            assert isinstance(handlers[0].formatter, StructuredFormatter)

    def test_setup_console_format(self):
        """Verifica que LOG_FORMAT=console usa ConsoleFormatter."""
        with patch.dict(os.environ, {"LOG_LEVEL": "INFO", "LOG_FORMAT": "console"}, clear=True):
            setup_logging()

            root_logger = logging.getLogger()
            handlers = [h for h in root_logger.handlers if isinstance(h, logging.StreamHandler)]
            assert len(handlers) == 1
            assert isinstance(handlers[0].formatter, ConsoleFormatter)

    def test_setup_invalid_log_level_defaults_to_warning(self):
        """Verifica que nível de log inválido usa WARNING como padrão."""
        with patch.dict(os.environ, {"LOG_LEVEL": "INVALID"}, clear=True):
            setup_logging()

            root_logger = logging.getLogger()
            assert root_logger.level == logging.WARNING

    def test_setup_creates_log_directory(self):
        """Verifica que diretório de log é criado se não existir."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "subdir", "app.log")

            with patch.dict(os.environ, {"LOG_FILE": log_file}, clear=True):
                setup_logging()

                assert os.path.exists(os.path.dirname(log_file))

    def test_setup_with_explicit_parameters(self):
        """Verifica que parâmetros explícitos têm precedência sobre env vars."""
        with patch.dict(os.environ, {"LOG_LEVEL": "ERROR"}, clear=True):
            setup_logging(log_level="DEBUG")

            root_logger = logging.getLogger()
            # Parameter takes precedence over env var
            assert root_logger.level == logging.DEBUG

    def test_setup_with_log_level_parameter_only(self):
        """Verifica que apenas parâmetro log_level funciona sem env var."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("LOG_LEVEL", None)

            setup_logging(log_level="INFO")

            root_logger = logging.getLogger()
            handlers = [h for h in root_logger.handlers if isinstance(h, logging.StreamHandler)]
            assert len(handlers) == 1
            assert root_logger.level == logging.INFO

    def test_setup_with_log_file_parameter(self):
        """Verifica que parâmetro log_file funciona."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            log_file = f.name

        try:
            with patch.dict(os.environ, {}, clear=True):
                setup_logging(log_file=log_file)

                root_logger = logging.getLogger()
                file_handlers = [h for h in root_logger.handlers if isinstance(h, logging.FileHandler)]
                assert len(file_handlers) == 1
        finally:
            os.unlink(log_file)
