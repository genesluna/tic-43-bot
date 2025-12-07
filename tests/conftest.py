"""Fixtures compartilhados para os testes do chatbot."""

import pytest
from unittest.mock import MagicMock, patch

from tests.helpers import create_mock_stream, MockStreamingResponse


# =============================================================================
# Mock Config Fixtures
# =============================================================================

@pytest.fixture
def mock_config_attrs():
    """Atributos padrão para mock de configuração."""
    return {
        "SYSTEM_PROMPT": "Você é um assistente de teste.",
        "RESPONSE_LANGUAGE": "português",
        "RESPONSE_LENGTH": "conciso",
        "RESPONSE_TONE": "amigável",
        "RESPONSE_FORMAT": "markdown",
        "MAX_MESSAGE_LENGTH": 10000,
        "MAX_HISTORY_SIZE": 25,
        "HISTORY_DIR": "./history",
        "OPENROUTER_MODEL": "openai/gpt-4o-mini",
        "EXIT_COMMANDS": ("sair", "exit", "quit"),
        "CLEAR_COMMANDS": ("/limpar", "/clear"),
        "SAVE_COMMANDS": ("/salvar", "/save"),
        "HELP_COMMANDS": ("/ajuda", "/help"),
        "MODEL_COMMANDS": ("/modelo",),
        "LIST_COMMANDS": ("/listar", "/list"),
        "LOAD_COMMANDS": ("/carregar", "/load"),
    }


@pytest.fixture
def mock_config_conversation(tmp_path, mock_config_attrs):
    """Mock de config para testes de conversação com diretório temporário."""
    with patch("utils.conversation.config") as mock_config:
        for attr, value in mock_config_attrs.items():
            setattr(mock_config, attr, value)
        mock_config.HISTORY_DIR = str(tmp_path)
        yield mock_config


@pytest.fixture
def mock_config_chatbot(mock_config_attrs):
    """Mock de config para testes do chatbot."""
    with patch("chatbot.config") as mock_config:
        for attr, value in mock_config_attrs.items():
            setattr(mock_config, attr, value)
        yield mock_config


# =============================================================================
# Mock HTTP Client Fixtures
# =============================================================================

@pytest.fixture
def mock_http_client():
    """Mock de httpx.Client com suporte a context manager."""
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    return mock_client


@pytest.fixture
def mock_http_response_success():
    """Mock de resposta HTTP bem-sucedida."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Olá! Como posso ajudar?"}}]
    }
    return mock_response


@pytest.fixture
def mock_stream_response_success():
    """Mock de resposta de streaming bem-sucedida."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.iter_lines.return_value = [
        'data: {"choices": [{"delta": {"content": "Olá"}}]}',
        'data: {"choices": [{"delta": {"content": "!"}}]}',
        'data: {"choices": [{"delta": {"content": " Tudo bem?"}}]}',
        'data: [DONE]',
    ]
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)
    return mock_response


# =============================================================================
# Mock Display/Client Fixtures
# =============================================================================

@pytest.fixture
def mock_display():
    """Mock de Display com prompt_input configurável."""
    mock = MagicMock()
    mock.prompt_input.return_value = "sair"
    return mock


@pytest.fixture
def mock_api_client():
    """Mock de OpenRouterClient com context manager."""
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.send_message_stream.return_value = create_mock_stream(["Resposta", " de", " teste"])
    return mock_client


@pytest.fixture
def mock_conversation():
    """Mock de ConversationManager."""
    mock = MagicMock()
    mock.get_messages.return_value = [
        {"role": "system", "content": "Você é um assistente."},
    ]
    mock.message_count.return_value = 0
    return mock


# =============================================================================
# Test Data Fixtures
# =============================================================================

@pytest.fixture
def sample_messages():
    """Mensagens de exemplo para testes."""
    return [
        {"role": "system", "content": "Você é um assistente."},
        {"role": "user", "content": "Olá"},
        {"role": "assistant", "content": "Oi! Como posso ajudar?"},
    ]


@pytest.fixture
def sample_history_data():
    """Dados de histórico de exemplo para testes."""
    return {
        "timestamp": "2024-01-01T12:00:00",
        "model": "openai/gpt-4o-mini",
        "messages": [
            {"role": "user", "content": "Olá"},
            {"role": "assistant", "content": "Oi!"},
        ]
    }
