"""Cliente para a API OpenRouter."""

import json
import logging
import random
import re
import ssl
import threading
import time
import uuid
from dataclasses import dataclass
import httpx
from typing import Any, Generator, Self
from .config import config, MAX_MESSAGE_CONTENT_SIZE
from .version import __version__

__all__ = ["OpenRouterClient", "APIError", "RateLimitError", "StreamingResponse", "APIResponse"]

USER_AGENT = f"TIC43-Chatbot/{__version__}"


@dataclass
class APIResponse:
    """Resposta da API com conteúdo e metadados."""

    content: str
    total_tokens: int = 0

    def __repr__(self) -> str:
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"APIResponse(content={preview!r}, tokens={self.total_tokens})"

logger = logging.getLogger(__name__)

# Retry configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_INITIAL_BACKOFF = 1.0
DEFAULT_MAX_BACKOFF = 30.0
DEFAULT_BACKOFF_MULTIPLIER = 2.0
JITTER_MIN = 0.5

# Close timeout configuration
CLOSE_WAIT_ITERATIONS = 50
CLOSE_WAIT_INTERVAL = 0.1
CLOSE_TOTAL_TIMEOUT = CLOSE_WAIT_ITERATIONS * CLOSE_WAIT_INTERVAL

# API key masking
MIN_MASK_KEY_LENGTH = 8
MASK_PREFIX_LENGTH = 4
MASK_SUFFIX_LENGTH = 4

# Error and SSE message limits
ERROR_MESSAGE_MAX_LENGTH = 100
SSE_DATA_PREFIX_LENGTH = 6
SSE_LOG_MAX_LENGTH = 100

# Valid message roles
VALID_MESSAGE_ROLES = frozenset({"system", "user", "assistant"})

# Pattern to match control characters for log sanitization
_CONTROL_CHARS_PATTERN = re.compile(r'[\x00-\x1f\x7f-\x9f]')


def _sanitize_for_logging(text: str) -> str:
    """Remove caracteres de controle que podem manipular logs."""
    return _CONTROL_CHARS_PATTERN.sub('', text)


def _generate_request_id() -> str:
    """Gera ID único para correlação de requisições nos logs."""
    return uuid.uuid4().hex[:8]


class APIError(Exception):
    """Erro de comunicação com a API."""


class StreamingResponse:
    """Wrapper para garantir cleanup do contador de requisições em streaming.

    Esta classe encapsula o generator de streaming e garante que o contador
    de requisições ativas seja decrementado mesmo quando o generator é
    abandonado (não consumido completamente) ou uma exceção ocorre.

    Uso recomendado com context manager:
        with client.send_message_stream(messages) as stream:
            for chunk in stream:
                process(chunk)
    """

    def __init__(self, client: "OpenRouterClient", generator: Generator[str, None, None]) -> None:
        self._client = client
        self._generator = generator
        self._closed = False
        self._cleanup_lock = threading.Lock()
        self._cleanup_via_del = False

    def __repr__(self) -> str:
        return f"StreamingResponse(closed={self._closed})"

    def __enter__(self) -> "StreamingResponse":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def __iter__(self) -> "StreamingResponse":
        return self

    def __next__(self) -> str:
        if self._closed:
            raise StopIteration
        try:
            return next(self._generator)
        except StopIteration:
            self._cleanup()
            raise
        except Exception:
            self._cleanup()
            raise

    def _cleanup(self) -> None:
        """Decrementa contador de requisições (thread-safe e idempotente)."""
        with self._cleanup_lock:
            if not self._closed:
                self._closed = True
                self._client._end_request()
                if self._cleanup_via_del:
                    logger.warning(
                        "StreamingResponse cleanup via __del__ - "
                        "considere usar 'with' statement ou chamar close()"
                    )

    def __del__(self) -> None:
        self._cleanup_via_del = True
        self._cleanup()

    def close(self) -> None:
        """Fecha explicitamente a resposta de streaming."""
        self._cleanup()


class RateLimitError(APIError):
    """Erro de rate limiting da API."""

    def __init__(self, message: str, retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after

    def __repr__(self) -> str:
        return f"RateLimitError({self.args[0]!r}, retry_after={self.retry_after})"


class OpenRouterClient:
    """Cliente para comunicação com a API OpenRouter.

    Thread-safety: O cliente HTTP é compartilhado entre threads e protegido
    por lock. O método close() aguarda requisições ativas antes de fechar.
    """

    def __init__(self):
        self.base_url: str = config.OPENROUTER_BASE_URL
        self._api_key: str = config.OPENROUTER_API_KEY
        self.model: str = config.OPENROUTER_MODEL
        self._client: httpx.Client | None = None
        self._client_lock = threading.Lock()
        self._active_requests = 0
        self._requests_lock = threading.Lock()
        self._requests_condition = threading.Condition(self._requests_lock)
        logger.debug("Cliente inicializado com modelo: %s", self.model)

    def __repr__(self) -> str:
        return f"OpenRouterClient(model={self.model})"

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def _get_client(self) -> httpx.Client:
        """Retorna cliente HTTP reutilizável (thread-safe)."""
        with self._client_lock:
            if self._client is None:
                timeout = httpx.Timeout(
                    connect=config.HTTP_CONNECT_TIMEOUT,
                    read=config.HTTP_READ_TIMEOUT,
                    write=config.HTTP_WRITE_TIMEOUT,
                    pool=config.HTTP_POOL_TIMEOUT,
                )
                ssl_context = ssl.create_default_context()
                ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
                self._client = httpx.Client(timeout=timeout, verify=ssl_context)
            return self._client

    def _begin_request(self) -> None:
        """Registra início de requisição (thread-safe)."""
        with self._requests_lock:
            self._active_requests += 1

    def _end_request(self) -> None:
        """Registra fim de requisição (thread-safe, notifica waiters)."""
        with self._requests_condition:
            self._active_requests -= 1
            self._requests_condition.notify_all()

    def _get_masked_key(self) -> str:
        """Retorna chave de API mascarada para logging seguro."""
        if self._api_key and len(self._api_key) > MIN_MASK_KEY_LENGTH:
            return f"{self._api_key[:MASK_PREFIX_LENGTH]}...{self._api_key[-MASK_SUFFIX_LENGTH:]}"
        return "***"

    def _get_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        }

    def _sanitize_error_message(self, response_text: str, max_length: int = ERROR_MESSAGE_MAX_LENGTH) -> str:
        """Sanitiza mensagem de erro para não expor informações sensíveis."""
        if not response_text:
            return "Sem detalhes disponíveis"
        # Padrão abrangente para credenciais em vários formatos (JSON, headers, query strings)
        sanitized = re.sub(
            r'(["\']?(?:api[-_]?key|token|secret|password|auth|credential|key)["\']?\s*[:=]\s*)["\']?[^\s"\',$}\]]+["\']?',
            r'\1[REDACTED]',
            response_text,
            flags=re.IGNORECASE
        )
        sanitized = re.sub(
            r'(bearer|authorization)["\s:=]+\S+(\s+\S+)?',
            r'\1=[REDACTED]',
            sanitized,
            flags=re.IGNORECASE
        )
        sanitized = sanitized[:max_length]
        if len(response_text) > max_length:
            sanitized += "..."
        return sanitized

    def _get_retry_after(self, response: httpx.Response) -> float | None:
        """Extrai tempo de espera do header Retry-After, se disponível."""
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                value = float(retry_after)
                if value > 0:
                    return value
            except ValueError:
                pass
        return None

    def _calculate_backoff(self, attempt: int, retry_after: float | None = None) -> float:
        """Calcula tempo de espera com exponential backoff e jitter."""
        if retry_after is not None:
            if retry_after > DEFAULT_MAX_BACKOFF:
                logger.warning(
                    "Retry-After muito alto (%ds), limitando a %ds",
                    int(retry_after), int(DEFAULT_MAX_BACKOFF)
                )
            return min(retry_after, DEFAULT_MAX_BACKOFF)
        backoff = DEFAULT_INITIAL_BACKOFF * (DEFAULT_BACKOFF_MULTIPLIER ** attempt)
        # Jitter adds randomness to avoid thundering herd: value in [0.5, 1.5]
        jitter = JITTER_MIN + random.random()
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
                "%s. Tentativa %d/%d. Aguardando %.1fs...",
                error_type, attempt + 1, DEFAULT_MAX_RETRIES, backoff
            )
            time.sleep(backoff)
        return error, should_retry

    def _handle_rate_limit(
        self, response: httpx.Response, attempt: int
    ) -> tuple[float | None, bool]:
        """Trata rate limiting com retry e backoff."""
        retry_after = self._get_retry_after(response)
        should_retry = attempt < DEFAULT_MAX_RETRIES - 1
        if should_retry:
            backoff = self._calculate_backoff(attempt, retry_after)
            logger.warning(
                "Rate limit atingido. Tentativa %d/%d. Aguardando %.1fs...",
                attempt + 1, DEFAULT_MAX_RETRIES, backoff
            )
            time.sleep(backoff)
        return retry_after, should_retry

    def _validate_messages(self, messages: list[dict[str, str]]) -> None:
        """Valida estrutura das mensagens antes de enviar à API."""
        if not messages:
            raise APIError("Lista de mensagens não pode estar vazia.")

        for i, msg in enumerate(messages):
            if not isinstance(msg, dict):
                raise APIError(f"Mensagem {i} deve ser um dicionário.")
            if "role" not in msg:
                raise APIError(f"Mensagem {i} não contém campo 'role'.")
            if "content" not in msg:
                raise APIError(f"Mensagem {i} não contém campo 'content'.")
            if msg["role"] not in VALID_MESSAGE_ROLES:
                raise APIError(f"Mensagem {i} tem role inválido: {msg['role']}")
            if not isinstance(msg["content"], str):
                raise APIError(f"Mensagem {i} tem content não-string.")
            if len(msg["content"]) > MAX_MESSAGE_CONTENT_SIZE:
                raise APIError(
                    f"Mensagem {i} excede tamanho máximo ({MAX_MESSAGE_CONTENT_SIZE} chars)."
                )

    def _prepare_request(
        self, messages: list[dict[str, str]], stream: bool = False
    ) -> dict[str, Any]:
        """Prepara e valida requisição para a API."""
        if not self._api_key:
            raise APIError(
                "Chave de API não configurada. Configure OPENROUTER_API_KEY no arquivo .env."
            )
        self._validate_messages(messages)
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }
        if stream:
            payload["stream"] = True
        return payload

    def _handle_response_error(
        self, response: httpx.Response, attempt: int
    ) -> tuple[bool, Exception | None]:
        """
        Trata erros de resposta HTTP.

        Returns:
            Tupla (should_proceed, exception).
            should_proceed=True significa sucesso, proceder com parsing.
            should_proceed=False com exception=None significa retry.
            should_proceed=False com exception significa erro fatal.
        """
        if response.status_code == 401:
            return False, APIError("Chave de API inválida. Verifique sua configuração.")

        if response.status_code == 429:
            retry_after, should_retry = self._handle_rate_limit(response, attempt)
            if should_retry:
                return False, None
            return False, RateLimitError(
                "Limite de requisições excedido após várias tentativas.",
                retry_after=retry_after,
            )

        if response.status_code >= 400:
            error_detail = self._sanitize_error_message(response.text)
            return False, APIError(f"Erro na API ({response.status_code}): {error_detail}")

        return True, None

    def _handle_network_error(
        self, error: Exception, attempt: int
    ) -> tuple[bool, APIError]:
        """Trata erros de rede (timeout, conexão)."""
        if isinstance(error, httpx.TimeoutException):
            last_error, should_retry = self._handle_transient_error(
                "Timeout", "Tempo limite excedido. Verifique sua conexão.", attempt
            )
            return should_retry, last_error

        if isinstance(error, httpx.ConnectError):
            last_error, should_retry = self._handle_transient_error(
                "Erro de conexão",
                "Não foi possível conectar à API. Verifique sua conexão.",
                attempt,
            )
            return should_retry, last_error

        return False, APIError(f"Erro de rede: {error}")

    def send_message(self, messages: list[dict[str, str]]) -> APIResponse:
        """
        Envia mensagens para a API e retorna a resposta.

        Args:
            messages: Lista de mensagens no formato OpenAI.

        Returns:
            APIResponse com o texto e contagem de tokens.

        Raises:
            APIError: Em caso de erro na comunicação.
            RateLimitError: Quando o limite de requisições é excedido após retentativas.
        """
        request_id = _generate_request_id()
        payload = self._prepare_request(messages)
        last_error: Exception | None = None

        logger.debug("[%s] Enviando requisição com %d mensagens", request_id, len(messages))
        self._begin_request()
        try:
            for attempt in range(DEFAULT_MAX_RETRIES):
                try:
                    client = self._get_client()
                    response = client.post(
                        self.base_url,
                        headers=self._get_headers(),
                        json=payload,
                    )

                    should_proceed, error = self._handle_response_error(response, attempt)
                    if error:
                        logger.debug("[%s] Erro na resposta: %s", request_id, error)
                        raise error
                    if not should_proceed:
                        continue

                    data = response.json()

                    if "choices" not in data or not data["choices"]:
                        raise APIError("Resposta da API não contém dados válidos.")

                    content = data["choices"][0].get("message", {}).get("content")
                    if content is None:
                        raise APIError("Resposta da API não contém conteúdo.")

                    total_tokens = data.get("usage", {}).get("total_tokens", 0)

                    logger.debug("[%s] Resposta recebida (%d chars, %d tokens)", request_id, len(content), total_tokens)
                    return APIResponse(content=content, total_tokens=total_tokens)

                except (httpx.TimeoutException, httpx.ConnectError) as e:
                    logger.debug("[%s] Erro de rede: %s", request_id, type(e).__name__)
                    should_retry, last_error = self._handle_network_error(e, attempt)
                    if should_retry:
                        continue

            if last_error:
                raise last_error
            raise APIError("Erro desconhecido na comunicação com a API.")
        finally:
            self._end_request()

    def send_message_stream(
        self, messages: list[dict[str, str]]
    ) -> StreamingResponse:
        """
        Envia mensagens para a API e retorna a resposta em streaming.

        Args:
            messages: Lista de mensagens no formato OpenAI.

        Returns:
            StreamingResponse iterável que produz chunks de texto.

        Raises:
            APIError: Em caso de erro na comunicação.
            RateLimitError: Quando o limite de requisições é excedido após retentativas.
        """
        request_id = _generate_request_id()
        payload = self._prepare_request(messages, stream=True)
        logger.debug("[%s] Iniciando streaming com %d mensagens", request_id, len(messages))
        self._begin_request()

        def _stream_generator() -> Generator[str, None, None]:
            last_error: Exception | None = None
            parse_errors = 0

            for attempt in range(DEFAULT_MAX_RETRIES):
                try:
                    client = self._get_client()
                    with client.stream(
                        "POST",
                        self.base_url,
                        headers=self._get_headers(),
                        json=payload,
                    ) as response:
                        if response.status_code >= 400:
                            # Em streaming, o corpo não é lido automaticamente.
                            # Lê o corpo para obter mensagem de erro (exceto 401,
                            # onde já sabemos que é erro de autenticação).
                            if response.status_code != 401:
                                response.read()
                            should_proceed, error = self._handle_response_error(
                                response, attempt
                            )
                            if error:
                                raise error
                            if not should_proceed:
                                continue

                        for line in response.iter_lines():
                            if not line or not line.startswith("data: "):
                                continue

                            data_str = line[SSE_DATA_PREFIX_LENGTH:]

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
                                parse_errors += 1
                                logger.warning(
                                    "Falha ao parsear SSE: %s - dados: %s",
                                    e, _sanitize_for_logging(data_str[:SSE_LOG_MAX_LENGTH])
                                )
                                continue

                        # Log summary of parse errors if any occurred
                        if parse_errors > 0:
                            logger.warning(
                                "Streaming concluído com %d erro(s) de parsing",
                                parse_errors
                            )
                        return

                except (httpx.TimeoutException, httpx.ConnectError) as e:
                    should_retry, last_error = self._handle_network_error(e, attempt)
                    if should_retry:
                        continue

            if last_error:
                raise last_error
            raise APIError("Erro desconhecido na comunicação com a API.")

        return StreamingResponse(self, _stream_generator())

    def set_model(self, model: str) -> None:
        """
        Altera o modelo utilizado.

        Args:
            model: Nome do modelo no formato 'provider/model-name'.

        Raises:
            ValueError: Se o modelo for inválido.
        """
        if not model or not isinstance(model, str):
            raise ValueError(
                "Nome do modelo inválido. "
                "Use o formato 'provider/model-name' (ex: openai/gpt-4o-mini)."
            )
        model = model.strip()
        if not model:
            raise ValueError(
                "Nome do modelo não pode estar vazio. "
                "Use o formato 'provider/model-name' (ex: openai/gpt-4o-mini)."
            )
        if "/" not in model:
            raise ValueError(
                f"Formato de modelo inválido: '{model}'. "
                "Use o formato 'provider/model-name' (ex: openai/gpt-4o-mini, anthropic/claude-3-haiku)."
            )
        logger.info("Modelo alterado para: %s", model)
        self.model = model

    def get_model(self) -> str:
        """Retorna o modelo atual."""
        return self.model

    def close(self) -> None:
        """Fecha o cliente HTTP (thread-safe).

        Aguarda requisições ativas antes de fechar usando Condition variable
        para eficiência (evita busy-wait com polling).
        """
        with self._requests_condition:
            if self._active_requests > 0:
                logger.debug("Aguardando %d requisição(ões) ativa(s)", self._active_requests)

            completed = self._requests_condition.wait_for(
                lambda: self._active_requests == 0,
                timeout=CLOSE_TOTAL_TIMEOUT
            )

            if not completed:
                logger.warning(
                    "Fechando cliente com %d requisição(ões) ativa(s) após timeout de %.1fs",
                    self._active_requests, CLOSE_TOTAL_TIMEOUT
                )

        with self._client_lock:
            if self._client:
                self._client.close()
                self._client = None
