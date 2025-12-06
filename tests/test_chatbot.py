"""Testes para o módulo principal do chatbot."""

import pytest
from unittest.mock import MagicMock, patch, call
from chatbot import handle_command, main


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

    def test_model_command_with_argument(self):
        """Verifica se '/modelo provider/model' troca o modelo."""
        result = handle_command(
            "/modelo openai/gpt-4",
            self.mock_conversation,
            self.mock_client,
            self.mock_display,
        )
        assert result is True
        self.mock_client.set_model.assert_called_once_with("openai/gpt-4")
        self.mock_display.show_model_changed.assert_called_once_with("openai/gpt-4")

    def test_model_command_with_invalid_argument(self):
        """Verifica se modelo inválido mostra erro."""
        self.mock_client.set_model.side_effect = ValueError("Modelo deve estar no formato 'provider/model-name'.")
        result = handle_command(
            "/modelo invalid-model",
            self.mock_conversation,
            self.mock_client,
            self.mock_display,
        )
        assert result is True
        self.mock_display.show_error.assert_called_once()

    def test_model_command_preserves_argument_case(self):
        """Verifica se o argumento do modelo preserva maiúsculas/minúsculas."""
        result = handle_command(
            "/modelo OpenAI/GPT-4o-Mini",
            self.mock_conversation,
            self.mock_client,
            self.mock_display,
        )
        assert result is True
        self.mock_client.set_model.assert_called_once_with("OpenAI/GPT-4o-Mini")

    def test_list_command(self):
        """Verifica se '/listar' mostra arquivos de histórico."""
        self.mock_conversation.list_history_files.return_value = []
        result = handle_command(
            "/listar",
            self.mock_conversation,
            self.mock_client,
            self.mock_display,
        )
        assert result is True
        self.mock_conversation.list_history_files.assert_called_once()
        self.mock_display.show_history_list.assert_called_once_with([])

    def test_list_command_english(self):
        """Verifica se '/list' mostra arquivos de histórico."""
        self.mock_conversation.list_history_files.return_value = []
        result = handle_command(
            "/list",
            self.mock_conversation,
            self.mock_client,
            self.mock_display,
        )
        assert result is True
        self.mock_display.show_history_list.assert_called_once()

    def test_load_command_with_file(self):
        """Verifica se '/carregar arquivo' carrega histórico."""
        self.mock_conversation.load_from_file.return_value = 5
        result = handle_command(
            "/carregar test.json",
            self.mock_conversation,
            self.mock_client,
            self.mock_display,
        )
        assert result is True
        self.mock_conversation.load_from_file.assert_called_once_with("test.json")
        self.mock_display.show_success.assert_called_once()

    def test_load_command_without_file(self):
        """Verifica se '/carregar' sem arquivo mostra erro."""
        result = handle_command(
            "/carregar",
            self.mock_conversation,
            self.mock_client,
            self.mock_display,
        )
        assert result is True
        self.mock_display.show_error.assert_called_once()

    def test_load_command_with_error(self):
        """Verifica se erro ao carregar é tratado."""
        from utils.conversation import ConversationLoadError
        self.mock_conversation.load_from_file.side_effect = ConversationLoadError("Arquivo não encontrado")
        result = handle_command(
            "/carregar nonexistent.json",
            self.mock_conversation,
            self.mock_client,
            self.mock_display,
        )
        assert result is True
        self.mock_display.show_error.assert_called_once()

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


class TestMain:
    """Testes para a função main."""

    @patch("chatbot.Display")
    @patch("chatbot.Config")
    def test_main_config_validation_error(self, mock_config_class, mock_display_class):
        """Verifica se erro de configuração encerra o programa."""
        from chatbot import ConfigurationError

        mock_display = MagicMock()
        mock_display_class.return_value = mock_display
        mock_config_class.validate.side_effect = ConfigurationError("API key missing")

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        mock_display.show_error.assert_called_once()

    @patch("chatbot.Display")
    @patch("chatbot.Config")
    @patch("chatbot.OpenRouterClient")
    @patch("chatbot.ConversationManager")
    def test_main_keyboard_interrupt(
        self, mock_conv_class, mock_client_class, mock_config_class, mock_display_class
    ):
        """Verifica se Ctrl+C encerra graciosamente."""
        mock_display = MagicMock()
        mock_display.prompt_input.side_effect = KeyboardInterrupt()
        mock_display_class.return_value = mock_display

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        main()

        mock_display.show_goodbye.assert_called_once()

    @patch("chatbot.Display")
    @patch("chatbot.Config")
    @patch("chatbot.OpenRouterClient")
    @patch("chatbot.ConversationManager")
    def test_main_empty_input_ignored(
        self, mock_conv_class, mock_client_class, mock_config_class, mock_display_class
    ):
        """Verifica se input vazio é ignorado."""
        mock_display = MagicMock()
        mock_display.prompt_input.side_effect = ["", "   ", "sair"]
        mock_display_class.return_value = mock_display

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        mock_conv = MagicMock()
        mock_conv_class.return_value = mock_conv

        main()

        mock_conv.add_user_message.assert_not_called()

    @patch("chatbot.Display")
    @patch("chatbot.Config")
    @patch("chatbot.OpenRouterClient")
    @patch("chatbot.ConversationManager")
    @patch("chatbot.config")
    def test_main_message_too_long(
        self, mock_config, mock_conv_class, mock_client_class, mock_config_class, mock_display_class
    ):
        """Verifica se mensagem muito longa é rejeitada."""
        mock_config.MAX_MESSAGE_LENGTH = 10
        mock_config.EXIT_COMMANDS = ("sair",)
        mock_config.CLEAR_COMMANDS = ()
        mock_config.SAVE_COMMANDS = ()
        mock_config.HELP_COMMANDS = ()
        mock_config.MODEL_COMMANDS = ()

        mock_display = MagicMock()
        mock_display.prompt_input.side_effect = ["Esta mensagem é muito longa", "sair"]
        mock_display_class.return_value = mock_display

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        mock_conv = MagicMock()
        mock_conv_class.return_value = mock_conv

        main()

        mock_display.show_error.assert_called()
        mock_conv.add_user_message.assert_not_called()

    @patch("chatbot.Display")
    @patch("chatbot.Config")
    @patch("chatbot.OpenRouterClient")
    @patch("chatbot.ConversationManager")
    @patch("chatbot.config")
    def test_main_api_error_removes_user_message(
        self, mock_config, mock_conv_class, mock_client_class, mock_config_class, mock_display_class
    ):
        """Verifica se erro de API remove a mensagem do usuário."""
        from chatbot import APIError

        mock_config.MAX_MESSAGE_LENGTH = 10000
        mock_config.EXIT_COMMANDS = ("sair",)
        mock_config.CLEAR_COMMANDS = ()
        mock_config.SAVE_COMMANDS = ()
        mock_config.HELP_COMMANDS = ()
        mock_config.MODEL_COMMANDS = ()

        mock_display = MagicMock()
        mock_display.prompt_input.side_effect = ["Olá", "sair"]
        mock_display_class.return_value = mock_display

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.send_message_stream.side_effect = APIError("Connection failed")
        mock_client_class.return_value = mock_client

        mock_conv = MagicMock()
        mock_conv.get_messages.return_value = [{"role": "user", "content": "Olá"}]
        mock_conv_class.return_value = mock_conv

        main()

        mock_conv.remove_last_user_message.assert_called_once()
        mock_display.show_error.assert_called()
