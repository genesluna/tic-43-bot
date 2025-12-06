"""Cliente para a API OpenRouter."""

import json
import httpx
import tiktoken
from functools import lru_cache
from typing import Generator
from .config import config


@lru_cache(maxsize=8)
def _get_encoding(model: str) -> tiktoken.Encoding:
    """Retorna encoding cacheado para o modelo."""
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str, model: str = "gpt-4") -> int:
    """
    Conta o número de tokens em um texto.

    Args:
        text: Texto para contar tokens.
        model: Modelo para usar o encoding apropriado.

    Returns:
        Número de tokens.
    """
    encoding = _get_encoding(model)
    return len(encoding.encode(text))


class APIError(Exception):
    """Erro de comunicação com a API."""

    pass


class OpenRouterClient:
    """Cliente para comunicação com a API OpenRouter."""

    def __init__(self):
        self.base_url = config.OPENROUTER_BASE_URL
        self.api_key = config.OPENROUTER_API_KEY
        self.model = config.OPENROUTER_MODEL
        self._client: httpx.Client | None = None

    def _get_client(self) -> httpx.Client:
        """Retorna cliente HTTP reutilizável."""
        if self._client is None:
            timeout = httpx.Timeout(
                connect=10.0,
                read=90.0,
                write=10.0,
                pool=10.0,
            )
            self._client = httpx.Client(timeout=timeout)
        return self._client

    def _get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
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

    def send_message(self, messages: list[dict]) -> str:
        """
        Envia mensagens para a API e retorna a resposta.

        Args:
            messages: Lista de mensagens no formato OpenAI.

        Returns:
            Texto da resposta do modelo.

        Raises:
            APIError: Em caso de erro na comunicação.
        """
        if not self.api_key:
            raise APIError(
                "Chave da API não configurada. Configure OPENROUTER_API_KEY no arquivo .env"
            )

        if not messages:
            raise APIError("Lista de mensagens não pode estar vazia.")

        payload = {
            "model": self.model,
            "messages": messages,
        }

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
                raise APIError("Limite de requisições excedido. Tente novamente mais tarde.")

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
            raise APIError("Tempo limite excedido. Verifique sua conexão.")
        except httpx.ConnectError:
            raise APIError("Não foi possível conectar à API. Verifique sua conexão.")

    def send_message_stream(self, messages: list[dict]) -> Generator[str, None, None]:
        """
        Envia mensagens para a API e retorna a resposta em streaming.

        Args:
            messages: Lista de mensagens no formato OpenAI.

        Yields:
            Chunks de texto conforme chegam da API.

        Raises:
            APIError: Em caso de erro na comunicação.
        """
        if not self.api_key:
            raise APIError(
                "Chave da API não configurada. Configure OPENROUTER_API_KEY no arquivo .env"
            )

        if not messages:
            raise APIError("Lista de mensagens não pode estar vazia.")

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
        }

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
                    raise APIError("Limite de requisições excedido. Tente novamente mais tarde.")

                if response.status_code >= 400:
                    response.read()
                    error_detail = self._sanitize_error_message(response.text)
                    raise APIError(f"Erro na API ({response.status_code}): {error_detail}")

                for line in response.iter_lines():
                    if not line or not line.startswith("data: "):
                        continue

                    data_str = line[6:]  # Remove "data: " prefix

                    if data_str == "[DONE]":
                        break

                    try:
                        data = json.loads(data_str)
                        if "choices" in data and data["choices"]:
                            delta = data["choices"][0].get("delta", {})
                            content = delta.get("content")
                            if content:
                                yield content
                    except json.JSONDecodeError:
                        continue

        except httpx.TimeoutException:
            raise APIError("Tempo limite excedido. Verifique sua conexão.")
        except httpx.ConnectError:
            raise APIError("Não foi possível conectar à API. Verifique sua conexão.")

    def set_model(self, model: str) -> None:
        """Altera o modelo utilizado."""
        self.model = model

    def get_model(self) -> str:
        """Retorna o modelo atual."""
        return self.model

    def close(self) -> None:
        """Fecha o cliente HTTP."""
        if self._client:
            self._client.close()
            self._client = None
