"""Módulos utilitários para o chatbot."""

from .config import config, Config, ConfigurationError
from .api import OpenRouterClient, APIError
from .conversation import ConversationManager
from .display import Display
