#!/usr/bin/env python3
"""
Chatbot Conversacional com IA - Projeto TIC43

Um chatbot interativo que utiliza a API OpenRouter para
manter conversas contextualizadas com o usuário.
"""

import logging
import sys
from utils.api import OpenRouterClient, APIError
from utils.conversation import ConversationManager, ConversationLoadError
from utils.display import Display
from utils.config import config, Config, ConfigurationError
from utils.logging_config import setup_logging

logger = logging.getLogger(__name__)


def handle_command(
    user_input: str,
    conversation: ConversationManager,
    client: OpenRouterClient,
    display: Display,
) -> bool | None:
    """
    Processa comandos especiais.

    Returns:
        True se deve continuar, False se deve sair, None se não é comando.
    """
    user_input_lower = user_input.lower().strip()

    if user_input_lower in config.EXIT_COMMANDS:
        logger.info("Comando de saída recebido")
        return False

    if user_input_lower in config.CLEAR_COMMANDS:
        conversation.clear()
        display.show_success("Histórico limpo!")
        return True

    if user_input_lower in config.SAVE_COMMANDS:
        try:
            filename = conversation.save_to_file()
            display.show_success(f"Histórico salvo em: {filename}")
        except IOError as e:
            display.show_error(str(e))
        return True

    if user_input_lower in config.HELP_COMMANDS:
        display.show_help()
        return True

    for cmd in config.MODEL_COMMANDS:
        if user_input_lower.startswith(cmd):
            arg = user_input[len(cmd):].strip()
            if not arg:
                display.show_model_info(client.get_model())
            else:
                try:
                    old_model = client.get_model()
                    client.set_model(arg)
                    logger.info(f"Modelo alterado: {old_model} -> {arg}")
                    display.show_model_changed(arg)
                except ValueError as e:
                    logger.warning(f"Modelo inválido: {arg}")
                    display.show_error(str(e))
            return True

    if user_input_lower in config.LIST_COMMANDS:
        files = conversation.list_history_files()
        display.show_history_list(files)
        return True

    for cmd in config.LOAD_COMMANDS:
        if user_input_lower.startswith(cmd):
            arg = user_input[len(cmd):].strip()
            if not arg:
                display.show_error("Uso: /carregar <nome_arquivo>")
            else:
                try:
                    count = conversation.load_from_file(arg)
                    display.show_success(f"Histórico carregado: {count} mensagens")
                except ConversationLoadError as e:
                    display.show_error(str(e))
            return True

    return None


def main():
    """Loop principal do chatbot."""
    setup_logging()
    logger.info("Iniciando chatbot")

    display = Display()

    try:
        Config.validate()
    except ConfigurationError as e:
        logger.error(f"Erro de configuração: {e}")
        display.show_error(str(e))
        sys.exit(1)

    with OpenRouterClient() as client:
        conversation = ConversationManager()

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

                if command_result is False:
                    break
                elif command_result is True:
                    continue

                conversation.add_user_message(user_input)

                try:
                    display.start_spinner()
                    first_chunk = True

                    for chunk in client.send_message_stream(conversation.get_messages()):
                        if first_chunk:
                            display.transition_spinner_to_streaming()
                            first_chunk = False
                        display.add_streaming_chunk(chunk)

                    if first_chunk:
                        display.stop_spinner()
                        response = ""
                    else:
                        response = display.stop_streaming()

                    if response:
                        conversation.add_assistant_message(response)

                except APIError as e:
                    logger.error(f"Erro na API: {e}")
                    try:
                        display.stop_spinner()
                    except Exception:
                        pass
                    try:
                        if display.streaming.running:
                            display.streaming.stop()
                    except Exception:
                        pass
                    display.show_error(str(e))
                    conversation.remove_last_user_message()

            except KeyboardInterrupt:
                display.console.print()
                break

    display.show_goodbye()


if __name__ == "__main__":
    main()
