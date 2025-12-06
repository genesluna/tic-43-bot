"""Cliente para a API OpenRouter."""

import json
import logging
import random
import threading
import time
import httpx
from typing import Generator
from .config import config

logger = logging.getLogger(__name__)

DEFAULT_CONNECT_TIMEOUT = 10.0
DEFAULT_READ_TIMEOUT = 90.0
DEFAULT_WRITE_TIMEOUT = 10.0
DEFAULT_POOL_TIMEOUT = 10.0

# Rate limiting configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_INITIAL_BACKOFF = 1.0  # seconds
DEFAULT_MAX_BACKOFF = 30.0  # seconds
DEFAULT_BACKOFF_MULTIPLIER = 2.0


class APIError(Exception):
    """Erro de comunicação com a API."""


class RateLimitError(APIError):
    """Erro de rate limiting da API."""

    def __init__(self, message: str, retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class OpenRouterClient:
    """Cliente para comunicação com a API OpenRouter."""

    def __init__(self):
        self.base_url = config.OPENROUTER_BASE_URL
        self._api_key = config.OPENROUTER_API_KEY
        self.model = config.OPENROUTER_MODEL
        self._client: httpx.Client | None = None
        self._client_lock = threading.Lock()

    def __repr__(self) -> str:
        return f"OpenRouterClient(model={self.model})"

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _get_client(self) -> httpx.Client:
        """Retorna cliente HTTP reutilizável (thread-safe)."""
        with self._client_lock:
            if self._client is None:
                timeout = httpx.Timeout(
                    connect=DEFAULT_CONNECT_TIMEOUT,
                    read=DEFAULT_READ_TIMEOUT,
                    write=DEFAULT_WRITE_TIMEOUT,
                    pool=DEFAULT_POOL_TIMEOUT,
                )
                self._client = httpx.Client(timeout=timeout)
            return self._client

    def _get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _sanitize_error_message(self, response_text: str, max_length: int = 100) -> str:
        """Sanitiza mensagem de erro para não expor informações sensíveis."""
        if not response_text:
            return "Sem detalhes disponíveis"
        sanitized = response_text[:max_length]
        if len(response_text) > max_length:
            sanitized += "..."
        return sanitized

    def _get_retry_after(self, response: httpx.Response) -> float | None:
        """Extrai tempo de espera do header Retry-After, se disponível."""
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return float(retry_after)
            except ValueError:
                pass
        return None

    def _calculate_backoff(self, attempt: int, retry_after: float | None = None) -> float:
        """Calcula tempo de espera com exponential backoff e jitter."""
        if retry_after is not None:
            return min(retry_after, DEFAULT_MAX_BACKOFF)
        backoff = DEFAULT_INITIAL_BACKOFF * (DEFAULT_BACKOFF_MULTIPLIER ** attempt)
        jitter = 0.5 + random.random()
        return min(backoff * jitter, DEFAULT_MAX_BACKOFF)

    def _handle_transient_error(
        self, error_type: str, message: str, attempt: int
    ) -> tuple[APIError, bool]:
        """Trata erros transientes com retry e backoff."""
        error = APIError(message)
        should_retry = attempt < DEFAULT_MAX_RETRIES - 1
        if should_retry:
            backoff = self._calculate_backoff(attempt)
            logger.warning(
                f"{error_type}. Tentativa {attempt + 1}/{DEFAULT_MAX_RETRIES}. "
                f"Aguardando {backoff:.1f}s..."
            )
            time.sleep(backoff)
        return error, should_retry

    def _handle_rate_limit(
        self, response: httpx.Response, attempt: int
    ) -> tuple[float | None, bool]:
        """Trata rate limiting com retry e backoff."""
        retry_after = self._get_retry_after(response)
        backoff = self._calculate_backoff(attempt, retry_after)
        logger.warning(
            f"Rate limit atingido. Tentativa {attempt + 1}/{DEFAULT_MAX_RETRIES}. "
            f"Aguardando {backoff:.1f}s..."
        )
        should_retry = attempt < DEFAULT_MAX_RETRIES - 1
        if should_retry:
            time.sleep(backoff)
        return retry_after, should_retry

    def send_message(self, messages: list[dict]) -> str:
        """
        Envia mensagens para a API e retorna a resposta.

        Args:
            messages: Lista de mensagens no formato OpenAI.

        Returns:
            Texto da resposta do modelo.

        Raises:
            APIError: Em caso de erro na comunicação.
            RateLimitError: Quando o limite de requisições é excedido após retentativas.
        """
        if not self._api_key:
            raise APIError(
                "Chave de API não configurada. Configure OPENROUTER_API_KEY no arquivo .env."
            )

        if not messages:
            raise APIError("Lista de mensagens não pode estar vazia.")

        payload = {
            "model": self.model,
            "messages": messages,
        }

        last_error: Exception | None = None

        for attempt in range(DEFAULT_MAX_RETRIES):
            try:
                client = self._get_client()
                response = client.post(
                    self.base_url,
                    headers=self._get_headers(),
                    json=payload,
                )

                if response.status_code == 401:
                    raise APIError("Chave de API inválida. Verifique sua configuração.")

                if response.status_code == 429:
                    retry_after, should_retry = self._handle_rate_limit(response, attempt)
                    if should_retry:
                        continue
                    raise RateLimitError(
                        "Limite de requisições excedido após várias tentativas.",
                        retry_after=retry_after,
                    )

                if response.status_code >= 400:
                    error_detail = self._sanitize_error_message(response.text)
                    raise APIError(f"Erro na API ({response.status_code}): {error_detail}")

                data = response.json()

                if "choices" not in data or not data["choices"]:
                    raise APIError("Resposta da API não contém dados válidos.")

                content = data["choices"][0].get("message", {}).get("content")
                if content is None:
                    raise APIError("Resposta da API não contém conteúdo.")

                return content

            except httpx.TimeoutException:
                last_error, should_retry = self._handle_transient_error(
                    "Timeout", "Tempo limite excedido. Verifique sua conexão.", attempt
                )
                if should_retry:
                    continue
            except httpx.ConnectError:
                last_error, should_retry = self._handle_transient_error(
                    "Erro de conexão", "Não foi possível conectar à API. Verifique sua conexão.", attempt
                )
                if should_retry:
                    continue

        if last_error:
            raise last_error
        raise APIError("Erro desconhecido na comunicação com a API.")

    def send_message_stream(self, messages: list[dict]) -> Generator[str, None, None]:
        """
        Envia mensagens para a API e retorna a resposta em streaming.

        Args:
            messages: Lista de mensagens no formato OpenAI.

        Yields:
            Chunks de texto conforme chegam da API.

        Raises:
            APIError: Em caso de erro na comunicação.
            RateLimitError: Quando o limite de requisições é excedido após retentativas.
        """
        if not self._api_key:
            raise APIError(
                "Chave de API não configurada. Configure OPENROUTER_API_KEY no arquivo .env."
            )

        if not messages:
            raise APIError("Lista de mensagens não pode estar vazia.")

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
        }

        last_error: Exception | None = None

        for attempt in range(DEFAULT_MAX_RETRIES):
            try:
                client = self._get_client()
                with client.stream(
                    "POST",
                    self.base_url,
                    headers=self._get_headers(),
                    json=payload,
                ) as response:
                    if response.status_code == 401:
                        raise APIError("Chave de API inválida. Verifique sua configuração.")

                    if response.status_code == 429:
                        retry_after, should_retry = self._handle_rate_limit(response, attempt)
                        if should_retry:
                            continue
                        raise RateLimitError(
                            "Limite de requisições excedido após várias tentativas.",
                            retry_after=retry_after,
                        )

                    if response.status_code >= 400:
                        response.read()
                        error_detail = self._sanitize_error_message(response.text)
                        raise APIError(f"Erro na API ({response.status_code}): {error_detail}")

                    for line in response.iter_lines():
                        if not line or not line.startswith("data: "):
                            continue

                        data_str = line[6:]

                        if data_str == "[DONE]":
                            break

                        try:
                            data = json.loads(data_str)
                            if "choices" in data and data["choices"]:
                                delta = data["choices"][0].get("delta", {})
                                content = delta.get("content")
                                if content:
                                    yield content
                        except json.JSONDecodeError as e:
                            logger.warning(f"Falha ao parsear SSE: {e} - dados: {data_str[:100]}")
                            continue

                    return

            except httpx.TimeoutException:
                last_error, should_retry = self._handle_transient_error(
                    "Timeout", "Tempo limite excedido. Verifique sua conexão.", attempt
                )
                if should_retry:
                    continue
            except httpx.ConnectError:
                last_error, should_retry = self._handle_transient_error(
                    "Erro de conexão", "Não foi possível conectar à API. Verifique sua conexão.", attempt
                )
                if should_retry:
                    continue

        if last_error:
            raise last_error
        raise APIError("Erro desconhecido na comunicação com a API.")

    def set_model(self, model: str) -> None:
        """
        Altera o modelo utilizado.

        Args:
            model: Nome do modelo no formato 'provider/model-name'.

        Raises:
            ValueError: Se o modelo for inválido.
        """
        if not model or not isinstance(model, str):
            raise ValueError("Modelo deve ser uma string não vazia.")
        model = model.strip()
        if not model:
            raise ValueError("Modelo deve ser uma string não vazia.")
        if "/" not in model:
            raise ValueError("Modelo deve estar no formato 'provider/model-name'.")
        self.model = model

    def get_model(self) -> str:
        """Retorna o modelo atual."""
        return self.model

    def close(self) -> None:
        """Fecha o cliente HTTP (thread-safe)."""
        with self._client_lock:
            if self._client:
                self._client.close()
                self._client = None
