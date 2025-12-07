"""Testes para o módulo de gerenciamento de conversas."""

import os
import json
import pytest
from unittest.mock import patch
from utils.conversation import ConversationManager, ConversationLoadError
from utils.config import MAX_MESSAGE_CONTENT_SIZE


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
        """Verifica se o limite de histórico é respeitado.

        MAX_HISTORY_SIZE representa pares de mensagens (usuário + assistente).
        O limite real de mensagens individuais é MAX_HISTORY_SIZE * 2.
        """
        from utils.config import config

        manager = ConversationManager()

        for i in range(config.MAX_HISTORY_SIZE + 10):
            manager.add_user_message(f"Mensagem {i}")
            manager.add_assistant_message(f"Resposta {i}")

        max_messages = config.MAX_HISTORY_SIZE * 2
        assert len(manager.messages) <= max_messages + 1

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

    def test_sanitize_filename_with_spaces(self):
        """Espaços devem ser convertidos em underscores."""
        manager = ConversationManager()

        sanitized = manager._sanitize_filename("my file name.json")
        assert " " not in sanitized
        assert sanitized == "my_file_name.json"

    def test_sanitize_filename_multiple_spaces(self):
        """Múltiplos espaços devem ser convertidos em um único underscore."""
        manager = ConversationManager()

        sanitized = manager._sanitize_filename("my   file   name.json")
        assert "   " not in sanitized
        assert sanitized == "my_file_name.json"

    def test_sanitize_filename_with_other_extension(self):
        """Extensões não-json devem ser removidas."""
        manager = ConversationManager()

        sanitized = manager._sanitize_filename("backup.bak")
        assert sanitized == "backup.json"

    def test_sanitize_filename_with_json_bak_extension(self):
        """Arquivos como .json.bak devem virar .json, não .json.bak.json."""
        manager = ConversationManager()

        sanitized = manager._sanitize_filename("history.json.bak")
        assert sanitized == "history.json"

    def test_sanitize_filename_case_insensitive_json(self):
        """Extensão .JSON (maiúscula) deve ser tratada corretamente."""
        manager = ConversationManager()

        sanitized = manager._sanitize_filename("history.JSON")
        assert sanitized == "history.json"

    def test_save_to_file_io_error(self, tmp_path, monkeypatch):
        """Erro de I/O deve levantar IOError."""
        monkeypatch.chdir(tmp_path)

        manager = ConversationManager()
        manager.add_user_message("Teste")

        with patch("utils.conversation.tempfile.mkstemp", side_effect=PermissionError("Acesso negado")):
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


class TestLoadFromFile:
    """Testes para carregamento de histórico."""

    def test_load_from_file_success(self, tmp_path):
        """Verifica se histórico é carregado corretamente."""
        history_dir = tmp_path / "history"
        history_dir.mkdir()
        test_file = history_dir / "test.json"
        test_data = {
            "timestamp": "2024-01-01T12:00:00",
            "model": "openai/gpt-4",
            "messages": [
                {"role": "user", "content": "Olá"},
                {"role": "assistant", "content": "Oi!"}
            ]
        }
        test_file.write_text(json.dumps(test_data), encoding="utf-8")

        with patch("utils.conversation.config") as mock_config:
            mock_config.HISTORY_DIR = str(history_dir)
            mock_config.SYSTEM_PROMPT = "Test"
            mock_config.RESPONSE_LANGUAGE = ""
            mock_config.RESPONSE_LENGTH = ""
            mock_config.RESPONSE_TONE = ""
            mock_config.RESPONSE_FORMAT = ""
            mock_config.MAX_HISTORY_SIZE = 50

            manager = ConversationManager()
            count = manager.load_from_file("test.json")

            assert count == 2
            assert manager.message_count() == 2

    def test_load_from_file_not_found(self, tmp_path):
        """Arquivo inexistente deve levantar ConversationLoadError."""
        with patch("utils.conversation.config") as mock_config:
            mock_config.HISTORY_DIR = str(tmp_path)
            mock_config.SYSTEM_PROMPT = "Test"
            mock_config.RESPONSE_LANGUAGE = ""
            mock_config.RESPONSE_LENGTH = ""
            mock_config.RESPONSE_TONE = ""
            mock_config.RESPONSE_FORMAT = ""
            mock_config.MAX_HISTORY_SIZE = 50

            manager = ConversationManager()

            with pytest.raises(ConversationLoadError) as exc_info:
                manager.load_from_file("nonexistent.json")

            assert "não encontrado" in str(exc_info.value)

    def test_load_from_file_too_large(self, tmp_path):
        """Arquivo muito grande deve levantar ConversationLoadError."""
        from utils.conversation import MAX_HISTORY_FILE_SIZE

        history_dir = tmp_path / "history"
        history_dir.mkdir()
        test_file = history_dir / "large.json"
        test_file.write_bytes(b"x" * (MAX_HISTORY_FILE_SIZE + 1))

        with patch("utils.conversation.config") as mock_config:
            mock_config.HISTORY_DIR = str(history_dir)
            mock_config.SYSTEM_PROMPT = "Test"
            mock_config.RESPONSE_LANGUAGE = ""
            mock_config.RESPONSE_LENGTH = ""
            mock_config.RESPONSE_TONE = ""
            mock_config.RESPONSE_FORMAT = ""
            mock_config.MAX_HISTORY_SIZE = 50

            manager = ConversationManager()

            with pytest.raises(ConversationLoadError) as exc_info:
                manager.load_from_file("large.json")

            assert "muito grande" in str(exc_info.value)

    def test_load_from_file_non_dict_root(self, tmp_path):
        """JSON com raiz não-dicionário deve levantar ConversationLoadError."""
        history_dir = tmp_path / "history"
        history_dir.mkdir()
        test_file = history_dir / "array_root.json"
        test_file.write_text("[1, 2, 3]", encoding="utf-8")

        with patch("utils.conversation.config") as mock_config:
            mock_config.HISTORY_DIR = str(history_dir)
            mock_config.SYSTEM_PROMPT = "Test"
            mock_config.RESPONSE_LANGUAGE = ""
            mock_config.RESPONSE_LENGTH = ""
            mock_config.RESPONSE_TONE = ""
            mock_config.RESPONSE_FORMAT = ""
            mock_config.MAX_HISTORY_SIZE = 50

            manager = ConversationManager()

            with pytest.raises(ConversationLoadError) as exc_info:
                manager.load_from_file("array_root.json")

            assert "estrutura" in str(exc_info.value).lower()

    def test_load_from_file_invalid_json(self, tmp_path):
        """JSON inválido deve levantar ConversationLoadError."""
        history_dir = tmp_path / "history"
        history_dir.mkdir()
        test_file = history_dir / "invalid.json"
        test_file.write_text("{ invalid json }", encoding="utf-8")

        with patch("utils.conversation.config") as mock_config:
            mock_config.HISTORY_DIR = str(history_dir)
            mock_config.SYSTEM_PROMPT = "Test"
            mock_config.RESPONSE_LANGUAGE = ""
            mock_config.RESPONSE_LENGTH = ""
            mock_config.RESPONSE_TONE = ""
            mock_config.RESPONSE_FORMAT = ""
            mock_config.MAX_HISTORY_SIZE = 50

            manager = ConversationManager()

            with pytest.raises(ConversationLoadError) as exc_info:
                manager.load_from_file("invalid.json")

            assert "JSON inválido" in str(exc_info.value)

    def test_load_from_file_missing_messages(self, tmp_path):
        """Arquivo sem 'messages' deve levantar erro."""
        history_dir = tmp_path / "history"
        history_dir.mkdir()
        test_file = history_dir / "no_messages.json"
        test_file.write_text('{"timestamp": "2024-01-01"}', encoding="utf-8")

        with patch("utils.conversation.config") as mock_config:
            mock_config.HISTORY_DIR = str(history_dir)
            mock_config.SYSTEM_PROMPT = "Test"
            mock_config.RESPONSE_LANGUAGE = ""
            mock_config.RESPONSE_LENGTH = ""
            mock_config.RESPONSE_TONE = ""
            mock_config.RESPONSE_FORMAT = ""
            mock_config.MAX_HISTORY_SIZE = 50

            manager = ConversationManager()

            with pytest.raises(ConversationLoadError) as exc_info:
                manager.load_from_file("no_messages.json")

            assert "messages" in str(exc_info.value)

    def test_load_from_file_invalid_role(self, tmp_path):
        """Role inválido deve levantar erro."""
        history_dir = tmp_path / "history"
        history_dir.mkdir()
        test_file = history_dir / "invalid_role.json"
        test_data = {
            "messages": [{"role": "system", "content": "test"}]
        }
        test_file.write_text(json.dumps(test_data), encoding="utf-8")

        with patch("utils.conversation.config") as mock_config:
            mock_config.HISTORY_DIR = str(history_dir)
            mock_config.SYSTEM_PROMPT = "Test"
            mock_config.RESPONSE_LANGUAGE = ""
            mock_config.RESPONSE_LENGTH = ""
            mock_config.RESPONSE_TONE = ""
            mock_config.RESPONSE_FORMAT = ""
            mock_config.MAX_HISTORY_SIZE = 50

            manager = ConversationManager()

            with pytest.raises(ConversationLoadError) as exc_info:
                manager.load_from_file("invalid_role.json")

            assert "role inválido" in str(exc_info.value)

    def test_load_from_file_content_too_large(self, tmp_path):
        """Mensagem muito grande deve levantar erro."""
        history_dir = tmp_path / "history"
        history_dir.mkdir()
        test_file = history_dir / "large_content.json"
        large_content = "x" * (MAX_MESSAGE_CONTENT_SIZE + 1)
        test_data = {
            "messages": [{"role": "user", "content": large_content}]
        }
        test_file.write_text(json.dumps(test_data), encoding="utf-8")

        with patch("utils.conversation.config") as mock_config:
            mock_config.HISTORY_DIR = str(history_dir)
            mock_config.SYSTEM_PROMPT = "Test"
            mock_config.RESPONSE_LANGUAGE = ""
            mock_config.RESPONSE_LENGTH = ""
            mock_config.RESPONSE_TONE = ""
            mock_config.RESPONSE_FORMAT = ""
            mock_config.MAX_HISTORY_SIZE = 50

            manager = ConversationManager()

            with pytest.raises(ConversationLoadError) as exc_info:
                manager.load_from_file("large_content.json")

            assert "tamanho máximo" in str(exc_info.value)

    def test_load_preserves_current_system_prompt(self, tmp_path):
        """Carregar deve usar system prompt atual, não o salvo."""
        history_dir = tmp_path / "history"
        history_dir.mkdir()
        test_file = history_dir / "test.json"
        test_data = {
            "timestamp": "2024-01-01T12:00:00",
            "model": "old-model",
            "messages": [{"role": "user", "content": "Olá"}]
        }
        test_file.write_text(json.dumps(test_data), encoding="utf-8")

        with patch("utils.conversation.config") as mock_config:
            mock_config.HISTORY_DIR = str(history_dir)
            mock_config.SYSTEM_PROMPT = "NOVO PROMPT"
            mock_config.RESPONSE_LANGUAGE = ""
            mock_config.RESPONSE_LENGTH = ""
            mock_config.RESPONSE_TONE = ""
            mock_config.RESPONSE_FORMAT = ""
            mock_config.MAX_HISTORY_SIZE = 50

            manager = ConversationManager()
            manager.load_from_file("test.json")

            messages = manager.get_messages()
            assert messages[0]["role"] == "system"
            assert "NOVO PROMPT" in messages[0]["content"]


class TestListHistoryFiles:
    """Testes para listagem de arquivos."""

    def test_list_empty_directory(self, tmp_path):
        """Diretório vazio deve retornar lista vazia."""
        with patch("utils.conversation.config") as mock_config:
            mock_config.HISTORY_DIR = str(tmp_path)
            mock_config.SYSTEM_PROMPT = "Test"
            mock_config.RESPONSE_LANGUAGE = ""
            mock_config.RESPONSE_LENGTH = ""
            mock_config.RESPONSE_TONE = ""
            mock_config.RESPONSE_FORMAT = ""
            mock_config.MAX_HISTORY_SIZE = 50

            manager = ConversationManager()
            files = manager.list_history_files()

            assert files == []

    def test_list_nonexistent_directory(self, tmp_path):
        """Diretório inexistente deve retornar lista vazia."""
        with patch("utils.conversation.config") as mock_config:
            mock_config.HISTORY_DIR = str(tmp_path / "nonexistent")
            mock_config.SYSTEM_PROMPT = "Test"
            mock_config.RESPONSE_LANGUAGE = ""
            mock_config.RESPONSE_LENGTH = ""
            mock_config.RESPONSE_TONE = ""
            mock_config.RESPONSE_FORMAT = ""
            mock_config.MAX_HISTORY_SIZE = 50

            manager = ConversationManager()
            files = manager.list_history_files()

            assert files == []

    def test_list_with_files(self, tmp_path):
        """Deve listar arquivos JSON válidos."""
        history_dir = tmp_path / "history"
        history_dir.mkdir()

        for i in range(3):
            test_file = history_dir / f"history_{i}.json"
            test_data = {
                "timestamp": f"2024-01-0{i+1}T12:00:00",
                "model": f"model-{i}",
                "messages": []
            }
            test_file.write_text(json.dumps(test_data), encoding="utf-8")

        with patch("utils.conversation.config") as mock_config:
            mock_config.HISTORY_DIR = str(history_dir)
            mock_config.SYSTEM_PROMPT = "Test"
            mock_config.RESPONSE_LANGUAGE = ""
            mock_config.RESPONSE_LENGTH = ""
            mock_config.RESPONSE_TONE = ""
            mock_config.RESPONSE_FORMAT = ""
            mock_config.MAX_HISTORY_SIZE = 50

            manager = ConversationManager()
            files = manager.list_history_files()

            assert len(files) == 3
            assert files[0][1] == "2024-01-03T12:00:00"

    def test_list_ignores_invalid_json(self, tmp_path):
        """Arquivos JSON inválidos devem ser ignorados."""
        history_dir = tmp_path / "history"
        history_dir.mkdir()

        valid_file = history_dir / "valid.json"
        valid_file.write_text('{"timestamp": "2024-01-01", "model": "test", "messages": []}')

        invalid_file = history_dir / "invalid.json"
        invalid_file.write_text("not json")

        with patch("utils.conversation.config") as mock_config:
            mock_config.HISTORY_DIR = str(history_dir)
            mock_config.SYSTEM_PROMPT = "Test"
            mock_config.RESPONSE_LANGUAGE = ""
            mock_config.RESPONSE_LENGTH = ""
            mock_config.RESPONSE_TONE = ""
            mock_config.RESPONSE_FORMAT = ""
            mock_config.MAX_HISTORY_SIZE = 50

            manager = ConversationManager()
            files = manager.list_history_files()

            assert len(files) == 1
            assert files[0][0] == "valid.json"


class TestPathTraversalProtection:
    """Testes para proteção contra path traversal."""

    def test_absolute_path_is_blocked(self, tmp_path):
        """Caminhos absolutos devem ser convertidos para relativos."""
        history_dir = tmp_path / "history"
        history_dir.mkdir()
        test_file = history_dir / "test.json"
        test_data = {
            "timestamp": "2024-01-01T12:00:00",
            "model": "test",
            "messages": [{"role": "user", "content": "test"}]
        }
        test_file.write_text(json.dumps(test_data), encoding="utf-8")

        with patch("utils.conversation.config") as mock_config:
            mock_config.HISTORY_DIR = str(history_dir)
            mock_config.SYSTEM_PROMPT = "Test"
            mock_config.RESPONSE_LANGUAGE = ""
            mock_config.RESPONSE_LENGTH = ""
            mock_config.RESPONSE_TONE = ""
            mock_config.RESPONSE_FORMAT = ""
            mock_config.MAX_HISTORY_SIZE = 50

            manager = ConversationManager()
            count = manager.load_from_file("/etc/passwd/../../../test.json")

            assert count == 1

    def test_directory_traversal_blocked(self, tmp_path):
        """Tentativas de directory traversal devem ser bloqueadas."""
        history_dir = tmp_path / "history"
        history_dir.mkdir()
        test_file = history_dir / "test.json"
        test_data = {
            "timestamp": "2024-01-01T12:00:00",
            "model": "test",
            "messages": [{"role": "user", "content": "test"}]
        }
        test_file.write_text(json.dumps(test_data), encoding="utf-8")

        with patch("utils.conversation.config") as mock_config:
            mock_config.HISTORY_DIR = str(history_dir)
            mock_config.SYSTEM_PROMPT = "Test"
            mock_config.RESPONSE_LANGUAGE = ""
            mock_config.RESPONSE_LENGTH = ""
            mock_config.RESPONSE_TONE = ""
            mock_config.RESPONSE_FORMAT = ""
            mock_config.MAX_HISTORY_SIZE = 50

            manager = ConversationManager()
            count = manager.load_from_file("../../../test.json")

            assert count == 1


class TestUnicodeAndLargeMessages:
    """Testes para mensagens Unicode e mensagens grandes."""

    @patch("utils.conversation.config")
    def test_unicode_message_content(self, mock_config):
        """Verifica que mensagens com Unicode são tratadas corretamente."""
        mock_config.SYSTEM_PROMPT = "Test"
        mock_config.RESPONSE_LANGUAGE = ""
        mock_config.RESPONSE_LENGTH = ""
        mock_config.RESPONSE_TONE = ""
        mock_config.RESPONSE_FORMAT = ""
        mock_config.MAX_HISTORY_SIZE = 50

        manager = ConversationManager()

        unicode_message = "Olá! 你好! مرحبا! שלום! 🎉🚀💻"
        manager.add_user_message(unicode_message)

        messages = manager.get_messages()
        assert messages[-1]["content"] == unicode_message

    @patch("utils.conversation.config")
    def test_emoji_message(self, mock_config):
        """Verifica que mensagens com emojis são tratadas corretamente."""
        mock_config.SYSTEM_PROMPT = "Test"
        mock_config.RESPONSE_LANGUAGE = ""
        mock_config.RESPONSE_LENGTH = ""
        mock_config.RESPONSE_TONE = ""
        mock_config.RESPONSE_FORMAT = ""
        mock_config.MAX_HISTORY_SIZE = 50

        manager = ConversationManager()

        emoji_message = "Hello 👋 World 🌍! How are you? 🤔💭"
        manager.add_user_message(emoji_message)
        manager.add_assistant_message("I'm fine! 😊")

        messages = manager.get_messages()
        assert messages[-2]["content"] == emoji_message
        assert messages[-1]["content"] == "I'm fine! 😊"

    @patch("utils.conversation.config")
    def test_large_message_within_limit(self, mock_config):
        """Verifica que mensagem grande dentro do limite é aceita."""
        mock_config.SYSTEM_PROMPT = "Test"
        mock_config.RESPONSE_LANGUAGE = ""
        mock_config.RESPONSE_LENGTH = ""
        mock_config.RESPONSE_TONE = ""
        mock_config.RESPONSE_FORMAT = ""
        mock_config.MAX_HISTORY_SIZE = 50

        manager = ConversationManager()

        large_message = "A" * 50000
        manager.add_user_message(large_message)

        messages = manager.get_messages()
        assert len(messages[-1]["content"]) == 50000

    @patch("utils.conversation.config")
    def test_multiline_message(self, mock_config):
        """Verifica que mensagens multilinha são tratadas corretamente."""
        mock_config.SYSTEM_PROMPT = "Test"
        mock_config.RESPONSE_LANGUAGE = ""
        mock_config.RESPONSE_LENGTH = ""
        mock_config.RESPONSE_TONE = ""
        mock_config.RESPONSE_FORMAT = ""
        mock_config.MAX_HISTORY_SIZE = 50

        manager = ConversationManager()

        multiline = """Linha 1
        Linha 2
        Linha 3

        Linha com espaço acima"""
        manager.add_user_message(multiline)

        messages = manager.get_messages()
        assert messages[-1]["content"] == multiline
        assert messages[-1]["content"].count("\n") == 4

    @patch("utils.conversation.config")
    def test_special_characters_message(self, mock_config):
        """Verifica que caracteres especiais são tratados corretamente."""
        mock_config.SYSTEM_PROMPT = "Test"
        mock_config.RESPONSE_LANGUAGE = ""
        mock_config.RESPONSE_LENGTH = ""
        mock_config.RESPONSE_TONE = ""
        mock_config.RESPONSE_FORMAT = ""
        mock_config.MAX_HISTORY_SIZE = 50

        manager = ConversationManager()

        special = '<script>alert("XSS")</script> & "quotes" \'single\' `backticks`'
        manager.add_user_message(special)

        messages = manager.get_messages()
        assert messages[-1]["content"] == special

    @patch("utils.conversation.config")
    def test_load_file_with_large_message_at_limit(self, mock_config, tmp_path):
        """Verifica carregamento de arquivo com mensagem no limite."""
        mock_config.SYSTEM_PROMPT = "Test"
        mock_config.RESPONSE_LANGUAGE = ""
        mock_config.RESPONSE_LENGTH = ""
        mock_config.RESPONSE_TONE = ""
        mock_config.RESPONSE_FORMAT = ""
        mock_config.MAX_HISTORY_SIZE = 50
        mock_config.HISTORY_DIR = str(tmp_path)

        large_content = "X" * (MAX_MESSAGE_CONTENT_SIZE - 1)
        history_data = {
            "timestamp": "2024-01-01T00:00:00",
            "model": "test",
            "messages": [{"role": "user", "content": large_content}]
        }

        history_file = tmp_path / "large.json"
        import json
        with open(history_file, "w") as f:
            json.dump(history_data, f)

        manager = ConversationManager()
        count = manager.load_from_file("large.json")

        assert count == 1

    @patch("utils.conversation.config")
    def test_load_file_with_message_exceeding_limit(self, mock_config, tmp_path):
        """Verifica erro ao carregar mensagem que excede limite."""
        mock_config.SYSTEM_PROMPT = "Test"
        mock_config.RESPONSE_LANGUAGE = ""
        mock_config.RESPONSE_LENGTH = ""
        mock_config.RESPONSE_TONE = ""
        mock_config.RESPONSE_FORMAT = ""
        mock_config.MAX_HISTORY_SIZE = 50
        mock_config.HISTORY_DIR = str(tmp_path)

        too_large_content = "X" * (MAX_MESSAGE_CONTENT_SIZE + 1)
        history_data = {
            "timestamp": "2024-01-01T00:00:00",
            "model": "test",
            "messages": [{"role": "user", "content": too_large_content}]
        }

        history_file = tmp_path / "too_large.json"
        import json
        with open(history_file, "w") as f:
            json.dump(history_data, f)

        manager = ConversationManager()

        with pytest.raises(ConversationLoadError) as exc_info:
            manager.load_from_file("too_large.json")

        assert "tamanho máximo" in str(exc_info.value)


class TestMessageValidation:
    """Testes para validação de mensagens."""

    @patch("utils.conversation.config")
    def test_add_user_message_non_string_raises_error(self, mock_config):
        """Conteúdo não-string deve levantar TypeError."""
        mock_config.SYSTEM_PROMPT = "Test"
        mock_config.RESPONSE_LANGUAGE = ""
        mock_config.RESPONSE_LENGTH = ""
        mock_config.RESPONSE_TONE = ""
        mock_config.RESPONSE_FORMAT = ""
        mock_config.MAX_HISTORY_SIZE = 50

        manager = ConversationManager()

        with pytest.raises(TypeError) as exc_info:
            manager.add_user_message(123)

        assert "string" in str(exc_info.value)

    @patch("utils.conversation.config")
    def test_add_assistant_message_non_string_raises_error(self, mock_config):
        """Conteúdo não-string deve levantar TypeError."""
        mock_config.SYSTEM_PROMPT = "Test"
        mock_config.RESPONSE_LANGUAGE = ""
        mock_config.RESPONSE_LENGTH = ""
        mock_config.RESPONSE_TONE = ""
        mock_config.RESPONSE_FORMAT = ""
        mock_config.MAX_HISTORY_SIZE = 50

        manager = ConversationManager()

        with pytest.raises(TypeError) as exc_info:
            manager.add_assistant_message(["not", "a", "string"])

        assert "string" in str(exc_info.value)

    @patch("utils.conversation.config")
    def test_add_user_message_too_large_raises_error(self, mock_config):
        """Mensagem muito grande deve levantar ValueError."""
        mock_config.SYSTEM_PROMPT = "Test"
        mock_config.RESPONSE_LANGUAGE = ""
        mock_config.RESPONSE_LENGTH = ""
        mock_config.RESPONSE_TONE = ""
        mock_config.RESPONSE_FORMAT = ""
        mock_config.MAX_HISTORY_SIZE = 50

        manager = ConversationManager()
        large_content = "x" * (MAX_MESSAGE_CONTENT_SIZE + 1)

        with pytest.raises(ValueError) as exc_info:
            manager.add_user_message(large_content)

        assert "tamanho máximo" in str(exc_info.value)

    @patch("utils.conversation.config")
    def test_add_assistant_message_too_large_raises_error(self, mock_config):
        """Mensagem muito grande deve levantar ValueError."""
        mock_config.SYSTEM_PROMPT = "Test"
        mock_config.RESPONSE_LANGUAGE = ""
        mock_config.RESPONSE_LENGTH = ""
        mock_config.RESPONSE_TONE = ""
        mock_config.RESPONSE_FORMAT = ""
        mock_config.MAX_HISTORY_SIZE = 50

        manager = ConversationManager()
        large_content = "x" * (MAX_MESSAGE_CONTENT_SIZE + 1)

        with pytest.raises(ValueError) as exc_info:
            manager.add_assistant_message(large_content)

        assert "tamanho máximo" in str(exc_info.value)

    @patch("utils.conversation.config")
    def test_add_message_at_size_limit_succeeds(self, mock_config):
        """Mensagem exatamente no limite deve ser aceita."""
        mock_config.SYSTEM_PROMPT = "Test"
        mock_config.RESPONSE_LANGUAGE = ""
        mock_config.RESPONSE_LENGTH = ""
        mock_config.RESPONSE_TONE = ""
        mock_config.RESPONSE_FORMAT = ""
        mock_config.MAX_HISTORY_SIZE = 50

        manager = ConversationManager()
        content_at_limit = "x" * MAX_MESSAGE_CONTENT_SIZE

        manager.add_user_message(content_at_limit)
        assert manager.message_count() == 1


class TestConcurrentSaveOperations:
    """Testes para operações de salvamento concorrentes."""

    def test_concurrent_save_to_different_files(self, tmp_path, monkeypatch):
        """Salvamentos concorrentes em arquivos diferentes devem funcionar."""
        import threading
        monkeypatch.chdir(tmp_path)

        manager = ConversationManager()
        manager.add_user_message("Test message")
        manager.add_assistant_message("Test response")

        errors = []
        saved_paths = []

        def save_file(filename):
            try:
                path = manager.save_to_file(filename)
                saved_paths.append(path)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=save_file, args=(f"history_{i}.json",))
            for i in range(5)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(saved_paths) == 5
        for path in saved_paths:
            assert os.path.exists(path)

    def test_concurrent_save_same_file(self, tmp_path, monkeypatch):
        """Salvamentos concorrentes no mesmo arquivo devem ser seguros."""
        import threading
        monkeypatch.chdir(tmp_path)

        manager = ConversationManager()
        manager.add_user_message("Test message")

        errors = []
        success_count = [0]

        def save_file():
            try:
                manager.save_to_file("shared.json")
                success_count[0] += 1
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=save_file) for _ in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert success_count[0] == 10
        assert os.path.exists(tmp_path / "history" / "shared.json")
