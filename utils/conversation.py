"""Gerenciamento do histórico de conversas."""

import json
import logging
import os
import re
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import TypedDict

from .config import config, MAX_MESSAGE_CONTENT_SIZE

__all__ = ["ConversationManager", "ConversationLoadError", "Message"]

MAX_HISTORY_FILE_SIZE = 10 * 1024 * 1024  # 10MB

logger = logging.getLogger(__name__)


class Message(TypedDict):
    """Estrutura de uma mensagem no formato OpenAI."""

    role: str
    content: str


class ConversationLoadError(Exception):
    """Erro ao carregar conversa de arquivo."""


class ConversationManager:
    """Gerencia o histórico de mensagens da conversa."""

    def __init__(self) -> None:
        self.messages: list[Message] = []
        self.system_prompt = self._build_system_prompt()
        self._init_system_message()

    def __repr__(self) -> str:
        return f"ConversationManager(messages={len(self.messages)})"

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
        """Mantém apenas os N pares de mensagens mais recentes + system prompt.

        MAX_HISTORY_SIZE representa o número de pares de conversa (usuário + assistente).
        O limite real de mensagens individuais é MAX_HISTORY_SIZE * 2.
        """
        max_messages = config.MAX_HISTORY_SIZE * 2
        if len(self.messages) > max_messages + 1:
            self.messages = [self.messages[0]] + self.messages[-(max_messages):]

    def _validate_message_content(self, content: str) -> None:
        """Valida o conteúdo de uma mensagem."""
        if not isinstance(content, str):
            raise TypeError("Conteúdo da mensagem deve ser uma string")
        if len(content) > MAX_MESSAGE_CONTENT_SIZE:
            raise ValueError(
                f"Mensagem excede tamanho máximo ({MAX_MESSAGE_CONTENT_SIZE} caracteres)"
            )

    def add_user_message(self, content: str) -> None:
        """Adiciona uma mensagem do usuário."""
        self._validate_message_content(content)
        self.messages.append({"role": "user", "content": content})
        self._enforce_history_limit()
        logger.debug("Mensagem do usuário adicionada (%d chars)", len(content))

    def add_assistant_message(self, content: str) -> None:
        """Adiciona uma mensagem do assistente."""
        self._validate_message_content(content)
        self.messages.append({"role": "assistant", "content": content})
        self._enforce_history_limit()
        logger.debug("Mensagem do assistente adicionada (%d chars)", len(content))

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

    def get_messages(self) -> list[Message]:
        """Retorna uma cópia de todas as mensagens."""
        return self.messages.copy()

    def clear(self) -> None:
        """Limpa o histórico, mantendo apenas o system prompt."""
        self._init_system_message()

    def get_history_for_display(self) -> list[Message]:
        """Retorna o histórico sem a mensagem de sistema."""
        return [msg for msg in self.messages if msg["role"] != "system"]

    def _sanitize_filename(self, filename: str) -> str:
        """Remove caracteres perigosos do nome do arquivo."""
        basename = os.path.basename(filename)
        sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', basename)
        sanitized = re.sub(r'\s+', '_', sanitized)
        # Remove all extensions (e.g., .json, .bak, .json.bak)
        while re.search(r'\.[a-zA-Z0-9]+$', sanitized):
            sanitized = re.sub(r'\.[a-zA-Z0-9]+$', '', sanitized)
        sanitized = sanitized.strip('._')
        if not sanitized:
            sanitized = "history"
        return sanitized + '.json'

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
        save_dir = Path(config.HISTORY_DIR)
        save_dir.mkdir(exist_ok=True, mode=0o700)

        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"history_{timestamp}.json"

        safe_filename = self._sanitize_filename(filename)
        filepath = save_dir / safe_filename

        history = {
            "timestamp": datetime.now().isoformat(),
            "model": config.OPENROUTER_MODEL,
            "messages": self.get_history_for_display(),
        }

        try:
            # Escrita atômica: escreve em arquivo temporário e move
            # Isso evita arquivos corrompidos em caso de falha ou disco cheio
            fd, tmp_path = tempfile.mkstemp(suffix='.json', dir=save_dir)
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    json.dump(history, f, ensure_ascii=False, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                shutil.move(tmp_path, filepath)
            except Exception:
                # Remove arquivo temporário em caso de erro
                try:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
                except OSError as cleanup_error:
                    logger.warning("Falha ao remover arquivo temporário %s: %s", tmp_path, cleanup_error)
                raise
            logger.info("Histórico salvo: %s (%d mensagens)", filepath, len(history['messages']))
            return str(filepath)
        except (OSError, PermissionError) as e:
            logger.error("Falha ao salvar histórico: %s", e)
            raise IOError(f"Erro ao salvar arquivo: {e}") from e

    def message_count(self) -> int:
        """Retorna o número de mensagens (excluindo system)."""
        return sum(1 for msg in self.messages if msg["role"] != "system")

    def list_history_files(self, limit: int = 100) -> list[tuple[str, str, str]]:
        """
        Lista arquivos de histórico disponíveis.

        Args:
            limit: Número máximo de arquivos a retornar.

        Returns:
            Lista de tuplas (nome_arquivo, timestamp, modelo) ordenada por data.
        """
        history_dir = Path(config.HISTORY_DIR)

        if not history_dir.exists():
            return []

        files = []
        for filepath in history_dir.glob("*.json"):
            try:
                if filepath.is_symlink():
                    logger.debug("Symlink ignorado: %s", filepath)
                    continue
                if filepath.stat().st_size > MAX_HISTORY_FILE_SIZE:
                    logger.debug("Arquivo muito grande ignorado: %s", filepath)
                    continue
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                timestamp = data.get("timestamp", "Desconhecido")
                model = data.get("model", "Desconhecido")
                files.append((filepath.name, timestamp, model))
            except json.JSONDecodeError:
                logger.debug("JSON inválido ignorado: %s", filepath)
                continue
            except OSError as e:
                logger.warning("Erro ao ler arquivo de histórico %s: %s", filepath, e)
                continue

        files.sort(key=lambda x: x[1], reverse=True)
        return files[:limit]

    def load_from_file(self, filename: str) -> int:
        """
        Carrega histórico de conversa de um arquivo JSON.

        Args:
            filename: Nome do arquivo (sempre relativo ao HISTORY_DIR).

        Returns:
            Número de mensagens carregadas.

        Raises:
            ConversationLoadError: Se arquivo inválido ou não encontrado.
        """
        safe_filename = self._sanitize_filename(Path(filename).name)
        path = Path(config.HISTORY_DIR) / safe_filename

        if not path.exists():
            logger.warning("Tentativa de carregar arquivo inexistente: %s", path)
            raise ConversationLoadError(f"Arquivo não encontrado: {path}")

        if path.is_symlink():
            logger.warning("Tentativa de carregar symlink: %s", path)
            raise ConversationLoadError("Links simbólicos não são permitidos")

        file_size = path.stat().st_size
        if file_size > MAX_HISTORY_FILE_SIZE:
            logger.warning(
                "Arquivo muito grande: %s (%d bytes, limite: %d)",
                path, file_size, MAX_HISTORY_FILE_SIZE
            )
            raise ConversationLoadError(
                f"Arquivo muito grande ({file_size // 1024 // 1024}MB). "
                f"Limite: {MAX_HISTORY_FILE_SIZE // 1024 // 1024}MB"
            )

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ConversationLoadError(f"Arquivo JSON inválido: {e}") from e
        except OSError as e:
            raise ConversationLoadError(f"Erro ao ler arquivo: {e}") from e

        if not isinstance(data, dict):
            raise ConversationLoadError("Estrutura de arquivo inválida: esperado objeto JSON")

        if "messages" not in data:
            raise ConversationLoadError("Arquivo não contém campo 'messages'")

        messages = data["messages"]
        if not isinstance(messages, list):
            raise ConversationLoadError("Campo 'messages' deve ser uma lista")

        for i, msg in enumerate(messages):
            if not isinstance(msg, dict):
                raise ConversationLoadError(f"Mensagem {i} inválida: esperado objeto")
            if "role" not in msg or "content" not in msg:
                raise ConversationLoadError(f"Mensagem {i} sem 'role' ou 'content'")
            if msg["role"] not in ("user", "assistant"):
                raise ConversationLoadError(f"Mensagem {i} com role inválido: {msg['role']}")
            content = msg.get("content")
            if not isinstance(content, str):
                raise ConversationLoadError(f"Mensagem {i} com 'content' não-string")
            if len(content) > MAX_MESSAGE_CONTENT_SIZE:
                raise ConversationLoadError(f"Mensagem {i} excede tamanho máximo")

        self._init_system_message()
        for msg in messages:
            self.messages.append({"role": msg["role"], "content": msg["content"]})

        self._enforce_history_limit()
        logger.info("Histórico carregado: %s (%d mensagens)", path, len(messages))
        return len(messages)
