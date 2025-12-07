"""Formatação e exibição no terminal."""

import logging
import random
import time
import threading

# Importa readline para habilitar edição de linha e histórico no input().
# É um import por efeito colateral que melhora a experiência no terminal.
try:
    import readline  # noqa: F401
except ImportError:
    try:
        import pyreadline3  # noqa: F401
    except ImportError:
        pass
from datetime import datetime
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live
from rich.text import Text

__all__ = ["Display", "RotatingSpinner", "StreamingTextDisplay", "THINKING_WORDS"]

logger = logging.getLogger(__name__)

SPINNER_REFRESH_RATE = 12  # Hz - taxa de atualização do spinner
STREAMING_REFRESH_RATE = 10  # Hz - taxa de atualização do streaming
WORD_CHANGE_INTERVAL = 5.0  # segundos - intervalo entre rotação de palavras
ANIMATION_FRAME_INTERVAL = 0.08  # segundos - atraso entre frames da animação
THREAD_JOIN_TIMEOUT = 0.2  # segundos - tempo máximo para encerrar thread
MAX_BUFFER_SIZE = 1_000_000  # bytes - limite máximo do buffer de streaming

THINKING_WORDS: list[str] = [
    "Pensando",
    "Analisando",
    "Processando",
    "Refletindo",
    "Raciocinando",
    "Ponderando",
    "Elaborando",
    "Formulando",
    "Gerando",
    "Avaliando",
    "Sintetizando",
    "Explorando",
    "Investigando",
    "Organizando",
    "Criando",
    "Construindo",
]


class RotatingSpinner:
    """Spinner com palavras rotativas usando Rich Live.

    Thread-safety: Usa _state_lock para proteger transições start/stop.
    O padrão é: capturar referências dentro do lock, fazer cleanup fora.
    """

    def __init__(self, console: Console) -> None:
        self.console: Console = console
        self.live: Live | None = None
        self.running: bool = False
        self.thread: threading.Thread | None = None
        self.spinner_chars: str = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        self.char_index: int = 0
        self.word_index: int = 0
        self.word_change_interval: float = WORD_CHANGE_INTERVAL
        self.last_word_change: float = 0
        self.start_time: float = 0
        self._token_count: int = 0
        self._lock: threading.Lock = threading.Lock()
        self._state_lock: threading.Lock = threading.Lock()
        self._stop_event: threading.Event = threading.Event()

    def __repr__(self) -> str:
        return f"RotatingSpinner(running={self.running})"

    def _get_renderable(self) -> Text:
        with self._lock:
            char_idx = self.char_index
            word_idx = self.word_index
            start = self.start_time
            tokens = self._token_count

        char = self.spinner_chars[char_idx % len(self.spinner_chars)]
        word = THINKING_WORDS[word_idx % len(THINKING_WORDS)]
        elapsed = int(time.time() - start) if start else 0

        parts: list[tuple[str, str] | str] = [
            (char, "cyan"),
            " ",
            (f"{word}…", "dim"),
            (" (Ctrl+C para cancelar", "dim"),
            (" · ", "dim"),
            (f"{elapsed}s", "dim"),
        ]
        if tokens > 0:
            parts.extend([
                (" · ", "dim"),
                ("↓ ", "cyan"),
                (self._format_tokens(tokens), "cyan"),
                (" tokens", "dim"),
            ])
        parts.append((")", "dim"))
        return Text.assemble(*parts)

    def update_tokens(self, count: int) -> None:
        """Atualiza o contador de tokens (thread-safe)."""
        with self._lock:
            self._token_count = count

    @property
    def token_count(self) -> int:
        """Retorna o contador de tokens (thread-safe)."""
        with self._lock:
            return self._token_count

    def _format_tokens(self, count: int) -> str:
        """Formata contagem de tokens para exibição legível."""
        if count >= 1_000_000:
            return f"{count / 1_000_000:.1f}m"
        if count >= 1_000:
            return f"{count / 1_000:.1f}k"
        return str(count)

    def _animate(self) -> None:
        last_word_change = time.time()
        while not self._stop_event.wait(timeout=ANIMATION_FRAME_INTERVAL):
            with self._lock:
                live = self.live
                if live is None or not self.running:
                    break

                if time.time() - last_word_change >= self.word_change_interval:
                    self.word_index = (self.word_index + 1) % len(THINKING_WORDS)
                    last_word_change = time.time()

                self.char_index = (self.char_index + 1) % len(self.spinner_chars)

            # Null check outside lock - live was captured while valid but could
            # be stopped by another thread between lock release and update call
            if live is not None:
                try:
                    live.update(self._get_renderable())
                except Exception as e:
                    logger.debug("Animação do spinner interrompida: %s", e)
                    break

    def start(self) -> None:
        """Inicia o spinner (thread-safe)."""
        with self._state_lock:
            if self.running:
                return
            self.running = True
            self._stop_event.clear()

            with self._lock:
                self.start_time = time.time()
                self._token_count = 0
                self.char_index = 0
                self.word_index = random.randint(0, len(THINKING_WORDS) - 1)

            self.live = Live(
                self._get_renderable(),
                console=self.console,
                transient=True,
                refresh_per_second=SPINNER_REFRESH_RATE
            )
            self.live.start()
            self.thread = threading.Thread(target=self._animate, daemon=True)
            self.thread.start()
            logger.debug("Spinner iniciado")

    def stop(self) -> None:
        """Para o spinner (thread-safe)."""
        with self._state_lock:
            if not self.running:
                return

            self._stop_event.set()
            self.running = False

            with self._lock:
                thread = self.thread
                live = self.live
                start_time = self.start_time
                self.thread = None
                self.live = None

        if thread and thread.is_alive():
            thread.join(timeout=THREAD_JOIN_TIMEOUT)
            if thread.is_alive():
                logger.warning("Thread do spinner não parou dentro do timeout")

        if live:
            try:
                live.stop()
            except Exception as e:
                logger.debug("Erro ao parar Live do spinner: %s", e)

        elapsed = time.time() - start_time if start_time else 0
        logger.debug("Spinner parado após %.1fs", elapsed)


class StreamingTextDisplay:
    """Exibição de texto em streaming com buffer thread-safe.

    Thread-safety: Usa _state_lock para proteger transições start/stop,
    e _lock para proteger acesso ao buffer. O padrão é: capturar
    referências dentro do lock, fazer operações de UI fora.
    """

    def __init__(self, console: Console) -> None:
        self.console: Console = console
        self.live: Live | None = None
        self.running: bool = False
        self._buffer: str = ""
        self._lock: threading.Lock = threading.Lock()
        self._state_lock: threading.Lock = threading.Lock()
        self._truncated: bool = False

    def __repr__(self) -> str:
        with self._lock:
            buffer_size = len(self._buffer)
        return f"StreamingTextDisplay(running={self.running}, buffer_size={buffer_size})"

    def _get_renderable(self) -> Markdown | Text:
        """Retorna o texto atual como Markdown."""
        with self._lock:
            current_text = self._buffer

        if not current_text:
            return Text("")

        return Markdown(current_text)

    def add_chunk(self, chunk: str) -> None:
        """Adiciona chunk ao buffer (thread-safe)."""
        with self._lock:
            if len(self._buffer) + len(chunk) > MAX_BUFFER_SIZE:
                if not self._truncated:
                    logger.warning("Limite do buffer atingido, resposta truncada")
                    self._truncated = True
                return
            self._buffer += chunk
            if not self.running:
                return
            live = self.live
            current_text = self._buffer

        if live is not None:
            renderable = Markdown(current_text) if current_text else Text("")
            try:
                live.update(renderable)
            except Exception as e:
                logger.debug("Falha ao atualizar display: %s", e)

    def get_full_text(self) -> str:
        """Retorna texto completo acumulado."""
        with self._lock:
            return self._buffer

    def start(self) -> None:
        """Inicia exibição em streaming (thread-safe)."""
        with self._state_lock:
            if self.running:
                return

            self.running = True
            with self._lock:
                self._buffer = ""
                self._truncated = False

            self.console.print()
            self.live = Live(
                self._get_renderable(),
                console=self.console,
                refresh_per_second=STREAMING_REFRESH_RATE,
                vertical_overflow="visible",
            )
            self.live.start()

    def stop(self) -> None:
        """Para exibição e finaliza (thread-safe)."""
        with self._state_lock:
            if not self.running:
                return

            self.running = False
            with self._lock:
                current_text = self._buffer
                total_chars = len(self._buffer)
                was_truncated = self._truncated
                live = self.live
                self.live = None

        if live:
            renderable = Markdown(current_text) if current_text else Text("")
            try:
                live.update(renderable)
                live.stop()
            except Exception as e:
                logger.debug("Erro ao parar Live do streaming: %s", e)

        logger.debug("Streaming finalizado (%d chars recebidos)", total_chars)
        self.console.print()
        if was_truncated:
            self.console.print()
            self.console.print(
                "[bold yellow]⚠ Resposta truncada[/bold yellow] "
                f"[dim](limite de {MAX_BUFFER_SIZE // 1_000_000}MB atingido)[/dim]"
            )
            self.console.print("[dim]Dica: divida sua pergunta em partes menores para respostas completas.[/dim]")


class Display:
    """Gerencia a exibição formatada no terminal."""

    def __init__(self) -> None:
        self.console: Console = Console()
        self.spinner: RotatingSpinner = RotatingSpinner(self.console)
        self.streaming: StreamingTextDisplay = StreamingTextDisplay(self.console)

    def __repr__(self) -> str:
        return f"Display(spinner={self.spinner.running}, streaming={self.streaming.running})"

    def cleanup(self) -> None:
        """Para spinner e streaming de forma segura, ignorando erros."""
        if self.spinner.running:
            try:
                self.spinner.stop()
            except Exception as e:
                logger.debug("Erro ao parar spinner durante cleanup: %s", e)
        if self.streaming.running:
            try:
                self.streaming.stop()
            except Exception as e:
                logger.debug("Erro ao parar streaming durante cleanup: %s", e)

    def show_banner(self) -> None:
        """Exibe o banner de boas-vindas."""
        logo = """[bold cyan]
    ████████╗██╗ ██████╗    ██████╗  ██████╗ ████████╗    ██╗  ██╗██████╗
    ╚══██╔══╝██║██╔════╝    ██╔══██╗██╔═══██╗╚══██╔══╝    ██║  ██║╚════██╗
       ██║   ██║██║         ██████╔╝██║   ██║   ██║       ███████║ █████╔╝
       ██║   ██║██║         ██╔══██╗██║   ██║   ██║       ╚════██║ ╚═══██╗
       ██║   ██║╚██████╗    ██████╔╝╚██████╔╝   ██║            ██║██████╔╝
       ╚═╝   ╚═╝ ╚═════╝    ╚═════╝  ╚═════╝    ╚═╝            ╚═╝╚═════╝[/bold cyan]

    [bold magenta]>[/bold magenta] [bold white]Chatbot Conversacional com IA Generativa[/bold white]
    [bold yellow]>[/bold yellow] [italic]Powered by Vertex[/italic]
"""
        self.console.print(logo)
        self.console.print()

    def show_help(self) -> None:
        """Exibe os comandos disponíveis."""
        self.console.print()
        self.console.print("[bold dim]Comandos disponíveis:[/bold dim]")
        self.console.print()
        commands = [
            ("sair, exit, quit", "Encerra o chatbot"),
            ("/limpar, /clear", "Limpa o histórico da conversa"),
            ("/salvar, /save", "Salva o histórico em arquivo"),
            ("/listar, /list", "Lista históricos salvos"),
            ("/carregar, /load", "Carrega histórico de arquivo"),
            ("/ajuda, /help", "Mostra esta mensagem"),
            ("/modelo, /model \\[nome]", "Mostra ou altera o modelo atual"),
            ("/streaming, /stream", "Alterna modo streaming on/off"),
        ]
        for cmd, desc in commands:
            self.console.print(f"  [bold cyan]{cmd:<28}[/bold cyan] [dim]{desc}[/dim]")
        self.console.print()

    def show_bot_message(self, message: str) -> None:
        """Exibe uma resposta do bot com suporte a Markdown."""
        self.console.print()
        md = Markdown(message)
        self.console.print(md)
        self.console.print()

    def show_error(self, message: str) -> None:
        """Exibe uma mensagem de erro."""
        self.console.print(f"\n[bold red]✗[/bold red] {message}\n")

    def show_success(self, message: str) -> None:
        """Exibe uma mensagem de sucesso."""
        self.console.print(f"[bold green]✓[/bold green] {message}")

    def show_info(self, message: str) -> None:
        """Exibe uma informação."""
        self.console.print(f"[dim]{message}[/dim]")

    def show_goodbye(self) -> None:
        """Exibe mensagem de despedida."""
        self.console.print()
        self.console.print("[dim]Até logo![/dim]")
        self.console.print()

    def start_spinner(self) -> None:
        """Inicia o spinner de carregamento."""
        self.spinner.start()

    def stop_spinner(self) -> None:
        """Para o spinner de carregamento."""
        self.spinner.stop()

    def update_spinner_tokens(self, count: int) -> None:
        """Atualiza o contador de tokens no spinner."""
        self.spinner.update_tokens(count)

    def start_streaming(self) -> None:
        """Inicia modo de exibição em streaming."""
        self.streaming.start()

    def add_streaming_chunk(self, chunk: str) -> None:
        """Adiciona chunk ao streaming."""
        self.streaming.add_chunk(chunk)

    def stop_streaming(self) -> str:
        """Para streaming e retorna texto completo."""
        self.streaming.stop()
        return self.streaming.get_full_text()

    def transition_spinner_to_streaming(self) -> None:
        """Transiciona do spinner para modo streaming."""
        self.stop_spinner()
        self.start_streaming()

    def show_model_info(self, model: str) -> None:
        """Exibe informação sobre o modelo atual."""
        self.console.print(f"\n[dim]Modelo:[/dim] [cyan]{model}[/cyan]\n")

    def show_model_changed(self, model: str) -> None:
        """Exibe confirmação de troca de modelo."""
        self.console.print(f"[bold green]✓[/bold green] Modelo alterado para: [cyan]{model}[/cyan]")

    def show_history_list(self, files: list[tuple[str, str, str]]) -> None:
        """Exibe lista de arquivos de histórico disponíveis."""
        self.console.print()
        if not files:
            self.console.print("[dim]Nenhum arquivo de histórico encontrado.[/dim]")
            self.console.print()
            return

        self.console.print("[bold dim]Arquivos de histórico disponíveis:[/bold dim]")
        self.console.print()
        for filename, timestamp, model in files:
            try:
                dt = datetime.fromisoformat(timestamp)
                formatted_time = dt.strftime("%d/%m/%Y %H:%M")
            except ValueError:
                formatted_time = timestamp
            self.console.print(
                f"  [cyan]{filename:<30}[/cyan] "
                f"[dim]{formatted_time}[/dim] "
                f"[dim]({model})[/dim]"
            )
        self.console.print()
        self.console.print("[dim]Use /carregar <nome_arquivo> para carregar.[/dim]")
        self.console.print()

    def prompt_input(self) -> str:
        """Solicita entrada do usuário."""
        try:
            # Usa marcadores readline (\001 e \002) para indicar caracteres não-imprimíveis
            # Isso evita que o readline conte os códigos ANSI como caracteres visíveis
            prompt = "\001\033[1;36m\002>\001\033[0m\002 "
            return input(prompt)
        except EOFError:
            return "sair"
