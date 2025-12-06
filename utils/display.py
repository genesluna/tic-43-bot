"""Formatação e exibição no terminal."""

import logging
import random
import time
import threading

try:
    import readline  # noqa: F401 - Unix/Linux input history/editing
    del readline
except ImportError:
    try:
        import pyreadline3  # noqa: F401 - Windows input history/editing
        del pyreadline3
    except ImportError:
        pass
from datetime import datetime
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live
from rich.text import Text

logger = logging.getLogger(__name__)

SPINNER_REFRESH_RATE = 12  # Hz - spinner animation refresh rate
STREAMING_REFRESH_RATE = 10  # Hz - streaming text refresh rate
WORD_CHANGE_INTERVAL = 5.0  # seconds - interval between rotating words
ANIMATION_FRAME_INTERVAL = 0.08  # seconds - delay between animation frames
THREAD_JOIN_TIMEOUT = 0.2  # seconds - max wait for thread cleanup

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
    """Spinner com palavras rotativas usando Rich Live."""

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
        self._stop_event: threading.Event = threading.Event()

    def _get_renderable(self) -> Text:
        char = self.spinner_chars[self.char_index]
        word = THINKING_WORDS[self.word_index]
        elapsed = int(time.time() - self.start_time)
        with self._lock:
            current_tokens = self._token_count
        parts: list[tuple[str, str] | str] = [
            (char, "cyan"),
            " ",
            (f"{word}…", "dim"),
            (" (Ctrl+C para cancelar", "dim"),
            (" · ", "dim"),
            (f"{elapsed}s", "dim"),
        ]
        if current_tokens > 0:
            parts.extend([
                (" · ", "dim"),
                (f"~{current_tokens}", "dim"),
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

    def _animate(self) -> None:
        self.last_word_change = time.time()
        while not self._stop_event.wait(timeout=ANIMATION_FRAME_INTERVAL):
            if time.time() - self.last_word_change >= self.word_change_interval:
                self.word_index = (self.word_index + 1) % len(THINKING_WORDS)
                self.last_word_change = time.time()

            live = self.live
            if live is None:
                break
            try:
                live.update(self._get_renderable())
            except Exception:
                break
            self.char_index = (self.char_index + 1) % len(self.spinner_chars)

    def start(self) -> None:
        """Inicia o spinner. Seguro para chamadas múltiplas."""
        if self.running:
            return
        self.running = True
        self._stop_event.clear()
        self.start_time = time.time()
        with self._lock:
            self._token_count = 0
        self.word_index = random.randint(0, len(THINKING_WORDS) - 1)
        self.live = Live(self._get_renderable(), console=self.console, transient=True, refresh_per_second=SPINNER_REFRESH_RATE)
        self.live.start()
        self.thread = threading.Thread(target=self._animate, daemon=True)
        self.thread.start()
        logger.debug("Spinner iniciado")

    def stop(self) -> None:
        """Para o spinner. Seguro para chamadas múltiplas."""
        self._stop_event.set()
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=THREAD_JOIN_TIMEOUT)
        self.thread = None
        if self.live:
            self.live.stop()
            self.live = None
        elapsed = time.time() - self.start_time if self.start_time else 0
        logger.debug(f"Spinner parado após {elapsed:.1f}s")


class StreamingTextDisplay:
    """Exibição de texto em streaming com buffer thread-safe."""

    def __init__(self, console: Console) -> None:
        self.console: Console = console
        self.live: Live | None = None
        self.running: bool = False
        self._buffer: str = ""
        self._lock: threading.Lock = threading.Lock()

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
            self._buffer += chunk
            if not self.running or self.live is None:
                return
            current_text = self._buffer

        renderable = Markdown(current_text) if current_text else Text("")
        try:
            if self.live is not None:
                self.live.update(renderable)
        except Exception as e:
            logger.debug(f"Falha ao atualizar display: {e}")

    def get_full_text(self) -> str:
        """Retorna texto completo acumulado."""
        with self._lock:
            return self._buffer

    def start(self) -> None:
        """Inicia exibição em streaming."""
        if self.running:
            return

        self.running = True
        with self._lock:
            self._buffer = ""

        self.console.print()
        self.live = Live(
            self._get_renderable(),
            console=self.console,
            refresh_per_second=STREAMING_REFRESH_RATE,
            vertical_overflow="visible",
        )
        self.live.start()

    def stop(self) -> None:
        """Para exibição e finaliza."""
        with self._lock:
            self.running = False
            current_text = self._buffer
            total_chars = len(self._buffer)
        if self.live:
            renderable = Markdown(current_text) if current_text else Text("")
            self.live.update(renderable)
            self.live.stop()
            self.live = None
        logger.debug(f"Streaming finalizado ({total_chars} chars recebidos)")
        self.console.print()


class Display:
    """Gerencia a exibição formatada no terminal."""

    def __init__(self) -> None:
        self.console: Console = Console()
        self.spinner: RotatingSpinner = RotatingSpinner(self.console)
        self.streaming: StreamingTextDisplay = StreamingTextDisplay(self.console)

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
            ("/modelo [nome]", "Mostra ou altera o modelo atual"),
        ]
        for cmd, desc in commands:
            self.console.print(f"  [bold cyan]{cmd:<20}[/bold cyan] [dim]{desc}[/dim]")
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
            self.console.print("[bold cyan]>[/bold cyan] ", end="")
            return input()
        except EOFError:
            return "sair"
