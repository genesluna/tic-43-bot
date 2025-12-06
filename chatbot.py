#!/usr/bin/env python3
"""
Chatbot Conversacional com IA - Projeto TIC43

Um chatbot interativo que utiliza a API OpenRouter para
manter conversas contextualizadas com o usuário.
"""

import sys
from utils.api import OpenRouterClient, APIError, count_tokens
from utils.conversation import ConversationManager
from utils.display import Display
from utils.config import config, Config, ConfigurationError


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

    if user_input_lower in config.MODEL_COMMANDS:
        display.show_model_info(client.get_model())
        return True

    return None


def main():
    """Loop principal do chatbot."""
    display = Display()

    try:
        Config.validate()
    except ConfigurationError as e:
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
                    response_chunks = []
                    token_count = 0

                    for chunk in client.send_message_stream(conversation.get_messages()):
                        response_chunks.append(chunk)
                        token_count += count_tokens(chunk)
                        display.update_spinner_tokens(token_count)

                    display.stop_spinner()

                    response = "".join(response_chunks)
                    conversation.add_assistant_message(response)
                    display.show_bot_message(response)

                except APIError as e:
                    display.stop_spinner()
                    display.show_error(str(e))
                    conversation.remove_last_user_message()

            except KeyboardInterrupt:
                display.console.print()
                break

    display.show_goodbye()


if __name__ == "__main__":
    main()
