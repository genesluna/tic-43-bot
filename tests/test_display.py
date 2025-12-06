"""Testes para o módulo de exibição."""

import pytest
from unittest.mock import patch, MagicMock
from io import StringIO
from utils.display import Display, RotatingSpinner, THINKING_WORDS


class TestThinkingWords:
    """Testes para as palavras do spinner."""

    def test_thinking_words_not_empty(self):
        """Verifica se a lista de palavras não está vazia."""
        assert len(THINKING_WORDS) > 0

    def test_thinking_words_are_strings(self):
        """Verifica se todas as palavras são strings."""
        assert all(isinstance(word, str) for word in THINKING_WORDS)

    def test_thinking_words_minimum_count(self):
        """Verifica se há pelo menos 10 palavras."""
        assert len(THINKING_WORDS) >= 10


class TestRotatingSpinner:
    """Testes para a classe RotatingSpinner."""

    def test_init(self):
        """Verifica se o spinner é inicializado corretamente."""
        from rich.console import Console

        console = Console()
        spinner = RotatingSpinner(console)

        assert spinner.running is False
        assert spinner.thread is None
        assert spinner.word_change_interval == 5.0

    def test_spinner_chars(self):
        """Verifica se os caracteres do spinner estão definidos."""
        from rich.console import Console

        console = Console()
        spinner = RotatingSpinner(console)

        assert len(spinner.spinner_chars) > 0

    def test_get_renderable(self):
        """Verifica se o renderable é gerado corretamente."""
        from rich.console import Console

        console = Console()
        spinner = RotatingSpinner(console)

        renderable = spinner._get_renderable()

        assert renderable is not None


class TestDisplay:
    """Testes para a classe Display."""

    def test_init(self):
        """Verifica se o Display é inicializado corretamente."""
        display = Display()

        assert display.console is not None
        assert display.spinner is not None

    def test_show_success(self, capsys):
        """Verifica se mensagem de sucesso é exibida."""
        display = Display()
        display.show_success("Operação concluída")

        captured = capsys.readouterr()
        assert "Operação concluída" in captured.out

    def test_show_error(self, capsys):
        """Verifica se mensagem de erro é exibida."""
        display = Display()
        display.show_error("Algo deu errado")

        captured = capsys.readouterr()
        assert "Algo deu errado" in captured.out

    def test_show_warning(self, capsys):
        """Verifica se mensagem de aviso é exibida."""
        display = Display()
        display.show_warning("Atenção")

        captured = capsys.readouterr()
        assert "Atenção" in captured.out

    def test_show_info(self, capsys):
        """Verifica se mensagem de informação é exibida."""
        display = Display()
        display.show_info("Informação importante")

        captured = capsys.readouterr()
        assert "Informação importante" in captured.out

    def test_show_model_info(self, capsys):
        """Verifica se informação do modelo é exibida."""
        display = Display()
        display.show_model_info("openai/gpt-4o-mini")

        captured = capsys.readouterr()
        assert "openai/gpt-4o-mini" in captured.out

    def test_show_banner(self, capsys):
        """Verifica se o banner é exibido."""
        display = Display()
        display.show_banner()

        captured = capsys.readouterr()
        assert "Chatbot Conversacional" in captured.out
        assert "OpenRouter" in captured.out

    def test_show_help(self, capsys):
        """Verifica se a ajuda é exibida."""
        display = Display()
        display.show_help()

        captured = capsys.readouterr()
        assert "sair" in captured.out
        assert "/limpar" in captured.out
        assert "/salvar" in captured.out
        assert "/ajuda" in captured.out
        assert "/modelo" in captured.out

    def test_show_goodbye(self, capsys):
        """Verifica se a mensagem de despedida é exibida."""
        display = Display()
        display.show_goodbye()

        captured = capsys.readouterr()
        assert "Até logo" in captured.out

    def test_show_bot_message(self, capsys):
        """Verifica se mensagem do bot é exibida."""
        display = Display()
        display.show_bot_message("Esta é uma resposta do bot.")

        captured = capsys.readouterr()
        assert "Esta é uma resposta do bot." in captured.out

    def test_show_bot_message_with_markdown(self, capsys):
        """Verifica se markdown é renderizado na mensagem do bot."""
        display = Display()
        display.show_bot_message("**Texto em negrito**")

        captured = capsys.readouterr()
        # O markdown é renderizado, então o texto deve estar presente
        assert "Texto em negrito" in captured.out

    @patch("builtins.input", return_value="teste de input")
    def test_prompt_input(self, mock_input):
        """Verifica se o prompt de input funciona."""
        display = Display()
        result = display.prompt_input()

        assert result == "teste de input"

    @patch("builtins.input", side_effect=EOFError)
    def test_prompt_input_eof(self, mock_input):
        """Verifica se EOF retorna 'sair'."""
        display = Display()
        result = display.prompt_input()

        assert result == "sair"

    def test_start_stop_spinner(self):
        """Verifica se o spinner pode ser iniciado e parado."""
        display = Display()

        display.start_spinner()
        assert display.spinner.running is True

        display.stop_spinner()
        assert display.spinner.running is False
