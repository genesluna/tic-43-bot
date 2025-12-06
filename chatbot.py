#!/usr/bin/env python3
"""
Chatbot Conversacional com IA - Projeto TIC43

Um chatbot interativo que utiliza a API OpenRouter para
manter conversas contextualizadas com o usuário.
"""

from utils.api import OpenRouterClient, APIError
from utils.conversation import ConversationManager
from utils.display import Display
from utils.config import config


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
        except Exception as e:
            display.show_error(f"Erro ao salvar: {e}")
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
    client = OpenRouterClient()
    conversation = ConversationManager()

    display.show_banner()
    display.show_info("Digite /ajuda para ver os comandos disponíveis.")
    display.console.print()

    while True:
        try:
            user_input = display.prompt_input()

            if not user_input.strip():
                continue

            command_result = handle_command(user_input, conversation, client, display)

            if command_result is False:
                break
            elif command_result is True:
                continue

            conversation.add_user_message(user_input)

            try:
                display.start_spinner()
                response = client.send_message(conversation.get_messages())
                display.stop_spinner()

                conversation.add_assistant_message(response)
                display.show_bot_message(response)

            except APIError as e:
                display.stop_spinner()
                display.show_error(str(e))
                conversation.messages.pop()

        except KeyboardInterrupt:
            display.console.print()
            break

    display.show_goodbye()


if __name__ == "__main__":
    main()
