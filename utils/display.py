"""Formatação e exibição no terminal."""

import readline  # Habilita navegação com setas e histórico
import random
import time
import threading
import sys
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.spinner import Spinner
from rich.live import Live
from rich.text import Text
from .config import config


THINKING_WORDS = [
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

    def _get_renderable(self):
        char = self.spinner_chars[self.char_index]
        word = THINKING_WORDS[self.word_index]
        elapsed = int(time.time() - self.start_time)
        return Text.assemble(
            (char, "cyan"),
            " ",
            (f"{word}…", "dim"),
            (" (esc para interromper", "dim"),
            (" · ", "dim"),
            (f"{elapsed}s", "dim"),
            (")", "dim"),
        )

    def _animate(self):
        self.last_word_change = time.time()
        while self.running:
            if time.time() - self.last_word_change >= self.word_change_interval:
                self.word_index = (self.word_index + 1) % len(THINKING_WORDS)
                self.last_word_change = time.time()

            self.live.update(self._get_renderable())
            self.char_index = (self.char_index + 1) % len(self.spinner_chars)
            time.sleep(0.08)

    def start(self):
        self.running = True
        self.start_time = time.time()
        self.word_index = random.randint(0, len(THINKING_WORDS) - 1)
        self.live = Live(self._get_renderable(), console=self.console, transient=True, refresh_per_second=12)
        self.live.start()
        self.thread = threading.Thread(target=self._animate, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
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
    [bold yellow]>[/bold yellow] [italic]Powered by OpenRouter[/italic]
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

    def show_user_message(self, message: str) -> None:
        """Exibe uma mensagem do usuário."""
        pass  # Não precisamos exibir novamente, já foi digitado

    def show_bot_message(self, message: str) -> None:
        """Exibe uma resposta do bot com suporte a Markdown."""
        self.console.print()
        md = Markdown(message)
        self.console.print(md)
        self.console.print()

    def show_error(self, message: str) -> None:
        """Exibe uma mensagem de erro."""
        self.console.print(f"\n[bold red]✗[/bold red] {message}\n")

    def show_warning(self, message: str) -> None:
        """Exibe um aviso."""
        self.console.print(f"[bold yellow]![/bold yellow] {message}")

    def show_success(self, message: str) -> None:
        """Exibe uma mensagem de sucesso."""
        self.console.print(f"[bold green]✓[/bold green] {message}")

    def show_info(self, message: str) -> None:
        """Exibe uma informação."""
        self.console.print(f"[dim]{message}[/dim]")

    def show_goodbye(self) -> None:
        """Exibe mensagem de despedida."""
        self.console.print()
        self.console.print("[dim]Até logo![/dim] 👋")
        self.console.print()

    def start_spinner(self) -> None:
        """Inicia o spinner de carregamento."""
        self.spinner.start()

    def stop_spinner(self) -> None:
        """Para o spinner de carregamento."""
        self.spinner.stop()

    def show_model_info(self, model: str) -> None:
        """Exibe informação sobre o modelo atual."""
        self.console.print(f"\n[dim]Modelo:[/dim] [cyan]{model}[/cyan]\n")

    def prompt_input(self) -> str:
        """Solicita entrada do usuário."""
        try:
            return input("\033[1;36m>\033[0m ")
        except EOFError:
            return "sair"
