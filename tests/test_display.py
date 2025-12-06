"""Testes para o módulo de exibição."""

import pytest
import threading
import time
from unittest.mock import patch, MagicMock
from io import StringIO
from utils.display import Display, RotatingSpinner, StreamingTextDisplay, THINKING_WORDS


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

    def test_repr(self):
        """Verifica representação string do spinner."""
        from rich.console import Console

        console = Console()
        spinner = RotatingSpinner(console)

        assert "RotatingSpinner" in repr(spinner)
        assert "running=False" in repr(spinner)

        spinner.start()
        assert "running=True" in repr(spinner)
        spinner.stop()

    def test_format_tokens_thousands(self):
        """Verifica formatação de tokens em milhares (K)."""
        from rich.console import Console

        console = Console()
        spinner = RotatingSpinner(console)

        assert spinner._format_tokens(1000) == "~1.0K"
        assert spinner._format_tokens(1500) == "~1.5K"
        assert spinner._format_tokens(10000) == "~10.0K"
        assert spinner._format_tokens(999999) == "~1000.0K"

    def test_format_tokens_millions(self):
        """Verifica formatação de tokens em milhões (M)."""
        from rich.console import Console

        console = Console()
        spinner = RotatingSpinner(console)

        assert spinner._format_tokens(1000000) == "~1.0M"
        assert spinner._format_tokens(1500000) == "~1.5M"
        assert spinner._format_tokens(10000000) == "~10.0M"


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

    def test_show_model_changed(self, capsys):
        """Verifica se mudança de modelo é exibida."""
        display = Display()
        display.show_model_changed("anthropic/claude-3")

        captured = capsys.readouterr()
        assert "anthropic/claude-3" in captured.out
        assert "alterado" in captured.out.lower()

    def test_show_history_list_empty(self, capsys):
        """Verifica se lista vazia mostra mensagem apropriada."""
        display = Display()
        display.show_history_list([])

        captured = capsys.readouterr()
        assert "Nenhum arquivo" in captured.out

    def test_show_history_list_with_files(self, capsys):
        """Verifica se lista de arquivos é exibida."""
        display = Display()
        files = [
            ("history_1.json", "2024-01-15T10:30:00", "openai/gpt-4"),
            ("history_2.json", "2024-01-14T09:00:00", "anthropic/claude-3"),
        ]
        display.show_history_list(files)

        captured = capsys.readouterr()
        assert "history_1.json" in captured.out
        assert "history_2.json" in captured.out
        assert "openai/gpt-4" in captured.out
        assert "/carregar" in captured.out

    def test_show_history_list_invalid_timestamp(self, capsys):
        """Verifica fallback para timestamp inválido."""
        display = Display()
        files = [
            ("history_1.json", "invalid-timestamp", "openai/gpt-4"),
            ("history_2.json", "not-a-date", "anthropic/claude-3"),
        ]
        display.show_history_list(files)

        captured = capsys.readouterr()
        assert "invalid-timestamp" in captured.out
        assert "not-a-date" in captured.out

    def test_show_banner(self, capsys):
        """Verifica se o banner é exibido."""
        display = Display()
        display.show_banner()

        captured = capsys.readouterr()
        assert "Chatbot Conversacional" in captured.out
        assert "Vertex" in captured.out

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
        assert "👋" not in captured.out

    def test_repr(self):
        """Verifica representação string do Display."""
        display = Display()

        assert "Display" in repr(display)
        assert "spinner=False" in repr(display)
        assert "streaming=False" in repr(display)

        display.start_spinner()
        assert "spinner=True" in repr(display)
        display.stop_spinner()

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
        assert "~42" in text_str
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

    def test_spinner_double_start_is_safe(self):
        """Iniciar spinner duas vezes não deve criar múltiplas threads."""
        display = Display()

        display.start_spinner()
        first_thread = display.spinner.thread

        display.start_spinner()
        second_thread = display.spinner.thread

        assert first_thread is second_thread
        assert display.spinner.running is True

        display.stop_spinner()

    def test_spinner_shows_approximate_tokens(self):
        """Spinner deve mostrar ~ para indicar tokens aproximados."""
        from rich.console import Console

        console = Console()
        spinner = RotatingSpinner(console)
        spinner.start_time = 0
        spinner.update_tokens(100)

        renderable = spinner._get_renderable()
        text_str = str(renderable)

        assert "~100" in text_str
        assert "tokens" in text_str


class TestStreamingTextDisplay:
    """Testes para exibição de texto em streaming."""

    def test_init(self):
        """Verifica inicialização."""
        from rich.console import Console

        console = Console()
        streaming = StreamingTextDisplay(console)

        assert streaming.running is False
        assert streaming._buffer == ""

    def test_add_chunk(self):
        """Verifica se chunks são adicionados."""
        from rich.console import Console

        console = Console()
        streaming = StreamingTextDisplay(console)

        streaming.add_chunk("Hello")
        streaming.add_chunk(" World")

        assert streaming.get_full_text() == "Hello World"

    def test_thread_safety(self):
        """Verifica se adição de chunks é thread-safe."""
        from rich.console import Console
        import threading

        console = Console()
        streaming = StreamingTextDisplay(console)

        def add_chunks():
            for i in range(100):
                streaming.add_chunk(f"{i}")

        threads = [threading.Thread(target=add_chunks) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        text = streaming.get_full_text()
        assert len(text) > 0

    def test_start_clears_buffer(self):
        """Start deve limpar buffer anterior."""
        from rich.console import Console

        console = Console()
        streaming = StreamingTextDisplay(console)

        streaming.add_chunk("Old text")
        streaming.start()

        assert streaming.get_full_text() == ""
        streaming.stop()

    def test_double_start_is_safe(self):
        """Iniciar duas vezes não deve causar erro."""
        from rich.console import Console

        console = Console()
        streaming = StreamingTextDisplay(console)

        streaming.start()
        streaming.start()

        assert streaming.running is True
        streaming.stop()

    def test_double_stop_is_safe(self):
        """Parar duas vezes não deve causar erro."""
        from rich.console import Console

        console = Console()
        streaming = StreamingTextDisplay(console)

        streaming.start()
        streaming.stop()
        streaming.stop()

        assert streaming.running is False

    def test_repr(self):
        """Verifica representação string do streaming display."""
        from rich.console import Console

        console = Console()
        streaming = StreamingTextDisplay(console)

        assert "StreamingTextDisplay" in repr(streaming)
        assert "running=False" in repr(streaming)
        assert "buffer_size=0" in repr(streaming)

        streaming.add_chunk("Hello World")
        assert "buffer_size=11" in repr(streaming)

    def test_get_renderable_with_content(self):
        """Verifica que Markdown é criado quando buffer tem conteúdo."""
        from rich.console import Console
        from rich.markdown import Markdown

        console = Console()
        streaming = StreamingTextDisplay(console)
        streaming.add_chunk("**Bold text**")

        renderable = streaming._get_renderable()

        assert isinstance(renderable, Markdown)

    def test_buffer_truncation_warning(self, capsys):
        """Verifica se aviso de truncamento é exibido."""
        from rich.console import Console
        from utils.display import MAX_BUFFER_SIZE

        console = Console()
        streaming = StreamingTextDisplay(console)

        streaming.start()
        large_chunk = "x" * (MAX_BUFFER_SIZE + 100)
        streaming.add_chunk(large_chunk)
        streaming.stop()

        captured = capsys.readouterr()
        assert "truncada" in captured.out.lower()
        assert "Dica" in captured.out


class TestDisplayStreaming:
    """Testes para métodos de streaming no Display."""

    def test_display_has_streaming(self):
        """Verifica se Display tem atributo streaming."""
        display = Display()
        assert hasattr(display, 'streaming')
        assert isinstance(display.streaming, StreamingTextDisplay)

    def test_transition_spinner_to_streaming(self):
        """Verifica transição de spinner para streaming."""
        display = Display()

        display.start_spinner()
        assert display.spinner.running is True

        display.transition_spinner_to_streaming()

        assert display.spinner.running is False
        assert display.streaming.running is True

        display.stop_streaming()

    def test_streaming_workflow(self):
        """Testa fluxo completo de streaming."""
        display = Display()

        display.start_streaming()
        display.add_streaming_chunk("Hello")
        display.add_streaming_chunk(" ")
        display.add_streaming_chunk("World")

        result = display.stop_streaming()

        assert result == "Hello World"
        assert display.streaming.running is False

    def test_streaming_with_empty_response(self):
        """Streaming sem chunks deve retornar string vazia."""
        display = Display()

        display.start_streaming()
        result = display.stop_streaming()

        assert result == ""


class TestConcurrentScenarios:
    """Testes de estresse para cenários concorrentes."""

    def test_concurrent_chunk_addition_during_stop(self):
        """Adicionar chunks durante stop não deve causar erro."""
        from rich.console import Console
        import threading
        import time

        console = Console()
        streaming = StreamingTextDisplay(console)
        errors = []

        streaming.start()

        def add_chunks():
            try:
                for i in range(50):
                    streaming.add_chunk(f"chunk{i}")
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        def stop_after_delay():
            time.sleep(0.02)
            streaming.stop()

        add_thread = threading.Thread(target=add_chunks)
        stop_thread = threading.Thread(target=stop_after_delay)

        add_thread.start()
        stop_thread.start()

        add_thread.join()
        stop_thread.join()

        assert len(errors) == 0

    def test_concurrent_spinner_token_updates(self):
        """Múltiplas atualizações de token simultâneas."""
        from rich.console import Console
        import threading

        console = Console()
        spinner = RotatingSpinner(console)

        def update_tokens(start_val):
            for i in range(100):
                spinner.update_tokens(start_val + i)

        threads = [
            threading.Thread(target=update_tokens, args=(i * 100,))
            for i in range(10)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert isinstance(spinner.token_count, int)

    def test_rapid_start_stop_cycles(self):
        """Ciclos rápidos de start/stop não devem causar erro."""
        display = Display()
        errors = []

        def cycle():
            try:
                for _ in range(20):
                    display.start_spinner()
                    display.stop_spinner()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=cycle) for _ in range(3)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert display.spinner.running is False

    def test_concurrent_start_stop_spinner(self):
        """Verifica que start/stop concorrentes não causam race condition."""
        from rich.console import Console

        console = Console()
        spinner = RotatingSpinner(console)
        errors = []
        operations_completed = []

        def start_stop_cycle():
            try:
                for _ in range(10):
                    spinner.start()
                    time.sleep(0.005)
                    spinner.stop()
                    operations_completed.append(True)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=start_stop_cycle) for _ in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert spinner.running is False
        assert len(operations_completed) == 50

    def test_concurrent_streaming_start_stop(self):
        """Verifica que start/stop de streaming é thread-safe."""
        from rich.console import Console

        console = Console()
        streaming = StreamingTextDisplay(console)
        errors = []

        def start_add_stop():
            try:
                for _ in range(10):
                    streaming.start()
                    streaming.add_chunk("test")
                    time.sleep(0.002)
                    streaming.stop()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=start_add_stop) for _ in range(3)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert streaming.running is False

    def test_spinner_state_lock_protects_transitions(self):
        """Verifica que state_lock protege transições de estado.

        Este teste verifica que não há exceções nem estado corrompido
        durante transições rápidas de start/stop, mesmo com observação
        concorrente. O lock garante que operações de transição são atômicas.
        """
        from rich.console import Console

        console = Console()
        spinner = RotatingSpinner(console)
        errors = []

        def monitor_state():
            """Monitor que tenta ler estado durante transições."""
            for _ in range(100):
                try:
                    _ = spinner.running
                    _ = spinner.thread
                    _ = spinner.live
                    _ = spinner._get_renderable()
                except Exception as e:
                    errors.append(f"Monitor error: {e}")
                time.sleep(0.001)

        def toggle_spinner():
            for _ in range(20):
                spinner.start()
                spinner.stop()

        monitor_thread = threading.Thread(target=monitor_state)
        toggle_thread = threading.Thread(target=toggle_spinner)

        monitor_thread.start()
        toggle_thread.start()

        toggle_thread.join()
        monitor_thread.join()

        assert len(errors) == 0
        assert spinner.running is False

    def test_streaming_buffer_integrity(self):
        """Verifica integridade do buffer com escrita concorrente."""
        from rich.console import Console

        console = Console()
        streaming = StreamingTextDisplay(console)
        streaming.start()

        def add_numbered_chunks(prefix):
            for i in range(50):
                streaming.add_chunk(f"{prefix}{i}")

        threads = [
            threading.Thread(target=add_numbered_chunks, args=(f"T{t}_",))
            for t in range(5)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        streaming.stop()
        text = streaming.get_full_text()

        for t in range(5):
            for i in range(50):
                assert f"T{t}_{i}" in text


class TestDisplayCleanup:
    """Testes para o método cleanup do Display."""

    def test_cleanup_stops_running_spinner(self):
        """Cleanup deve parar spinner em execução."""
        display = Display()

        display.start_spinner()
        assert display.spinner.running is True

        display.cleanup()
        assert display.spinner.running is False

    def test_cleanup_stops_running_streaming(self):
        """Cleanup deve parar streaming em execução."""
        display = Display()

        display.start_streaming()
        assert display.streaming.running is True

        display.cleanup()
        assert display.streaming.running is False

    def test_cleanup_handles_both_running(self):
        """Cleanup deve lidar com spinner e streaming rodando."""
        display = Display()

        display.start_spinner()
        display.transition_spinner_to_streaming()
        display.start_spinner()

        display.cleanup()

        assert display.spinner.running is False
        assert display.streaming.running is False

    def test_cleanup_safe_when_nothing_running(self):
        """Cleanup não deve causar erro quando nada está rodando."""
        display = Display()

        display.cleanup()

        assert display.spinner.running is False
        assert display.streaming.running is False

    def test_cleanup_multiple_times_safe(self):
        """Cleanup pode ser chamado múltiplas vezes sem erro."""
        display = Display()

        display.start_spinner()
        display.cleanup()
        display.cleanup()
        display.cleanup()

        assert display.spinner.running is False
