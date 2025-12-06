"""Testes para o módulo de gerenciamento de conversas."""

import os
import json
import pytest
from unittest.mock import patch
from utils.conversation import ConversationManager


class TestConversationManager:
    """Testes para a classe ConversationManager."""

    def test_init_with_system_message(self):
        """Verifica se o manager é inicializado com a mensagem de sistema."""
        manager = ConversationManager()

        assert len(manager.messages) == 1
        assert manager.messages[0]["role"] == "system"

    def test_add_user_message(self):
        """Verifica se mensagens do usuário são adicionadas corretamente."""
        manager = ConversationManager()
        manager.add_user_message("Olá, tudo bem?")

        assert len(manager.messages) == 2
        assert manager.messages[1]["role"] == "user"
        assert manager.messages[1]["content"] == "Olá, tudo bem?"

    def test_add_assistant_message(self):
        """Verifica se mensagens do assistente são adicionadas corretamente."""
        manager = ConversationManager()
        manager.add_assistant_message("Olá! Estou bem, obrigado.")

        assert len(manager.messages) == 2
        assert manager.messages[1]["role"] == "assistant"
        assert manager.messages[1]["content"] == "Olá! Estou bem, obrigado."

    def test_get_messages(self):
        """Verifica se get_messages retorna todas as mensagens."""
        manager = ConversationManager()
        manager.add_user_message("Olá")
        manager.add_assistant_message("Oi!")

        messages = manager.get_messages()

        assert len(messages) == 3
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[2]["role"] == "assistant"

    def test_clear(self):
        """Verifica se o histórico é limpo corretamente."""
        manager = ConversationManager()
        manager.add_user_message("Olá")
        manager.add_assistant_message("Oi!")

        manager.clear()

        assert len(manager.messages) == 1
        assert manager.messages[0]["role"] == "system"

    def test_get_history_for_display(self):
        """Verifica se o histórico para exibição exclui a mensagem de sistema."""
        manager = ConversationManager()
        manager.add_user_message("Olá")
        manager.add_assistant_message("Oi!")

        history = manager.get_history_for_display()

        assert len(history) == 2
        assert all(msg["role"] != "system" for msg in history)

    def test_message_count(self):
        """Verifica se a contagem de mensagens está correta."""
        manager = ConversationManager()

        assert manager.message_count() == 0

        manager.add_user_message("Olá")
        assert manager.message_count() == 1

        manager.add_assistant_message("Oi!")
        assert manager.message_count() == 2

    def test_save_to_file(self, tmp_path, monkeypatch):
        """Verifica se o histórico é salvo corretamente em arquivo."""
        monkeypatch.chdir(tmp_path)

        manager = ConversationManager()
        manager.add_user_message("Olá")
        manager.add_assistant_message("Oi!")

        saved_path = manager.save_to_file("test_history.json")

        assert "test_history.json" in saved_path
        assert os.path.exists(saved_path)

        with open(saved_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "timestamp" in data
        assert "model" in data
        assert "messages" in data
        assert len(data["messages"]) == 2

    def test_save_to_file_auto_filename(self, tmp_path, monkeypatch):
        """Verifica se o nome do arquivo é gerado automaticamente."""
        monkeypatch.chdir(tmp_path)

        manager = ConversationManager()
        manager.add_user_message("Teste")

        saved_path = manager.save_to_file()

        assert "history_" in saved_path
        assert saved_path.endswith(".json")
        assert os.path.exists(saved_path)

    def test_remove_last_user_message(self):
        """Verifica se a última mensagem do usuário é removida corretamente."""
        manager = ConversationManager()
        manager.add_user_message("Primeira")
        manager.add_assistant_message("Resposta")
        manager.add_user_message("Segunda")

        removed = manager.remove_last_user_message()

        assert removed == "Segunda"
        assert manager.message_count() == 2

    def test_remove_last_user_message_empty(self):
        """Verifica comportamento quando não há mensagens do usuário."""
        manager = ConversationManager()

        removed = manager.remove_last_user_message()

        assert removed is None

    def test_history_limit(self):
        """Verifica se o limite de histórico é respeitado."""
        from utils.config import config

        manager = ConversationManager()

        for i in range(config.MAX_HISTORY_SIZE + 10):
            manager.add_user_message(f"Mensagem {i}")
            manager.add_assistant_message(f"Resposta {i}")

        assert len(manager.messages) <= config.MAX_HISTORY_SIZE + 1

    def test_sanitize_filename(self):
        """Verifica se nomes de arquivo são sanitizados."""
        manager = ConversationManager()

        sanitized = manager._sanitize_filename("../../../etc/passwd")
        assert ".." not in sanitized
        assert "/" not in sanitized

        sanitized = manager._sanitize_filename('file<>:"/\\|?*.json')
        assert "<" not in sanitized
        assert ">" not in sanitized

    def test_sanitize_filename_empty(self):
        """String vazia deve retornar nome padrão."""
        manager = ConversationManager()

        sanitized = manager._sanitize_filename("")
        assert sanitized == "history.json"

    def test_sanitize_filename_only_dots(self):
        """String com apenas pontos deve retornar nome padrão."""
        manager = ConversationManager()

        sanitized = manager._sanitize_filename("...")
        assert sanitized == "history.json"

    def test_sanitize_filename_control_chars(self):
        """Caracteres de controle devem ser removidos."""
        manager = ConversationManager()

        sanitized = manager._sanitize_filename("file\x00\x1fname.json")
        assert "\x00" not in sanitized
        assert "\x1f" not in sanitized

    def test_save_to_file_io_error(self, tmp_path, monkeypatch):
        """Erro de I/O deve levantar IOError."""
        monkeypatch.chdir(tmp_path)

        manager = ConversationManager()
        manager.add_user_message("Teste")

        with patch("builtins.open", side_effect=PermissionError("Acesso negado")):
            with pytest.raises(IOError) as exc_info:
                manager.save_to_file("test.json")

            assert "Erro ao salvar" in str(exc_info.value)

    def test_get_messages_returns_copy(self):
        """get_messages deve retornar cópia, não referência."""
        manager = ConversationManager()
        manager.add_user_message("Teste")

        messages = manager.get_messages()
        messages.append({"role": "fake", "content": "fake"})

        assert len(manager.get_messages()) == 2

    def test_conversation_flow(self):
        """Testa um fluxo de conversa completo."""
        manager = ConversationManager()

        manager.add_user_message("Olá!")
        manager.add_assistant_message("Olá! Como posso ajudar?")
        manager.add_user_message("Qual é a capital do Brasil?")
        manager.add_assistant_message("A capital do Brasil é Brasília.")

        assert manager.message_count() == 4

        messages = manager.get_messages()
        assert len(messages) == 5

        manager.clear()
        assert manager.message_count() == 0

    def test_save_to_file_custom_history_dir(self, tmp_path):
        """Verifica se HISTORY_DIR customizado é respeitado."""
        custom_dir = tmp_path / "custom_history"

        with patch("utils.conversation.config") as mock_config:
            mock_config.HISTORY_DIR = str(custom_dir)
            mock_config.OPENROUTER_MODEL = "test-model"
            mock_config.SYSTEM_PROMPT = "Test prompt"
            mock_config.RESPONSE_LANGUAGE = ""
            mock_config.RESPONSE_LENGTH = ""
            mock_config.RESPONSE_TONE = ""
            mock_config.RESPONSE_FORMAT = ""
            mock_config.MAX_HISTORY_SIZE = 50

            manager = ConversationManager()
            manager.add_user_message("Teste")

            saved_path = manager.save_to_file("test.json")

            assert str(custom_dir) in saved_path
            assert custom_dir.exists()
            assert (custom_dir / "test.json").exists()
