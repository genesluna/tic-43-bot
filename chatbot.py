#!/usr/bin/env python3
"""
Chatbot Conversacional com IA - Projeto TIC43

Um chatbot interativo que utiliza a API OpenRouter para
manter conversas contextualizadas com o usuário.
"""

import argparse
import logging
import sys
from enum import Enum, auto
from typing import Sequence

from utils.api import OpenRouterClient, APIError
from utils.conversation import ConversationManager, ConversationLoadError
from utils.display import Display
from utils.config import config, ConfigurationError
from utils.logging_config import setup_logging
from utils.version import __version__

# Aproximação: ~4 caracteres por token (varia por modelo e idioma)
CHARS_PER_TOKEN = 4

logger = logging.getLogger(__name__)


class CommandResult(Enum):
    """Resultado do processamento de comandos."""

    CONTINUE = auto()  # Continua o loop principal
    EXIT = auto()      # Encerra o chatbot
    NOT_COMMAND = auto()  # Não é um comando, processar como mensagem
    TOGGLE_STREAM = auto()  # Alterna modo streaming


def _extract_command_arg(user_input: str, commands: tuple[str, ...]) -> str | None:
    """Extrai argumento de um comando, ou None se não for o comando."""
    user_input_lower = user_input.lower().strip()
    for cmd in commands:
        if user_input_lower.startswith(cmd):
            return user_input[len(cmd):].strip()
    return None


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Processa argumentos de linha de comando."""
    parser = argparse.ArgumentParser(
        prog="chatbot",
        description="Chatbot conversacional com IA via OpenRouter API",
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "-m", "--model",
        metavar="MODEL",
        help="modelo de IA (ex: openai/gpt-4o-mini)",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        metavar="LEVEL",
        help="nível de logging (DEBUG, INFO, WARNING, ERROR)",
    )
    parser.add_argument(
        "--log-file",
        metavar="FILE",
        help="arquivo para salvar logs",
    )
    parser.add_argument(
        "--no-stream",
        action="store_true",
        help="desativa streaming (mostra spinner com tokens)",
    )
    return parser.parse_args(argv)


def handle_command(
    user_input: str,
    conversation: ConversationManager,
    client: OpenRouterClient,
    display: Display,
) -> CommandResult:
    """
    Processa comandos especiais.

    Returns:
        CommandResult indicando a ação a ser tomada.
    """
    user_input_lower = user_input.lower().strip()

    if user_input_lower in config.EXIT_COMMANDS:
        logger.info("Comando de saída recebido")
        return CommandResult.EXIT

    if user_input_lower in config.CLEAR_COMMANDS:
        conversation.clear()
        display.show_success("Histórico limpo!")
        return CommandResult.CONTINUE

    if user_input_lower in config.SAVE_COMMANDS:
        try:
            filename = conversation.save_to_file()
            display.show_success(f"Histórico salvo em: {filename}")
        except IOError as e:
            logger.error("Falha ao salvar histórico: %s", e)
            display.show_error(str(e))
        return CommandResult.CONTINUE

    if user_input_lower in config.HELP_COMMANDS:
        display.show_help()
        return CommandResult.CONTINUE

    model_arg = _extract_command_arg(user_input, config.MODEL_COMMANDS)
    if model_arg is not None:
        if not model_arg:
            display.show_model_info(client.get_model())
        else:
            try:
                old_model = client.get_model()
                client.set_model(model_arg)
                logger.info("Modelo alterado: %s -> %s", old_model, model_arg)
                display.show_model_changed(model_arg)
            except ValueError as e:
                logger.warning("Modelo inválido: %s", model_arg)
                display.show_error(str(e))
        return CommandResult.CONTINUE

    if user_input_lower in config.LIST_COMMANDS:
        files = conversation.list_history_files()
        display.show_history_list(files)
        return CommandResult.CONTINUE

    if user_input_lower in config.STREAM_COMMANDS:
        return CommandResult.TOGGLE_STREAM

    load_arg = _extract_command_arg(user_input, config.LOAD_COMMANDS)
    if load_arg is not None:
        if not load_arg:
            display.show_error("Uso: /carregar <nome_arquivo>")
        else:
            try:
                count = conversation.load_from_file(load_arg)
                display.show_success(f"Histórico carregado: {count} mensagens")
            except ConversationLoadError as e:
                logger.error("Falha ao carregar histórico: %s", e)
                display.show_error(str(e))
        return CommandResult.CONTINUE

    return CommandResult.NOT_COMMAND


def main(argv: Sequence[str] | None = None) -> None:
    """Loop principal do chatbot."""
    args = parse_args(argv)

    # Pass parameters directly to setup_logging instead of mutating os.environ
    # This is thread-safe and avoids side effects on the global environment
    setup_logging(
        log_level=args.log_level,
        log_file=args.log_file
    )
    logger.info("Iniciando chatbot")

    display = Display()

    try:
        config.validate()
    except ConfigurationError as e:
        logger.error("Erro de configuração: %s", e)
        display.show_error(str(e))
        sys.exit(1)

    with OpenRouterClient() as client:
        if args.model:
            try:
                client.set_model(args.model)
            except ValueError as e:
                display.show_error(str(e))
                sys.exit(1)
        conversation = ConversationManager()

        # Determina modo de streaming (CLI sobrescreve config)
        use_streaming = config.STREAM_RESPONSE and not args.no_stream

        display.show_banner()
        display.show_info("Digite /ajuda para ver os comandos disponíveis.")
        display.console.print()

        while True:
            try:
                user_input = display.prompt_input()

                if not user_input.strip():
                    continue

                if len(user_input) > config.MAX_MESSAGE_LENGTH:
                    display.show_error(
                        f"Mensagem muito longa (máximo {config.MAX_MESSAGE_LENGTH} caracteres)."
                    )
                    continue

                command_result = handle_command(user_input, conversation, client, display)

                if command_result == CommandResult.EXIT:
                    break
                elif command_result == CommandResult.CONTINUE:
                    continue
                elif command_result == CommandResult.TOGGLE_STREAM:
                    use_streaming = not use_streaming
                    mode = "ativado" if use_streaming else "desativado"
                    display.show_success(f"Streaming {mode}")
                    continue

                conversation.add_user_message(user_input)
                messages = conversation.get_messages()

                try:
                    display.start_spinner()

                    first_chunk = True
                    char_count = 0
                    response_buffer: list[str] = []

                    with client.send_message_stream(messages) as stream:
                        for chunk in stream:
                            if first_chunk:
                                if use_streaming:
                                    display.transition_spinner_to_streaming()
                                first_chunk = False

                            response_buffer.append(chunk)
                            char_count += len(chunk)
                            display.update_spinner_tokens(char_count // CHARS_PER_TOKEN)

                            if use_streaming:
                                display.add_streaming_chunk(chunk)

                    if first_chunk:
                        display.stop_spinner()
                        response = ""
                    elif use_streaming:
                        response = display.stop_streaming()
                    else:
                        display.stop_spinner()
                        response = "".join(response_buffer)
                        if response:
                            display.show_bot_message(response)

                    if response:
                        conversation.add_assistant_message(response)
                    else:
                        logger.warning("Resposta vazia recebida da API")
                        display.show_info("Resposta vazia recebida. Tente novamente.")
                        conversation.remove_last_user_message()

                except APIError as e:
                    logger.error("Erro na API: %s", e)
                    display.cleanup()
                    display.show_error(str(e))
                    conversation.remove_last_user_message()

            except KeyboardInterrupt:
                display.console.print()
                break

    display.show_goodbye()


if __name__ == "__main__":
    main()
