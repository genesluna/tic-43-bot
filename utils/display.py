"""Formatação e exibição no terminal."""

import random
import readline
import time

del readline
import threading
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live
from rich.text import Text


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

    def __init__(self, console: Console):
        self.console = console
        self.live = None
        self.running = False
        self.thread = None
        self.spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        self.char_index = 0
        self.word_index = 0
        self.word_change_interval = 5.0
        self.last_word_change = 0
        self.start_time = 0
        self._token_count = 0
        self._lock = threading.Lock()
        self._stop_event = threading.Event()

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

    def _animate(self):
        self.last_word_change = time.time()
        while not self._stop_event.wait(timeout=0.08):
            if time.time() - self.last_word_change >= self.word_change_interval:
                self.word_index = (self.word_index + 1) % len(THINKING_WORDS)
                self.last_word_change = time.time()

            self.live.update(self._get_renderable())
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
        self.live = Live(self._get_renderable(), console=self.console, transient=True, refresh_per_second=12)
        self.live.start()
        self.thread = threading.Thread(target=self._animate, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        """Para o spinner. Seguro para chamadas múltiplas."""
        self.running = False
        self._stop_event.set()
        if self.thread:
            self.thread.join(timeout=0.2)
        if self.live:
            self.live.stop()


class Display:
    """Gerencia a exibição formatada no terminal."""

    def __init__(self):
        self.console = Console()
        self.spinner = RotatingSpinner(self.console)

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
            ("/ajuda, /help", "Mostra esta mensagem"),
            ("/modelo", "Mostra o modelo atual"),
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

    def show_model_info(self, model: str) -> None:
        """Exibe informação sobre o modelo atual."""
        self.console.print(f"\n[dim]Modelo:[/dim] [cyan]{model}[/cyan]\n")

    def prompt_input(self) -> str:
        """Solicita entrada do usuário."""
        try:
            self.console.print("[bold cyan]>[/bold cyan] ", end="")
            return input()
        except EOFError:
            return "sair"
