"""Testes de integração para o chatbot."""

import pytest
from unittest.mock import patch, MagicMock
from io import StringIO

from chatbot import main, handle_command
from utils.api import OpenRouterClient, APIError
from utils.conversation import ConversationManager
from utils.display import Display


class TestConversationFlow:
    """Testes de integração do fluxo de conversa."""

    @patch("utils.api.httpx.Client")
    def test_full_conversation_flow(self, mock_client_class):
        """Testa fluxo completo: enviar mensagem, receber resposta, histórico."""
        mock_stream_response = MagicMock()
        mock_stream_response.status_code = 200
        mock_stream_response.iter_lines.return_value = [
            'data: {"choices": [{"delta": {"content": "Olá"}}]}',
            'data: {"choices": [{"delta": {"content": "!"}}]}',
            'data: {"choices": [{"delta": {"content": " Tudo bem?"}}]}',
            'data: [DONE]',
        ]
        mock_stream_response.__enter__ = MagicMock(return_value=mock_stream_response)
        mock_stream_response.__exit__ = MagicMock(return_value=False)

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.stream.return_value = mock_stream_response
        mock_client_class.return_value = mock_client

        with OpenRouterClient() as client:
            client._api_key = "test_key"
            conversation = ConversationManager()

            conversation.add_user_message("Oi!")
            chunks = list(client.send_message_stream(conversation.get_messages()))
            response = "".join(chunks)
            conversation.add_assistant_message(response)

            assert response == "Olá! Tudo bem?"
            assert conversation.message_count() == 2

            messages = conversation.get_messages()
            assert messages[1]["role"] == "user"
            assert messages[1]["content"] == "Oi!"
            assert messages[2]["role"] == "assistant"
            assert messages[2]["content"] == "Olá! Tudo bem?"

    @patch("utils.api.httpx.Client")
    def test_conversation_with_error_recovery(self, mock_client_class):
        """Testa recuperação após erro de API."""
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.stream.side_effect = APIError("Erro de conexão")
        mock_client_class.return_value = mock_client

        with OpenRouterClient() as client:
            client._api_key = "test_key"
            conversation = ConversationManager()

            conversation.add_user_message("Teste")
            initial_count = conversation.message_count()

            try:
                list(client.send_message_stream(conversation.get_messages()))
            except APIError:
                conversation.remove_last_user_message()

            assert conversation.message_count() == initial_count - 1

    def test_conversation_history_limit(self):
        """Testa que histórico respeita limite configurado."""
        conversation = ConversationManager()

        for i in range(100):
            conversation.add_user_message(f"Mensagem {i}")
            conversation.add_assistant_message(f"Resposta {i}")

        from utils.config import config
        assert len(conversation.messages) <= config.MAX_HISTORY_SIZE + 1


class TestMainIntegration:
    """Testes de integração da função main."""

    @patch("chatbot.Display")
    @patch("chatbot.Config")
    @patch("chatbot.OpenRouterClient")
    @patch("chatbot.ConversationManager")
    @patch("chatbot.config")
    def test_complete_session(
        self, mock_config, mock_conv_class, mock_client_class, mock_config_class, mock_display_class
    ):
        """Testa sessão completa: banner, mensagem, resposta, saída."""
        mock_config.MAX_MESSAGE_LENGTH = 10000
        mock_config.EXIT_COMMANDS = ("sair",)
        mock_config.CLEAR_COMMANDS = ("/limpar",)
        mock_config.SAVE_COMMANDS = ("/salvar",)
        mock_config.HELP_COMMANDS = ("/ajuda",)
        mock_config.MODEL_COMMANDS = ("/modelo",)

        mock_display = MagicMock()
        mock_display.prompt_input.side_effect = ["Olá", "sair"]
        mock_display.stop_streaming.return_value = "Olá! Como posso ajudar?"
        mock_display_class.return_value = mock_display

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.send_message_stream.return_value = iter(["Olá", "!", " Como posso ajudar?"])
        mock_client_class.return_value = mock_client

        mock_conv = MagicMock()
        mock_conv.get_messages.return_value = [{"role": "user", "content": "Olá"}]
        mock_conv_class.return_value = mock_conv

        main([])

        mock_display.show_banner.assert_called_once()
        mock_display.show_info.assert_called()
        mock_display.start_spinner.assert_called_once()
        mock_display.transition_spinner_to_streaming.assert_called()
        mock_display.add_streaming_chunk.assert_called()
        mock_display.stop_streaming.assert_called()
        mock_conv.add_user_message.assert_called_with("Olá")
        mock_conv.add_assistant_message.assert_called()
        mock_display.show_goodbye.assert_called_once()

    @patch("chatbot.Display")
    @patch("chatbot.Config")
    @patch("chatbot.OpenRouterClient")
    @patch("chatbot.ConversationManager")
    @patch("chatbot.config")
    def test_session_with_commands(
        self, mock_config, mock_conv_class, mock_client_class, mock_config_class, mock_display_class
    ):
        """Testa sessão com comandos especiais."""
        mock_config.MAX_MESSAGE_LENGTH = 10000
        mock_config.EXIT_COMMANDS = ("sair",)
        mock_config.CLEAR_COMMANDS = ("/limpar",)
        mock_config.SAVE_COMMANDS = ("/salvar",)
        mock_config.HELP_COMMANDS = ("/ajuda",)
        mock_config.MODEL_COMMANDS = ("/modelo",)

        mock_display = MagicMock()
        mock_display.prompt_input.side_effect = ["/ajuda", "/limpar", "/modelo", "sair"]
        mock_display_class.return_value = mock_display

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get_model.return_value = "openai/gpt-4o-mini"
        mock_client_class.return_value = mock_client

        mock_conv = MagicMock()
        mock_conv_class.return_value = mock_conv

        main([])

        mock_display.show_help.assert_called_once()
        mock_conv.clear.assert_called_once()
        mock_display.show_model_info.assert_called_once_with("openai/gpt-4o-mini")


class TestCommandIntegration:
    """Testes de integração dos comandos."""

    def test_all_exit_commands(self):
        """Testa todos os comandos de saída."""
        conversation = MagicMock()
        client = MagicMock()
        display = MagicMock()

        for cmd in ["sair", "exit", "quit", "SAIR", "EXIT", "QUIT"]:
            result = handle_command(cmd, conversation, client, display)
            assert result is False

    def test_all_clear_commands(self):
        """Testa todos os comandos de limpar."""
        conversation = MagicMock()
        client = MagicMock()
        display = MagicMock()

        for cmd in ["/limpar", "/clear", "/LIMPAR", "/CLEAR"]:
            conversation.reset_mock()
            display.reset_mock()
            result = handle_command(cmd, conversation, client, display)
            assert result is True
            conversation.clear.assert_called_once()

    def test_save_command_creates_file(self, tmp_path, monkeypatch):
        """Testa que comando salvar cria arquivo."""
        monkeypatch.chdir(tmp_path)

        conversation = ConversationManager()
        conversation.add_user_message("Teste")
        conversation.add_assistant_message("Resposta")

        client = MagicMock()
        display = MagicMock()

        result = handle_command("/salvar", conversation, client, display)

        assert result is True
        display.show_success.assert_called_once()

        history_dir = tmp_path / "history"
        assert history_dir.exists()
        files = list(history_dir.glob("*.json"))
        assert len(files) == 1


class TestDisplayIntegration:
    """Testes de integração do display."""

    def test_spinner_lifecycle(self):
        """Testa ciclo de vida completo do spinner."""
        display = Display()

        assert display.spinner.running is False

        display.start_spinner()
        assert display.spinner.running is True
        assert display.spinner.thread is not None
        assert display.spinner.thread.is_alive()

        display.update_spinner_tokens(50)
        assert display.spinner.token_count == 50

        display.stop_spinner()
        assert display.spinner.running is False

    def test_display_output_sequence(self, capsys):
        """Testa sequência de outputs do display."""
        display = Display()

        display.show_banner()
        display.show_info("Teste info")
        display.show_success("Sucesso")
        display.show_error("Erro")
        display.show_bot_message("Resposta do bot")
        display.show_goodbye()

        captured = capsys.readouterr()

        assert "Chatbot Conversacional" in captured.out
        assert "Teste info" in captured.out
        assert "Sucesso" in captured.out
        assert "Erro" in captured.out
        assert "Resposta do bot" in captured.out
        assert "Até logo" in captured.out
