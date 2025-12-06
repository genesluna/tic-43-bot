"""Testes para o módulo principal do chatbot."""

import pytest
from unittest.mock import MagicMock, patch
from chatbot import handle_command


class TestHandleCommand:
    """Testes para a função handle_command."""

    def setup_method(self):
        """Configura mocks para cada teste."""
        self.mock_conversation = MagicMock()
        self.mock_client = MagicMock()
        self.mock_display = MagicMock()

    def test_exit_command_sair(self):
        """Verifica se 'sair' retorna False para encerrar."""
        result = handle_command(
            "sair",
            self.mock_conversation,
            self.mock_client,
            self.mock_display,
        )
        assert result is False

    def test_exit_command_exit(self):
        """Verifica se 'exit' retorna False para encerrar."""
        result = handle_command(
            "exit",
            self.mock_conversation,
            self.mock_client,
            self.mock_display,
        )
        assert result is False

    def test_exit_command_quit(self):
        """Verifica se 'quit' retorna False para encerrar."""
        result = handle_command(
            "quit",
            self.mock_conversation,
            self.mock_client,
            self.mock_display,
        )
        assert result is False

    def test_clear_command_limpar(self):
        """Verifica se '/limpar' limpa o histórico."""
        result = handle_command(
            "/limpar",
            self.mock_conversation,
            self.mock_client,
            self.mock_display,
        )
        assert result is True
        self.mock_conversation.clear.assert_called_once()
        self.mock_display.show_success.assert_called_once()

    def test_clear_command_clear(self):
        """Verifica se '/clear' limpa o histórico."""
        result = handle_command(
            "/clear",
            self.mock_conversation,
            self.mock_client,
            self.mock_display,
        )
        assert result is True
        self.mock_conversation.clear.assert_called_once()

    def test_save_command_success(self):
        """Verifica se '/salvar' salva o histórico."""
        self.mock_conversation.save_to_file.return_value = "history/test.json"
        result = handle_command(
            "/salvar",
            self.mock_conversation,
            self.mock_client,
            self.mock_display,
        )
        assert result is True
        self.mock_conversation.save_to_file.assert_called_once()
        self.mock_display.show_success.assert_called_once()

    def test_save_command_error(self):
        """Verifica se erro ao salvar é tratado."""
        self.mock_conversation.save_to_file.side_effect = IOError("Erro de escrita")
        result = handle_command(
            "/salvar",
            self.mock_conversation,
            self.mock_client,
            self.mock_display,
        )
        assert result is True
        self.mock_display.show_error.assert_called_once()

    def test_help_command(self):
        """Verifica se '/ajuda' mostra ajuda."""
        result = handle_command(
            "/ajuda",
            self.mock_conversation,
            self.mock_client,
            self.mock_display,
        )
        assert result is True
        self.mock_display.show_help.assert_called_once()

    def test_help_command_english(self):
        """Verifica se '/help' mostra ajuda."""
        result = handle_command(
            "/help",
            self.mock_conversation,
            self.mock_client,
            self.mock_display,
        )
        assert result is True
        self.mock_display.show_help.assert_called_once()

    def test_model_command(self):
        """Verifica se '/modelo' mostra info do modelo."""
        self.mock_client.get_model.return_value = "openai/gpt-4o-mini"
        result = handle_command(
            "/modelo",
            self.mock_conversation,
            self.mock_client,
            self.mock_display,
        )
        assert result is True
        self.mock_client.get_model.assert_called_once()
        self.mock_display.show_model_info.assert_called_once_with("openai/gpt-4o-mini")

    def test_regular_message_returns_none(self):
        """Verifica se mensagem normal retorna None."""
        result = handle_command(
            "Olá, como vai?",
            self.mock_conversation,
            self.mock_client,
            self.mock_display,
        )
        assert result is None

    def test_command_case_insensitive(self):
        """Verifica se comandos são case-insensitive."""
        result = handle_command(
            "SAIR",
            self.mock_conversation,
            self.mock_client,
            self.mock_display,
        )
        assert result is False

    def test_command_with_whitespace(self):
        """Verifica se comandos funcionam com espaços."""
        result = handle_command(
            "  /ajuda  ",
            self.mock_conversation,
            self.mock_client,
            self.mock_display,
        )
        assert result is True
        self.mock_display.show_help.assert_called_once()
