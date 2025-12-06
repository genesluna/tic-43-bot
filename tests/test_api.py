"""Testes para o módulo de API."""

import pytest
from unittest.mock import patch, MagicMock
import httpx
from utils.api import OpenRouterClient, APIError, RateLimitError


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

    def test_set_model_empty_string(self):
        """Verifica se string vazia levanta ValueError."""
        client = OpenRouterClient()

        with pytest.raises(ValueError) as exc_info:
            client.set_model("")

        assert "string não vazia" in str(exc_info.value)

    def test_set_model_whitespace_only(self):
        """Verifica se string com apenas espaços levanta ValueError."""
        client = OpenRouterClient()

        with pytest.raises(ValueError) as exc_info:
            client.set_model("   ")

        assert "string não vazia" in str(exc_info.value)

    def test_set_model_no_slash(self):
        """Verifica se modelo sem barra levanta ValueError."""
        client = OpenRouterClient()

        with pytest.raises(ValueError) as exc_info:
            client.set_model("gpt-4o-mini")

        assert "provider/model-name" in str(exc_info.value)

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
            "choices": [{"message": {"content": "Olá! Como posso ajudar?"}}]
        }

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = OpenRouterClient()
        client._api_key = "test_key"

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
            "choices": [{"message": {"content": "Resposta de sucesso"}}]
        }

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = [mock_rate_limit_response, mock_success_response]
        mock_client_class.return_value = mock_client

        client = OpenRouterClient()
        client._api_key = "test_key"

        result = client.send_message([{"role": "user", "content": "Olá"}])

        assert result == "Resposta de sucesso"
        assert mock_sleep.call_count == 1
        assert mock_client.post.call_count == 2

    @patch("utils.api.time.sleep")
    @patch("utils.api.httpx.Client")
    def test_send_message_retry_success_after_timeout(self, mock_client_class, mock_sleep):
        """Deve retornar resposta após retry bem-sucedido de timeout."""
        mock_success_response = MagicMock()
        mock_success_response.status_code = 200
        mock_success_response.json.return_value = {
            "choices": [{"message": {"content": "Resposta após timeout"}}]
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

        assert result == "Resposta após timeout"
        assert mock_sleep.call_count == 1
        assert mock_client.post.call_count == 2

    @patch("utils.api.time.sleep")
    @patch("utils.api.httpx.Client")
    def test_send_message_retry_success_after_connection_error(self, mock_client_class, mock_sleep):
        """Deve retornar resposta após retry bem-sucedido de erro de conexão."""
        mock_success_response = MagicMock()
        mock_success_response.status_code = 200
        mock_success_response.json.return_value = {
            "choices": [{"message": {"content": "Resposta após erro de conexão"}}]
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

        assert result == "Resposta após erro de conexão"
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
