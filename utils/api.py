"""Cliente para a API OpenRouter."""

import httpx
from .config import config


class APIError(Exception):
    """Erro de comunicação com a API."""

    pass


class OpenRouterClient:
    """Cliente para comunicação com a API OpenRouter."""

    def __init__(self):
        self.base_url = config.OPENROUTER_BASE_URL
        self.api_key = config.OPENROUTER_API_KEY
        self.model = config.OPENROUTER_MODEL

    def _get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

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

        payload = {
            "model": self.model,
            "messages": messages,
        }

        try:
            with httpx.Client(timeout=60.0) as client:
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
                    raise APIError(f"Erro na API: {response.status_code} - {response.text}")

                data = response.json()
                return data["choices"][0]["message"]["content"]

        except httpx.TimeoutException:
            raise APIError("Tempo limite excedido. Verifique sua conexão.")
        except httpx.ConnectError:
            raise APIError("Não foi possível conectar à API. Verifique sua conexão.")
        except (KeyError, IndexError) as e:
            raise APIError(f"Resposta inesperada da API: {e}")

    def set_model(self, model: str) -> None:
        """Altera o modelo utilizado."""
        self.model = model

    def get_model(self) -> str:
        """Retorna o modelo atual."""
        return self.model
