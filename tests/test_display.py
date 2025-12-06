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

    def test_update_spinner_tokens(self):
        """Verifica se o contador de tokens pode ser atualizado."""
        display = Display()

        display.start_spinner()
        display.update_spinner_tokens(50)

        assert display.spinner.token_count == 50

        display.stop_spinner()

    def test_spinner_token_count_reset_on_start(self):
        """Verifica se o contador de tokens é resetado ao iniciar."""
        display = Display()

        display.start_spinner()
        display.update_spinner_tokens(100)
        display.stop_spinner()

        display.start_spinner()
        assert display.spinner.token_count == 0
        display.stop_spinner()

    def test_spinner_renderable_with_tokens(self):
        """Verifica se o renderable inclui tokens quando > 0."""
        from rich.console import Console

        console = Console()
        spinner = RotatingSpinner(console)
        spinner.start_time = 0
        spinner.update_tokens(42)

        renderable = spinner._get_renderable()
        text_str = str(renderable)
        assert "42" in text_str
        assert "tokens" in text_str

    def test_spinner_double_stop_is_safe(self):
        """Parar spinner duas vezes não deve causar erro."""
        display = Display()

        display.start_spinner()
        display.stop_spinner()
        display.stop_spinner()

        assert display.spinner.running is False

    def test_spinner_thread_is_daemon(self):
        """Thread do spinner deve ser daemon."""
        display = Display()

        display.start_spinner()
        assert display.spinner.thread.daemon is True
        display.stop_spinner()

    def test_spinner_stop_event_is_set_on_stop(self):
        """_stop_event deve ser setado ao parar."""
        display = Display()

        display.start_spinner()
        assert not display.spinner._stop_event.is_set()

        display.stop_spinner()
        assert display.spinner._stop_event.is_set()

    @patch("builtins.input", side_effect=KeyboardInterrupt)
    def test_prompt_input_keyboard_interrupt(self, mock_input, capsys):
        """KeyboardInterrupt no input deve propagar."""
        display = Display()

        with pytest.raises(KeyboardInterrupt):
            display.prompt_input()

    def test_show_bot_message_empty(self, capsys):
        """Mensagem vazia não deve causar erro."""
        display = Display()
        display.show_bot_message("")

        captured = capsys.readouterr()
        assert captured.out is not None

    def test_show_bot_message_with_code_block(self, capsys):
        """Code block em markdown deve ser renderizado."""
        display = Display()
        display.show_bot_message("```python\nprint('hello')\n```")

        captured = capsys.readouterr()
        assert "print" in captured.out

    def test_spinner_token_count_thread_safe(self):
        """Acesso ao token_count deve ser thread-safe."""
        from rich.console import Console
        import threading

        console = Console()
        spinner = RotatingSpinner(console)

        results = []

        def update_tokens():
            for i in range(100):
                spinner.update_tokens(i)
                results.append(spinner.token_count)

        threads = [threading.Thread(target=update_tokens) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 500
        assert all(isinstance(r, int) for r in results)
