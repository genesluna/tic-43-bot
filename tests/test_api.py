"""Testes para o módulo de API."""

import pytest
from unittest.mock import patch, MagicMock
import httpx
from utils.api import OpenRouterClient, APIError, count_tokens


class TestCountTokens:
    """Testes para a função count_tokens."""

    def test_count_tokens_simple(self):
        """Verifica contagem de tokens em texto simples."""
        text = "Hello, world!"
        tokens = count_tokens(text)

        assert tokens > 0
        assert isinstance(tokens, int)

    def test_count_tokens_empty(self):
        """Verifica contagem de tokens em texto vazio."""
        tokens = count_tokens("")

        assert tokens == 0

    def test_count_tokens_portuguese(self):
        """Verifica contagem de tokens em português."""
        text = "Olá, como você está?"
        tokens = count_tokens(text)

        assert tokens > 0

    def test_count_tokens_with_unknown_model(self):
        """Verifica fallback para modelo desconhecido."""
        text = "Test text"
        tokens = count_tokens(text, model="unknown-model")

        assert tokens > 0


class TestOpenRouterClient:
    """Testes para a classe OpenRouterClient."""

    def test_init(self):
        """Verifica se o cliente é inicializado corretamente."""
        client = OpenRouterClient()

        assert client.base_url == "https://openrouter.ai/api/v1/chat/completions"
        assert client.model is not None

    def test_get_headers(self):
        """Verifica se os headers são gerados corretamente."""
        client = OpenRouterClient()
        headers = client._get_headers()

        assert "Authorization" in headers
        assert "Content-Type" in headers
        assert headers["Content-Type"] == "application/json"

    def test_get_model(self):
        """Verifica se o modelo pode ser obtido."""
        client = OpenRouterClient()
        model = client.get_model()

        assert model is not None
        assert len(model) > 0

    def test_set_model(self):
        """Verifica se o modelo pode ser alterado."""
        client = OpenRouterClient()
        new_model = "anthropic/claude-3-haiku"

        client.set_model(new_model)

        assert client.get_model() == new_model

    def test_send_message_without_api_key(self):
        """Verifica se erro é levantado quando não há API key."""
        with patch("utils.api.config") as mock_config:
            mock_config.OPENROUTER_API_KEY = ""
            mock_config.OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
            mock_config.OPENROUTER_MODEL = "openai/gpt-4o-mini"

            client = OpenRouterClient()
            client.api_key = ""

            with pytest.raises(APIError) as exc_info:
                client.send_message([{"role": "user", "content": "Olá"}])

            assert "Chave da API não configurada" in str(exc_info.value)

    @patch("utils.api.httpx.Client")
    def test_send_message_success(self, mock_client_class):
        """Verifica se mensagens são enviadas com sucesso."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Olá! Como posso ajudar?"}}]
        }

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = OpenRouterClient()
        client.api_key = "test_key"

        response = client.send_message([{"role": "user", "content": "Olá"}])

        assert response == "Olá! Como posso ajudar?"

    @patch("utils.api.httpx.Client")
    def test_send_message_unauthorized(self, mock_client_class):
        """Verifica se erro 401 é tratado corretamente."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = OpenRouterClient()
        client.api_key = "invalid_key"

        with pytest.raises(APIError) as exc_info:
            client.send_message([{"role": "user", "content": "Olá"}])

        assert "Chave de API inválida" in str(exc_info.value)

    @patch("utils.api.httpx.Client")
    def test_send_message_rate_limit(self, mock_client_class):
        """Verifica se erro 429 é tratado corretamente."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Too Many Requests"

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = OpenRouterClient()
        client.api_key = "test_key"

        with pytest.raises(APIError) as exc_info:
            client.send_message([{"role": "user", "content": "Olá"}])

        assert "Limite de requisições excedido" in str(exc_info.value)

    @patch("utils.api.httpx.Client")
    def test_send_message_timeout(self, mock_client_class):
        """Verifica se timeout é tratado corretamente."""
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = httpx.TimeoutException("Timeout")
        mock_client_class.return_value = mock_client

        client = OpenRouterClient()
        client.api_key = "test_key"

        with pytest.raises(APIError) as exc_info:
            client.send_message([{"role": "user", "content": "Olá"}])

        assert "Tempo limite excedido" in str(exc_info.value)

    @patch("utils.api.httpx.Client")
    def test_send_message_connection_error(self, mock_client_class):
        """Verifica se erro de conexão é tratado corretamente."""
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = httpx.ConnectError("Connection failed")
        mock_client_class.return_value = mock_client

        client = OpenRouterClient()
        client.api_key = "test_key"

        with pytest.raises(APIError) as exc_info:
            client.send_message([{"role": "user", "content": "Olá"}])

        assert "Não foi possível conectar" in str(exc_info.value)

    @patch("utils.api.httpx.Client")
    def test_send_message_invalid_response(self, mock_client_class):
        """Verifica se resposta inválida é tratada corretamente."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"invalid": "response"}

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = OpenRouterClient()
        client.api_key = "test_key"

        with pytest.raises(APIError) as exc_info:
            client.send_message([{"role": "user", "content": "Olá"}])

        assert "não contém dados válidos" in str(exc_info.value)

    def test_send_message_stream_without_api_key(self):
        """Verifica se erro é levantado no streaming quando não há API key."""
        with patch("utils.api.config") as mock_config:
            mock_config.OPENROUTER_API_KEY = ""
            mock_config.OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
            mock_config.OPENROUTER_MODEL = "openai/gpt-4o-mini"

            client = OpenRouterClient()
            client.api_key = ""

            with pytest.raises(APIError) as exc_info:
                list(client.send_message_stream([{"role": "user", "content": "Olá"}]))

            assert "Chave da API não configurada" in str(exc_info.value)

    def test_send_message_stream_empty_messages(self):
        """Verifica se erro é levantado quando lista de mensagens está vazia."""
        client = OpenRouterClient()
        client.api_key = "test_key"

        with pytest.raises(APIError) as exc_info:
            list(client.send_message_stream([]))

        assert "Lista de mensagens não pode estar vazia" in str(exc_info.value)

    @patch("utils.api.httpx.Client")
    def test_send_message_stream_success(self, mock_client_class):
        """Verifica se streaming funciona corretamente."""
        mock_stream_response = MagicMock()
        mock_stream_response.status_code = 200
        mock_stream_response.iter_lines.return_value = [
            'data: {"choices": [{"delta": {"content": "Olá"}}]}',
            'data: {"choices": [{"delta": {"content": "!"}}]}',
            'data: {"choices": [{"delta": {"content": " Como"}}]}',
            'data: {"choices": [{"delta": {"content": " vai?"}}]}',
            'data: [DONE]',
        ]
        mock_stream_response.__enter__ = MagicMock(return_value=mock_stream_response)
        mock_stream_response.__exit__ = MagicMock(return_value=False)

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.stream.return_value = mock_stream_response
        mock_client_class.return_value = mock_client

        client = OpenRouterClient()
        client.api_key = "test_key"

        chunks = list(client.send_message_stream([{"role": "user", "content": "Olá"}]))

        assert chunks == ["Olá", "!", " Como", " vai?"]

    @patch("utils.api.httpx.Client")
    def test_send_message_stream_unauthorized(self, mock_client_class):
        """Verifica se erro 401 é tratado corretamente no streaming."""
        mock_stream_response = MagicMock()
        mock_stream_response.status_code = 401
        mock_stream_response.__enter__ = MagicMock(return_value=mock_stream_response)
        mock_stream_response.__exit__ = MagicMock(return_value=False)

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.stream.return_value = mock_stream_response
        mock_client_class.return_value = mock_client

        client = OpenRouterClient()
        client.api_key = "invalid_key"

        with pytest.raises(APIError) as exc_info:
            list(client.send_message_stream([{"role": "user", "content": "Olá"}]))

        assert "Chave de API inválida" in str(exc_info.value)
