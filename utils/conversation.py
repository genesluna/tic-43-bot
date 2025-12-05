"""Gerenciamento do histórico de conversas."""

import json
from datetime import datetime
from .config import config


class ConversationManager:
    """Gerencia o histórico de mensagens da conversa."""

    def __init__(self):
        self.messages: list[dict] = []
        self.system_prompt = config.SYSTEM_PROMPT
        self._init_system_message()

    def _init_system_message(self) -> None:
        """Inicializa com a mensagem de sistema."""
        self.messages = [{"role": "system", "content": self.system_prompt}]

    def add_user_message(self, content: str) -> None:
        """Adiciona uma mensagem do usuário."""
        self.messages.append({"role": "user", "content": content})

    def add_assistant_message(self, content: str) -> None:
        """Adiciona uma mensagem do assistente."""
        self.messages.append({"role": "assistant", "content": content})

    def get_messages(self) -> list[dict]:
        """Retorna todas as mensagens."""
        return self.messages

    def clear(self) -> None:
        """Limpa o histórico, mantendo apenas o system prompt."""
        self._init_system_message()

    def get_history_for_display(self) -> list[dict]:
        """Retorna o histórico sem a mensagem de sistema."""
        return [msg for msg in self.messages if msg["role"] != "system"]

    def save_to_file(self, filename: str | None = None) -> str:
        """
        Salva o histórico em um arquivo JSON.

        Args:
            filename: Nome do arquivo. Se None, gera automaticamente.

        Returns:
            Caminho do arquivo salvo.
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"historico_{timestamp}.json"

        history = {
            "timestamp": datetime.now().isoformat(),
            "model": config.OPENROUTER_MODEL,
            "messages": self.get_history_for_display(),
        }

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

        return filename

    def message_count(self) -> int:
        """Retorna o número de mensagens (excluindo system)."""
        return len(self.get_history_for_display())
