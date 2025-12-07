"""Testes para o módulo de API."""

import gc
import pytest
import threading
import time
from unittest.mock import patch, MagicMock
import httpx
from utils.api import OpenRouterClient, APIError, RateLimitError, StreamingResponse, APIResponse
from utils.config import MAX_MESSAGE_CONTENT_SIZE


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
        assert "User-Agent" in headers
        assert "TIC43-Chatbot" in headers["User-Agent"]

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

    def test_set_model_none(self):
        """Verifica se None levanta ValueError."""
        client = OpenRouterClient()

        with pytest.raises(ValueError) as exc_info:
            client.set_model(None)

        assert "provider/model-name" in str(exc_info.value)

    def test_set_model_empty_string(self):
        """Verifica se string vazia levanta ValueError."""
        client = OpenRouterClient()

        with pytest.raises(ValueError) as exc_info:
            client.set_model("")

        assert "provider/model-name" in str(exc_info.value)

    def test_set_model_whitespace_only(self):
        """Verifica se string com apenas espaços levanta ValueError."""
        client = OpenRouterClient()

        with pytest.raises(ValueError) as exc_info:
            client.set_model("   ")

        assert "não pode estar vazio" in str(exc_info.value)

    def test_set_model_no_slash(self):
        """Verifica se modelo sem barra levanta ValueError."""
        client = OpenRouterClient()

        with pytest.raises(ValueError) as exc_info:
            client.set_model("gpt-4o-mini")

        assert "provider/model-name" in str(exc_info.value)
        assert "gpt-4o-mini" in str(exc_info.value)

    def test_set_model_strips_whitespace(self):
        """Verifica se espaços são removidos do modelo."""
        client = OpenRouterClient()

        client.set_model("  openai/gpt-4o  ")

        assert client.get_model() == "openai/gpt-4o"

    def test_send_message_without_api_key(self):
        """Verifica se erro é levantado quando não há API key."""
        with patch("utils.api.config") as mock_config:
            mock_config.OPENROUTER_API_KEY = ""
            mock_config.OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
            mock_config.OPENROUTER_MODEL = "openai/gpt-4o-mini"

            client = OpenRouterClient()
            client._api_key = ""

            with pytest.raises(APIError) as exc_info:
                client.send_message([{"role": "user", "content": "Olá"}])

            assert "Chave de API não configurada" in str(exc_info.value)

    @patch("utils.api.httpx.Client")
    def test_send_message_success(self, mock_client_class):
        """Verifica se mensagens são enviadas com sucesso."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Olá! Como posso ajudar?"}}],
            "usage": {"total_tokens": 150}
        }

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = OpenRouterClient()
        client._api_key = "test_key"

        response = client.send_message([{"role": "user", "content": "Olá"}])

        assert isinstance(response, APIResponse)
        assert response.content == "Olá! Como posso ajudar?"
        assert response.total_tokens == 150

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
        client._api_key = "invalid_key"

        with pytest.raises(APIError) as exc_info:
            client.send_message([{"role": "user", "content": "Olá"}])

        assert "Chave de API inválida" in str(exc_info.value)

    @patch("utils.api.time.sleep")
    @patch("utils.api.httpx.Client")
    def test_send_message_rate_limit(self, mock_client_class, mock_sleep):
        """Verifica se erro 429 é tratado com retry e RateLimitError."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Too Many Requests"
        mock_response.headers = {"Retry-After": "5"}

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = OpenRouterClient()
        client._api_key = "test_key"

        with pytest.raises(RateLimitError) as exc_info:
            client.send_message([{"role": "user", "content": "Olá"}])

        assert "Limite de requisições excedido" in str(exc_info.value)
        assert exc_info.value.retry_after == 5.0
        assert mock_sleep.call_count == 2

    @patch("utils.api.httpx.Client")
    def test_send_message_timeout(self, mock_client_class):
        """Verifica se timeout é tratado corretamente."""
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = httpx.TimeoutException("Timeout")
        mock_client_class.return_value = mock_client

        client = OpenRouterClient()
        client._api_key = "test_key"

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
        client._api_key = "test_key"

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
        client._api_key = "test_key"

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
            client._api_key = ""

            with pytest.raises(APIError) as exc_info:
                list(client.send_message_stream([{"role": "user", "content": "Olá"}]))

            assert "Chave de API não configurada" in str(exc_info.value)

    def test_send_message_stream_empty_messages(self):
        """Verifica se erro é levantado quando lista de mensagens está vazia."""
        client = OpenRouterClient()
        client._api_key = "test_key"

        with pytest.raises(APIError) as exc_info:
            list(client.send_message_stream([]))

        assert "Lista de mensagens não pode estar vazia" in str(exc_info.value)

    def test_send_message_empty_messages(self):
        """Verifica se erro é levantado quando lista de mensagens está vazia."""
        client = OpenRouterClient()
        client._api_key = "test_key"

        with pytest.raises(APIError) as exc_info:
            client.send_message([])

        assert "Lista de mensagens não pode estar vazia" in str(exc_info.value)

    @patch("utils.api.httpx.Client")
    def test_send_message_null_content(self, mock_client_class):
        """Verifica se resposta com content None é tratada."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": None}}]
        }

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = OpenRouterClient()
        client._api_key = "test_key"

        with pytest.raises(APIError) as exc_info:
            client.send_message([{"role": "user", "content": "Olá"}])

        assert "não contém conteúdo" in str(exc_info.value)

    @patch("utils.api.httpx.Client")
    def test_send_message_generic_error(self, mock_client_class):
        """Verifica se erro 500 é tratado corretamente."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = OpenRouterClient()
        client._api_key = "test_key"

        with pytest.raises(APIError) as exc_info:
            client.send_message([{"role": "user", "content": "Olá"}])

        assert "Erro na API (500)" in str(exc_info.value)

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
        client._api_key = "test_key"

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
        client._api_key = "invalid_key"

        with pytest.raises(APIError) as exc_info:
            list(client.send_message_stream([{"role": "user", "content": "Olá"}]))

        assert "Chave de API inválida" in str(exc_info.value)

    @patch("utils.api.time.sleep")
    @patch("utils.api.httpx.Client")
    def test_send_message_stream_rate_limit(self, mock_client_class, mock_sleep):
        """Verifica se erro 429 é tratado com retry no streaming."""
        mock_stream_response = MagicMock()
        mock_stream_response.status_code = 429
        mock_stream_response.headers = {}
        mock_stream_response.__enter__ = MagicMock(return_value=mock_stream_response)
        mock_stream_response.__exit__ = MagicMock(return_value=False)

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.stream.return_value = mock_stream_response
        mock_client_class.return_value = mock_client

        client = OpenRouterClient()
        client._api_key = "test_key"

        with pytest.raises(RateLimitError) as exc_info:
            list(client.send_message_stream([{"role": "user", "content": "Olá"}]))

        assert "Limite de requisições excedido" in str(exc_info.value)
        assert mock_sleep.call_count == 2


class TestRateLimitError:
    """Testes para a classe RateLimitError."""

    def test_inherits_from_api_error(self):
        """RateLimitError deve herdar de APIError."""
        assert issubclass(RateLimitError, APIError)

    def test_retry_after_attribute(self):
        """RateLimitError deve armazenar retry_after."""
        error = RateLimitError("Rate limited", retry_after=30.0)
        assert error.retry_after == 30.0
        assert str(error) == "Rate limited"

    def test_retry_after_none(self):
        """RateLimitError deve aceitar retry_after=None."""
        error = RateLimitError("Rate limited")
        assert error.retry_after is None


class TestBackoffCalculation:
    """Testes para cálculo de backoff."""

    def test_calculate_backoff_with_retry_after(self):
        """Deve usar retry_after quando fornecido."""
        client = OpenRouterClient()
        result = client._calculate_backoff(0, retry_after=5.0)
        assert result == 5.0

    def test_calculate_backoff_retry_after_respects_max(self):
        """retry_after deve respeitar o máximo."""
        client = OpenRouterClient()
        result = client._calculate_backoff(0, retry_after=100.0)
        assert result == 30.0

    @patch("utils.api.random.random", return_value=0.5)
    def test_calculate_backoff_exponential(self, mock_random):
        """Deve calcular backoff exponencial com jitter."""
        client = OpenRouterClient()
        result_0 = client._calculate_backoff(0)
        result_1 = client._calculate_backoff(1)
        result_2 = client._calculate_backoff(2)

        assert result_0 == 1.0
        assert result_1 == 2.0
        assert result_2 == 4.0

    @patch("utils.api.random.random", return_value=0.5)
    def test_calculate_backoff_respects_max(self, mock_random):
        """Backoff não deve exceder o máximo."""
        client = OpenRouterClient()
        result = client._calculate_backoff(10)
        assert result == 30.0

    def test_calculate_backoff_has_jitter(self):
        """Backoff deve incluir jitter (variação aleatória)."""
        client = OpenRouterClient()
        results = [client._calculate_backoff(1) for _ in range(10)]
        assert len(set(results)) > 1


class TestRetryAfterHeader:
    """Testes para parsing do header Retry-After."""

    def test_get_retry_after_valid(self):
        """Deve parsear header Retry-After válido."""
        client = OpenRouterClient()
        response = MagicMock()
        response.headers = {"Retry-After": "45"}
        result = client._get_retry_after(response)
        assert result == 45.0

    def test_get_retry_after_float(self):
        """Deve parsear header Retry-After com float."""
        client = OpenRouterClient()
        response = MagicMock()
        response.headers = {"Retry-After": "2.5"}
        result = client._get_retry_after(response)
        assert result == 2.5

    def test_get_retry_after_invalid(self):
        """Deve retornar None para Retry-After inválido."""
        client = OpenRouterClient()
        response = MagicMock()
        response.headers = {"Retry-After": "invalid"}
        result = client._get_retry_after(response)
        assert result is None

    def test_get_retry_after_missing(self):
        """Deve retornar None quando header não existe."""
        client = OpenRouterClient()
        response = MagicMock()
        response.headers = {}
        result = client._get_retry_after(response)
        assert result is None


class TestRetrySuccess:
    """Testes para retry bem-sucedido após falha inicial."""

    @patch("utils.api.time.sleep")
    @patch("utils.api.httpx.Client")
    def test_send_message_retry_success_after_rate_limit(self, mock_client_class, mock_sleep):
        """Deve retornar resposta após retry bem-sucedido de rate limit."""
        mock_rate_limit_response = MagicMock()
        mock_rate_limit_response.status_code = 429
        mock_rate_limit_response.headers = {}

        mock_success_response = MagicMock()
        mock_success_response.status_code = 200
        mock_success_response.json.return_value = {
            "choices": [{"message": {"content": "Resposta de sucesso"}}],
            "usage": {"total_tokens": 100}
        }

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = [mock_rate_limit_response, mock_success_response]
        mock_client_class.return_value = mock_client

        client = OpenRouterClient()
        client._api_key = "test_key"

        result = client.send_message([{"role": "user", "content": "Olá"}])

        assert result.content == "Resposta de sucesso"
        assert mock_sleep.call_count == 1
        assert mock_client.post.call_count == 2

    @patch("utils.api.time.sleep")
    @patch("utils.api.httpx.Client")
    def test_send_message_retry_success_after_timeout(self, mock_client_class, mock_sleep):
        """Deve retornar resposta após retry bem-sucedido de timeout."""
        mock_success_response = MagicMock()
        mock_success_response.status_code = 200
        mock_success_response.json.return_value = {
            "choices": [{"message": {"content": "Resposta após timeout"}}],
            "usage": {"total_tokens": 100}
        }

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = [
            httpx.TimeoutException("Timeout"),
            mock_success_response
        ]
        mock_client_class.return_value = mock_client

        client = OpenRouterClient()
        client._api_key = "test_key"

        result = client.send_message([{"role": "user", "content": "Olá"}])

        assert result.content == "Resposta após timeout"
        assert mock_sleep.call_count == 1
        assert mock_client.post.call_count == 2

    @patch("utils.api.time.sleep")
    @patch("utils.api.httpx.Client")
    def test_send_message_retry_success_after_connection_error(self, mock_client_class, mock_sleep):
        """Deve retornar resposta após retry bem-sucedido de erro de conexão."""
        mock_success_response = MagicMock()
        mock_success_response.status_code = 200
        mock_success_response.json.return_value = {
            "choices": [{"message": {"content": "Resposta após erro de conexão"}}],
            "usage": {"total_tokens": 100}
        }

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = [
            httpx.ConnectError("Connection failed"),
            mock_success_response
        ]
        mock_client_class.return_value = mock_client

        client = OpenRouterClient()
        client._api_key = "test_key"

        result = client.send_message([{"role": "user", "content": "Olá"}])

        assert result.content == "Resposta após erro de conexão"
        assert mock_sleep.call_count == 1
        assert mock_client.post.call_count == 2


class TestOpenRouterClientClose:
    """Testes para o método close()."""

    @patch("utils.api.httpx.Client")
    def test_close_closes_client(self, mock_client_class):
        """Verifica que close() fecha o cliente HTTP."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        client = OpenRouterClient()
        client._api_key = "test_key"
        _ = client._get_client()

        client.close()

        mock_client.close.assert_called_once()
        assert client._client is None

    def test_close_without_client(self):
        """Verifica que close() sem cliente não causa erro."""
        client = OpenRouterClient()
        client._api_key = "test_key"

        client.close()

        assert client._client is None

    @patch("utils.api.httpx.Client")
    def test_close_multiple_times(self, mock_client_class):
        """Verifica que close() pode ser chamado múltiplas vezes."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        client = OpenRouterClient()
        client._api_key = "test_key"
        _ = client._get_client()

        client.close()
        client.close()

        mock_client.close.assert_called_once()


class TestMessageValidation:
    """Testes para validação de mensagens."""

    def test_validate_messages_empty_list(self):
        """Verifica erro com lista vazia."""
        client = OpenRouterClient()
        client._api_key = "test_key"

        with pytest.raises(APIError) as exc_info:
            client._validate_messages([])

        assert "vazia" in str(exc_info.value)

    def test_validate_messages_invalid_type(self):
        """Verifica erro com item que não é dicionário."""
        client = OpenRouterClient()
        client._api_key = "test_key"

        with pytest.raises(APIError) as exc_info:
            client._validate_messages(["not a dict"])

        assert "dicionário" in str(exc_info.value)

    def test_validate_messages_missing_role(self):
        """Verifica erro quando falta campo role."""
        client = OpenRouterClient()
        client._api_key = "test_key"

        with pytest.raises(APIError) as exc_info:
            client._validate_messages([{"content": "test"}])

        assert "role" in str(exc_info.value)

    def test_validate_messages_missing_content(self):
        """Verifica erro quando falta campo content."""
        client = OpenRouterClient()
        client._api_key = "test_key"

        with pytest.raises(APIError) as exc_info:
            client._validate_messages([{"role": "user"}])

        assert "content" in str(exc_info.value)

    def test_validate_messages_invalid_role(self):
        """Verifica erro com role inválido."""
        client = OpenRouterClient()
        client._api_key = "test_key"

        with pytest.raises(APIError) as exc_info:
            client._validate_messages([{"role": "invalid", "content": "test"}])

        assert "inválido" in str(exc_info.value)

    def test_validate_messages_non_string_content(self):
        """Verifica erro com content não-string."""
        client = OpenRouterClient()
        client._api_key = "test_key"

        with pytest.raises(APIError) as exc_info:
            client._validate_messages([{"role": "user", "content": 123}])

        assert "não-string" in str(exc_info.value)

    def test_validate_messages_valid(self):
        """Verifica que mensagens válidas passam."""
        client = OpenRouterClient()
        client._api_key = "test_key"

        client._validate_messages([
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ])

    def test_validate_messages_content_too_large(self):
        """Verifica erro quando conteúdo excede tamanho máximo."""
        client = OpenRouterClient()
        client._api_key = "test_key"

        large_content = "x" * (MAX_MESSAGE_CONTENT_SIZE + 1)

        with pytest.raises(APIError) as exc_info:
            client._validate_messages([{"role": "user", "content": large_content}])

        assert "tamanho máximo" in str(exc_info.value)

    def test_validate_messages_content_at_limit(self):
        """Verifica que conteúdo exatamente no limite é aceito."""
        client = OpenRouterClient()
        client._api_key = "test_key"

        content_at_limit = "x" * MAX_MESSAGE_CONTENT_SIZE

        # Should not raise
        client._validate_messages([{"role": "user", "content": content_at_limit}])


class TestAPIResponse:
    """Testes para a classe APIResponse."""

    def test_repr_short_content(self):
        """Verifica __repr__ com conteúdo curto (sem truncation)."""
        response = APIResponse(content="Hello world", total_tokens=10)
        repr_str = repr(response)

        assert "Hello world" in repr_str
        assert "..." not in repr_str
        assert "tokens=10" in repr_str

    def test_repr_long_content_truncated(self):
        """Verifica __repr__ com conteúdo longo (com truncation)."""
        long_content = "x" * 100
        response = APIResponse(content=long_content, total_tokens=50)
        repr_str = repr(response)

        assert "..." in repr_str
        assert "tokens=50" in repr_str
        assert "x" * 51 not in repr_str

    def test_repr_exactly_50_chars(self):
        """Verifica __repr__ com exatamente 50 caracteres (sem truncation)."""
        content_50 = "a" * 50
        response = APIResponse(content=content_50, total_tokens=25)
        repr_str = repr(response)

        assert content_50 in repr_str
        assert "..." not in repr_str

    def test_repr_51_chars(self):
        """Verifica __repr__ com 51 caracteres (com truncation)."""
        content_51 = "b" * 51
        response = APIResponse(content=content_51, total_tokens=30)
        repr_str = repr(response)

        assert "..." in repr_str
        assert content_51 not in repr_str


class TestStreamingResponse:
    """Testes para a classe StreamingResponse."""

    def test_init(self):
        """Verifica inicialização da StreamingResponse."""
        client = OpenRouterClient()
        gen = iter(["chunk1", "chunk2"])
        response = StreamingResponse(client, gen)

        assert response._client is client
        assert response._closed is False

    def test_repr(self):
        """Verifica representação string."""
        client = OpenRouterClient()
        gen = iter([])
        response = StreamingResponse(client, gen)

        assert "StreamingResponse" in repr(response)
        assert "closed=False" in repr(response)

    def test_iteration(self):
        """Verifica que iteração funciona corretamente."""
        client = OpenRouterClient()
        client._active_requests = 1
        chunks = ["chunk1", "chunk2", "chunk3"]
        gen = iter(chunks)
        response = StreamingResponse(client, gen)

        result = list(response)

        assert result == chunks
        assert response._closed is True
        assert client._active_requests == 0

    def test_cleanup_on_exhaustion(self):
        """Verifica cleanup quando generator é completamente consumido."""
        client = OpenRouterClient()
        client._active_requests = 1
        response = StreamingResponse(client, iter(["a", "b"]))

        list(response)

        assert client._active_requests == 0
        assert response._closed is True

    def test_cleanup_on_exception(self):
        """Verifica cleanup quando exceção ocorre durante iteração."""
        client = OpenRouterClient()
        client._active_requests = 1

        def failing_generator():
            yield "first"
            raise ValueError("Test error")

        response = StreamingResponse(client, failing_generator())

        with pytest.raises(ValueError):
            list(response)

        assert client._active_requests == 0
        assert response._closed is True

    def test_cleanup_idempotent(self):
        """Verifica que _cleanup é idempotente."""
        client = OpenRouterClient()
        client._active_requests = 1
        response = StreamingResponse(client, iter([]))

        response._cleanup()
        response._cleanup()
        response._cleanup()

        assert client._active_requests == 0

    def test_cleanup_thread_safe(self):
        """Verifica que _cleanup é thread-safe com chamadas concorrentes."""
        client = OpenRouterClient()
        client._active_requests = 1
        response = StreamingResponse(client, iter(["a", "b", "c"]))
        errors = []

        def call_cleanup():
            try:
                for _ in range(10):
                    response._cleanup()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=call_cleanup) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert client._active_requests == 0
        assert response._closed is True

    def test_close_method(self):
        """Verifica método close() explícito."""
        client = OpenRouterClient()
        client._active_requests = 1
        response = StreamingResponse(client, iter(["a", "b", "c"]))

        next(response)
        response.close()

        assert client._active_requests == 0
        assert response._closed is True

    def test_iteration_after_close_raises_stop_iteration(self):
        """Verifica que iteração após close levanta StopIteration."""
        client = OpenRouterClient()
        client._active_requests = 1
        response = StreamingResponse(client, iter(["a", "b"]))

        next(response)
        response.close()

        with pytest.raises(StopIteration):
            next(response)

    def test_del_triggers_cleanup(self):
        """Verifica que __del__ dispara cleanup."""
        client = OpenRouterClient()
        client._active_requests = 1
        response = StreamingResponse(client, iter(["a", "b"]))

        next(response)
        del response
        gc.collect()

        assert client._active_requests == 0

    def test_context_manager_enter(self):
        """Verifica que __enter__ retorna self."""
        client = OpenRouterClient()
        response = StreamingResponse(client, iter(["a", "b"]))

        result = response.__enter__()

        assert result is response

    def test_context_manager_exit_cleanup(self):
        """Verifica que __exit__ dispara cleanup."""
        client = OpenRouterClient()
        client._active_requests = 1
        response = StreamingResponse(client, iter(["a", "b"]))

        response.__enter__()
        next(response)
        response.__exit__(None, None, None)

        assert client._active_requests == 0
        assert response._closed is True

    def test_context_manager_with_statement(self):
        """Verifica uso com 'with' statement."""
        client = OpenRouterClient()
        client._active_requests = 1
        chunks = ["a", "b", "c"]
        response = StreamingResponse(client, iter(chunks))

        result = []
        with response as stream:
            for chunk in stream:
                result.append(chunk)

        assert result == chunks
        assert client._active_requests == 0
        assert response._closed is True

    def test_context_manager_with_break(self):
        """Verifica cleanup quando 'with' é abandonado com break."""
        client = OpenRouterClient()
        client._active_requests = 1
        response = StreamingResponse(client, iter(["a", "b", "c"]))

        with response as stream:
            next(stream)
            # Simula break saindo do loop sem consumir generator
            pass

        assert client._active_requests == 0
        assert response._closed is True

    def test_context_manager_with_exception(self):
        """Verifica cleanup quando exceção ocorre dentro do 'with'."""
        client = OpenRouterClient()
        client._active_requests = 1
        response = StreamingResponse(client, iter(["a", "b", "c"]))

        with pytest.raises(RuntimeError):
            with response as stream:
                next(stream)
                raise RuntimeError("Test error")

        assert client._active_requests == 0
        assert response._closed is True


class TestStreamingResponseCleanup:
    """Testes de cleanup do StreamingResponse em cenários reais."""

    @patch("utils.api.httpx.Client")
    def test_abandoned_generator_cleanup(self, mock_client_class):
        """Verifica cleanup quando generator é abandonado."""
        mock_stream_response = MagicMock()
        mock_stream_response.status_code = 200
        mock_stream_response.iter_lines.return_value = iter([
            'data: {"choices": [{"delta": {"content": "chunk1"}}]}',
            'data: {"choices": [{"delta": {"content": "chunk2"}}]}',
            'data: {"choices": [{"delta": {"content": "chunk3"}}]}',
            'data: [DONE]',
        ])
        mock_stream_response.__enter__ = MagicMock(return_value=mock_stream_response)
        mock_stream_response.__exit__ = MagicMock(return_value=False)

        mock_client = MagicMock()
        mock_client.stream.return_value = mock_stream_response
        mock_client_class.return_value = mock_client

        client = OpenRouterClient()
        client._api_key = "test_key"

        response = client.send_message_stream([{"role": "user", "content": "test"}])
        next(response)
        del response
        gc.collect()

        assert client._active_requests == 0

    @patch("utils.api.httpx.Client")
    def test_partial_consumption_cleanup(self, mock_client_class):
        """Verifica cleanup após consumo parcial do generator."""
        mock_stream_response = MagicMock()
        mock_stream_response.status_code = 200
        mock_stream_response.iter_lines.return_value = iter([
            'data: {"choices": [{"delta": {"content": "1"}}]}',
            'data: {"choices": [{"delta": {"content": "2"}}]}',
            'data: {"choices": [{"delta": {"content": "3"}}]}',
            'data: [DONE]',
        ])
        mock_stream_response.__enter__ = MagicMock(return_value=mock_stream_response)
        mock_stream_response.__exit__ = MagicMock(return_value=False)

        mock_client = MagicMock()
        mock_client.stream.return_value = mock_stream_response
        mock_client_class.return_value = mock_client

        client = OpenRouterClient()
        client._api_key = "test_key"

        response = client.send_message_stream([{"role": "user", "content": "test"}])
        next(response)
        next(response)
        response.close()

        assert client._active_requests == 0


class TestConcurrentAPIAccess:
    """Testes de concorrência para o cliente API."""

    def test_concurrent_get_client(self):
        """Verifica que _get_client é thread-safe."""
        client = OpenRouterClient()
        clients_obtained = []
        errors = []

        def get_client():
            try:
                c = client._get_client()
                clients_obtained.append(c)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=get_client) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(clients_obtained) == 10
        assert all(c is clients_obtained[0] for c in clients_obtained)

        client.close()

    def test_concurrent_request_counting(self):
        """Verifica que contagem de requisições é thread-safe."""
        client = OpenRouterClient()
        errors = []

        def increment_decrement():
            try:
                for _ in range(100):
                    client._begin_request()
                    time.sleep(0.001)
                    client._end_request()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=increment_decrement) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert client._active_requests == 0

    @patch("utils.api.time.sleep")
    def test_close_waits_for_active_requests(self, mock_sleep):
        """Verifica que close() espera requisições ativas."""
        client = OpenRouterClient()
        client._active_requests = 2
        close_completed = threading.Event()

        def simulate_request_completion():
            time.sleep(0.1)
            with client._requests_lock:
                client._active_requests = 0

        def close_client():
            mock_sleep.side_effect = lambda x: time.sleep(0.05)
            client.close()
            close_completed.set()

        request_thread = threading.Thread(target=simulate_request_completion)
        close_thread = threading.Thread(target=close_client)

        request_thread.start()
        close_thread.start()

        request_thread.join()
        close_thread.join()

        assert close_completed.is_set()
        assert client._client is None


class TestSanitizeErrorMessage:
    """Testes para sanitização de mensagens de erro."""

    def test_sanitize_empty_response(self):
        """Resposta vazia deve retornar mensagem padrão."""
        client = OpenRouterClient()
        result = client._sanitize_error_message("")
        assert result == "Sem detalhes disponíveis"

    def test_sanitize_none_response(self):
        """None deve retornar mensagem padrão."""
        client = OpenRouterClient()
        result = client._sanitize_error_message(None)
        assert result == "Sem detalhes disponíveis"

    def test_sanitize_truncates_long_message(self):
        """Mensagens longas devem ser truncadas."""
        client = OpenRouterClient()
        long_message = "x" * 200
        result = client._sanitize_error_message(long_message)
        assert len(result) <= 103
        assert result.endswith("...")

    def test_sanitize_redacts_api_key(self):
        """API keys devem ser redactadas."""
        client = OpenRouterClient()
        message = 'Error: api_key=sk-1234567890abcdef'
        result = client._sanitize_error_message(message)
        assert "sk-1234567890abcdef" not in result
        assert "REDACTED" in result

    def test_sanitize_redacts_token(self):
        """Tokens devem ser redactados."""
        client = OpenRouterClient()
        message = 'Invalid token: abc123xyz'
        result = client._sanitize_error_message(message)
        assert "abc123xyz" not in result
        assert "REDACTED" in result

    def test_sanitize_redacts_bearer(self):
        """Bearer tokens devem ser redactados."""
        client = OpenRouterClient()
        message = 'Authorization: Bearer sk-secret123'
        result = client._sanitize_error_message(message)
        assert "sk-secret123" not in result
        assert "REDACTED" in result

    def test_sanitize_redacts_password(self):
        """Passwords devem ser redactados."""
        client = OpenRouterClient()
        message = 'password=mysecretpassword'
        result = client._sanitize_error_message(message)
        assert "mysecretpassword" not in result
        assert "REDACTED" in result

    def test_sanitize_case_insensitive(self):
        """Redação deve ser case-insensitive."""
        client = OpenRouterClient()
        message = 'API_KEY=secret123 Token=abc'
        result = client._sanitize_error_message(message)
        assert "secret123" not in result
        assert "abc" not in result


class TestRateLimitErrorRepr:
    """Testes para __repr__ do RateLimitError."""

    def test_repr_with_retry_after(self):
        """Verifica repr com retry_after."""
        error = RateLimitError("Rate limit exceeded", retry_after=30.0)
        result = repr(error)
        assert "RateLimitError" in result
        assert "Rate limit exceeded" in result
        assert "retry_after=30.0" in result

    def test_repr_without_retry_after(self):
        """Verifica repr sem retry_after."""
        error = RateLimitError("Rate limit exceeded")
        result = repr(error)
        assert "RateLimitError" in result
        assert "retry_after=None" in result


class TestStreamingNetworkErrors:
    """Testes para erros de rede durante streaming."""

    @patch("utils.api.httpx.Client")
    def test_send_message_stream_network_error_mid_stream(self, mock_client_class):
        """Verifica que erro de rede durante streaming é tratado corretamente."""
        def failing_iterator():
            yield 'data: {"choices": [{"delta": {"content": "Ola"}}]}'
            yield 'data: {"choices": [{"delta": {"content": " mundo"}}]}'
            raise httpx.ReadError("Connection lost")

        mock_stream_response = MagicMock()
        mock_stream_response.status_code = 200
        mock_stream_response.iter_lines.return_value = failing_iterator()
        mock_stream_response.__enter__ = MagicMock(return_value=mock_stream_response)
        mock_stream_response.__exit__ = MagicMock(return_value=False)

        mock_client = MagicMock()
        mock_client.stream.return_value = mock_stream_response
        mock_client_class.return_value = mock_client

        client = OpenRouterClient()
        client._api_key = "test_key"

        response = client.send_message_stream([{"role": "user", "content": "test"}])

        chunks = []
        with pytest.raises(httpx.ReadError):
            for chunk in response:
                chunks.append(chunk)

        assert len(chunks) == 2
        assert chunks[0] == "Ola"
        assert chunks[1] == " mundo"
        assert client._active_requests == 0

    @patch("utils.api.httpx.Client")
    def test_send_message_stream_connection_reset_mid_stream(self, mock_client_class):
        """Verifica que erro de conexão durante streaming é tratado corretamente."""
        def connection_error_iterator():
            yield 'data: {"choices": [{"delta": {"content": "Start"}}]}'
            raise httpx.RemoteProtocolError("Connection reset")

        mock_stream_response = MagicMock()
        mock_stream_response.status_code = 200
        mock_stream_response.iter_lines.return_value = connection_error_iterator()
        mock_stream_response.__enter__ = MagicMock(return_value=mock_stream_response)
        mock_stream_response.__exit__ = MagicMock(return_value=False)

        mock_client = MagicMock()
        mock_client.stream.return_value = mock_stream_response
        mock_client_class.return_value = mock_client

        client = OpenRouterClient()
        client._api_key = "test_key"

        response = client.send_message_stream([{"role": "user", "content": "test"}])

        chunks = []
        with pytest.raises(httpx.RemoteProtocolError):
            for chunk in response:
                chunks.append(chunk)

        assert len(chunks) == 1
        assert client._active_requests == 0


class TestLogSanitization:
    """Testes para a função de sanitização de logs."""

    def test_sanitize_removes_control_characters(self):
        """Verifica remoção de caracteres de controle."""
        from utils.api import _sanitize_for_logging

        text_with_controls = "Hello\x00World\x1fTest\x7f"
        result = _sanitize_for_logging(text_with_controls)

        assert result == "HelloWorldTest"

    def test_sanitize_removes_ansi_escape_codes(self):
        """Verifica remoção de códigos ANSI de escape."""
        from utils.api import _sanitize_for_logging

        text_with_ansi = "Hello\x1b[31mRed\x1b[0m"
        result = _sanitize_for_logging(text_with_ansi)

        assert "\x1b" not in result
        assert "Hello" in result
        assert "Red" in result

    def test_sanitize_preserves_normal_text(self):
        """Verifica que texto normal é preservado."""
        from utils.api import _sanitize_for_logging

        normal_text = "Hello World! 123 áéíóú çÇ"
        result = _sanitize_for_logging(normal_text)

        assert result == normal_text

    def test_sanitize_empty_string(self):
        """Verifica que string vazia retorna vazia."""
        from utils.api import _sanitize_for_logging

        result = _sanitize_for_logging("")

        assert result == ""

    def test_sanitize_only_control_chars(self):
        """Verifica que string só com controles retorna vazia."""
        from utils.api import _sanitize_for_logging

        result = _sanitize_for_logging("\x00\x01\x02\x1f")

        assert result == ""
