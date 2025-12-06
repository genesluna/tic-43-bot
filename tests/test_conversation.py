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

    def test_save_to_file(self, tmp_path):
        """Verifica se o histórico é salvo corretamente em arquivo."""
        manager = ConversationManager()
        manager.add_user_message("Olá")
        manager.add_assistant_message("Oi!")

        filename = str(tmp_path / "test_history.json")
        saved_path = manager.save_to_file(filename)

        assert saved_path == filename
        assert os.path.exists(filename)

        with open(filename, "r", encoding="utf-8") as f:
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

        assert saved_path.startswith("historico_")
        assert saved_path.endswith(".json")
        assert os.path.exists(saved_path)

    def test_conversation_flow(self):
        """Testa um fluxo de conversa completo."""
        manager = ConversationManager()

        # Simula uma conversa
        manager.add_user_message("Olá!")
        manager.add_assistant_message("Olá! Como posso ajudar?")
        manager.add_user_message("Qual é a capital do Brasil?")
        manager.add_assistant_message("A capital do Brasil é Brasília.")

        assert manager.message_count() == 4

        messages = manager.get_messages()
        assert len(messages) == 5  # 4 + system

        # Limpa e verifica
        manager.clear()
        assert manager.message_count() == 0
