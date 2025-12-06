"""Gerenciamento do histórico de conversas."""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from .config import config


class ConversationManager:
    """Gerencia o histórico de mensagens da conversa."""

    SAVE_DIR = Path("./history")

    def __init__(self):
        self.messages: list[dict] = []
        self.system_prompt = self._build_system_prompt()
        self._init_system_message()

    def _build_system_prompt(self) -> str:
        """Constrói o system prompt com as configurações de personalização."""
        parts = [config.SYSTEM_PROMPT]

        instructions = []
        if config.RESPONSE_LANGUAGE:
            instructions.append(f"Responda em {config.RESPONSE_LANGUAGE}")
        if config.RESPONSE_LENGTH:
            instructions.append(f"seja {config.RESPONSE_LENGTH} nas respostas")
        if config.RESPONSE_TONE:
            instructions.append(f"use tom {config.RESPONSE_TONE}")
        if config.RESPONSE_FORMAT:
            if config.RESPONSE_FORMAT.lower() == "markdown":
                instructions.append("use formatação markdown quando apropriado")
            else:
                instructions.append("use apenas texto simples sem formatação")

        if instructions:
            parts.append(". ".join(instructions) + ".")

        return " ".join(parts)

    def _init_system_message(self) -> None:
        """Inicializa com a mensagem de sistema."""
        self.messages = [{"role": "system", "content": self.system_prompt}]

    def _enforce_history_limit(self) -> None:
        """Mantém apenas as N mensagens mais recentes + system prompt."""
        max_size = config.MAX_HISTORY_SIZE
        if len(self.messages) > max_size + 1:
            self.messages = [self.messages[0]] + self.messages[-(max_size):]

    def add_user_message(self, content: str) -> None:
        """Adiciona uma mensagem do usuário."""
        self.messages.append({"role": "user", "content": content})
        self._enforce_history_limit()

    def add_assistant_message(self, content: str) -> None:
        """Adiciona uma mensagem do assistente."""
        self.messages.append({"role": "assistant", "content": content})
        self._enforce_history_limit()

    def remove_last_user_message(self) -> str | None:
        """
        Remove e retorna a última mensagem do usuário.

        Returns:
            Conteúdo da mensagem removida ou None se não houver.
        """
        for i in range(len(self.messages) - 1, -1, -1):
            if self.messages[i]["role"] == "user":
                removed = self.messages.pop(i)
                return removed["content"]
        return None

    def get_messages(self) -> list[dict]:
        """Retorna todas as mensagens."""
        return self.messages

    def clear(self) -> None:
        """Limpa o histórico, mantendo apenas o system prompt."""
        self._init_system_message()

    def get_history_for_display(self) -> list[dict]:
        """Retorna o histórico sem a mensagem de sistema."""
        return [msg for msg in self.messages if msg["role"] != "system"]

    def _sanitize_filename(self, filename: str) -> str:
        """Remove caracteres perigosos do nome do arquivo."""
        basename = os.path.basename(filename)
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', basename)
        if not sanitized.endswith('.json'):
            sanitized += '.json'
        return sanitized

    def save_to_file(self, filename: str | None = None) -> str:
        """
        Salva o histórico em um arquivo JSON.

        Args:
            filename: Nome do arquivo. Se None, gera automaticamente.

        Returns:
            Caminho do arquivo salvo.

        Raises:
            IOError: Em caso de erro ao salvar.
        """
        self.SAVE_DIR.mkdir(exist_ok=True)

        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"history_{timestamp}.json"

        safe_filename = self._sanitize_filename(filename)
        filepath = self.SAVE_DIR / safe_filename

        history = {
            "timestamp": datetime.now().isoformat(),
            "model": config.OPENROUTER_MODEL,
            "messages": self.get_history_for_display(),
        }

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
            return str(filepath)
        except (OSError, PermissionError) as e:
            raise IOError(f"Erro ao salvar arquivo: {e}") from e

    def message_count(self) -> int:
        """Retorna o número de mensagens (excluindo system)."""
        return len(self.get_history_for_display())
