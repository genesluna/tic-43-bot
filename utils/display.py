"""Formatação e exibição no terminal."""

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.text import Text
from rich.spinner import Spinner
from rich.live import Live
from .config import config


class Display:
    """Gerencia a exibição formatada no terminal."""

    def __init__(self):
        self.console = Console()

    def show_banner(self) -> None:
        """Exibe o banner de boas-vindas."""
        banner = Text()
        banner.append("CHATBOT IA", style="bold cyan")
        banner.append(" - Projeto TIC43", style="dim")

        self.console.print(
            Panel(
                banner,
                border_style="cyan",
                padding=(1, 2),
            )
        )
        self.console.print()

    def show_help(self) -> None:
        """Exibe os comandos disponíveis."""
        help_text = """
[bold]Comandos disponíveis:[/bold]

  [cyan]sair[/cyan], [cyan]exit[/cyan], [cyan]quit[/cyan]  - Encerra o chatbot
  [cyan]/limpar[/cyan], [cyan]/clear[/cyan]    - Limpa o histórico da conversa
  [cyan]/salvar[/cyan], [cyan]/save[/cyan]     - Salva o histórico em arquivo
  [cyan]/ajuda[/cyan], [cyan]/help[/cyan]      - Mostra esta mensagem
  [cyan]/modelo[/cyan]             - Mostra o modelo atual
"""
        self.console.print(Panel(help_text, title="Ajuda", border_style="blue"))

    def show_user_message(self, message: str) -> None:
        """Exibe uma mensagem do usuário."""
        self.console.print(f"[bold green]Você:[/bold green] {message}")

    def show_bot_message(self, message: str) -> None:
        """Exibe uma resposta do bot com suporte a Markdown."""
        self.console.print("[bold cyan]Bot:[/bold cyan]")
        md = Markdown(message)
        self.console.print(md)
        self.console.print()

    def show_error(self, message: str) -> None:
        """Exibe uma mensagem de erro."""
        self.console.print(f"[bold red]Erro:[/bold red] {message}")

    def show_warning(self, message: str) -> None:
        """Exibe um aviso."""
        self.console.print(f"[bold yellow]Aviso:[/bold yellow] {message}")

    def show_success(self, message: str) -> None:
        """Exibe uma mensagem de sucesso."""
        self.console.print(f"[bold green]✓[/bold green] {message}")

    def show_info(self, message: str) -> None:
        """Exibe uma informação."""
        self.console.print(f"[dim]{message}[/dim]")

    def show_goodbye(self) -> None:
        """Exibe mensagem de despedida."""
        self.console.print()
        self.console.print(
            Panel(
                "[bold cyan]Até logo! Foi um prazer conversar com você.[/bold cyan]",
                border_style="cyan",
            )
        )

    def get_spinner(self) -> Live:
        """Retorna um contexto de spinner para carregamento."""
        spinner = Spinner("dots", text="Pensando...", style="cyan")
        return Live(spinner, console=self.console, transient=True)

    def show_model_info(self, model: str) -> None:
        """Exibe informação sobre o modelo atual."""
        self.console.print(f"[dim]Modelo atual:[/dim] [cyan]{model}[/cyan]")

    def prompt_input(self) -> str:
        """Solicita entrada do usuário."""
        try:
            return self.console.input("[bold green]Você:[/bold green] ")
        except EOFError:
            return "sair"
