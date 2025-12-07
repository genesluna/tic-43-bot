# Utils - Módulos Utilitários do Chatbot

Este diretório contém os módulos centrais do chatbot, organizados por responsabilidade. Cada módulo é independente, thread-safe e extensivamente testado.

## Visão Geral

```
utils/
├── __init__.py          # Exports públicos do pacote
├── api.py               # Cliente HTTP para OpenRouter API
├── config.py            # Configurações do ambiente
├── conversation.py      # Gerenciamento de histórico
├── display.py           # Interface de terminal (Rich)
├── logging_config.py    # Sistema de logging estruturado
└── version.py           # Versão centralizada
```

## Módulos

### `api.py` - Cliente OpenRouter

Cliente HTTP thread-safe para comunicação com a API OpenRouter.

#### Classes

| Classe | Descrição |
|--------|-----------|
| `OpenRouterClient` | Cliente principal com retry, streaming e TLS 1.2+ |
| `StreamingResponse` | Wrapper para streaming com cleanup garantido |
| `APIResponse` | Dataclass com conteúdo e contagem de tokens |
| `APIError` | Exceção base para erros de API |
| `RateLimitError` | Exceção específica para rate limiting |

#### Recursos de Segurança

- **TLS 1.2+**: Conexões usam `ssl.TLSVersion.TLSv1_2` como mínimo
- **Mascaramento de credenciais**: `_get_masked_key()` para logs seguros
- **Sanitização de erros**: `_sanitize_error_message()` remove credenciais de respostas
- **Sanitização de logs**: `_sanitize_for_logging()` remove caracteres de controle
- **Validação de mensagens**: Verifica estrutura, roles e tamanho

#### Thread-Safety

- `_client_lock`: Protege acesso ao cliente HTTP compartilhado
- `_requests_condition`: Coordena shutdown gracioso aguardando requisições ativas
- `StreamingResponse._cleanup_lock`: Garante cleanup idempotente

#### Uso

```python
from utils import OpenRouterClient

# Uso com context manager (recomendado)
with OpenRouterClient() as client:
    # Requisição simples
    response = client.send_message([
        {"role": "user", "content": "Olá!"}
    ])
    print(response.content)

    # Streaming
    with client.send_message_stream(messages) as stream:
        for chunk in stream:
            print(chunk, end="")
```

#### Configuração de Retry

| Constante | Valor | Descrição |
|-----------|-------|-----------|
| `DEFAULT_MAX_RETRIES` | 3 | Tentativas máximas |
| `DEFAULT_INITIAL_BACKOFF` | 1.0s | Backoff inicial |
| `DEFAULT_MAX_BACKOFF` | 30.0s | Backoff máximo |
| `DEFAULT_BACKOFF_MULTIPLIER` | 2.0 | Multiplicador exponencial |

---

### `config.py` - Configurações

Gerenciamento de configurações com avaliação lazy e thread-safe via variáveis de ambiente.

#### Classes

| Classe | Descrição |
|--------|-----------|
| `Config` | Singleton de configuração com cached properties |
| `ConfigurationError` | Exceção para erros de configuração |
| `_ThreadSafeCachedProperty` | Descriptor para cache thread-safe |

#### Variáveis de Ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `OPENROUTER_API_KEY` | (obrigatório) | Chave de API do OpenRouter |
| `OPENROUTER_MODEL` | `openai/gpt-4o-mini` | Modelo padrão |
| `SYSTEM_PROMPT` | "Você é um assistente..." | Prompt do sistema |
| `RESPONSE_LANGUAGE` | `português` | Idioma das respostas |
| `RESPONSE_LENGTH` | `conciso` | Tamanho das respostas |
| `RESPONSE_TONE` | `amigável` | Tom das respostas |
| `RESPONSE_FORMAT` | `markdown` | Formato de saída |
| `MAX_MESSAGE_LENGTH` | 10000 | Limite de entrada do usuário |
| `MAX_HISTORY_SIZE` | 25 | Pares de mensagens mantidos |
| `HISTORY_DIR` | `./history` | Diretório de históricos |
| `STREAM_RESPONSE` | `true` | Habilita streaming |
| `LOG_LEVEL` | `WARNING` | Nível de log |
| `LOG_FORMAT` | `console` | Formato (`console`/`json`) |
| `LOG_FILE` | (vazio) | Arquivo de log |
| `HTTP_CONNECT_TIMEOUT` | 10.0s | Timeout de conexão |
| `HTTP_READ_TIMEOUT` | 90.0s | Timeout de leitura |
| `HTTP_WRITE_TIMEOUT` | 10.0s | Timeout de escrita |
| `HTTP_POOL_TIMEOUT` | 10.0s | Timeout do pool |

#### Limites de Segurança

| Constante | Valor | Descrição |
|-----------|-------|-----------|
| `MAX_MESSAGE_CONTENT_SIZE` | 100,000 | Tamanho máximo por mensagem |
| `MAX_MESSAGE_LENGTH_UPPER` | 100,000 | Limite superior para config |
| `MAX_HISTORY_SIZE_UPPER` | 500 | Máximo de pares de histórico |

#### Uso

```python
from utils import config, ConfigurationError

# Acesso a configurações (avaliação lazy)
api_key = config.OPENROUTER_API_KEY
model = config.OPENROUTER_MODEL

# Validação antecipada
try:
    config.validate()
except ConfigurationError as e:
    print(f"Erro de configuração: {e}")
```

---

### `conversation.py` - Histórico de Conversas

Gerenciamento do histórico de mensagens com persistência em JSON.

#### Classes

| Classe | Descrição |
|--------|-----------|
| `ConversationManager` | Gerencia histórico e persistência |
| `ConversationLoadError` | Exceção para erros de carregamento |
| `Message` | TypedDict para estrutura de mensagem |

#### Recursos de Segurança

- **Path traversal prevention**: `os.path.basename()` + regex sanitization
- **Rejeição de symlinks**: Verificação com `path.is_symlink()`
- **Escrita atômica**: `tempfile.mkstemp()` + `fsync()` + `shutil.move()`
- **Limite de tamanho**: `MAX_HISTORY_FILE_SIZE` = 10MB
- **Validação de HISTORY_DIR**: Restringe escrita ao diretório do projeto

#### Uso

```python
from utils import ConversationManager, ConversationLoadError

manager = ConversationManager()

# Adicionar mensagens
manager.add_user_message("Olá!")
manager.add_assistant_message("Olá! Como posso ajudar?")

# Obter mensagens para API
messages = manager.get_messages()

# Persistência
filepath = manager.save_to_file("minha_conversa")
print(f"Salvo em: {filepath}")

# Listar arquivos
files = manager.list_history_files()
for name, timestamp, model in files:
    print(f"{name}: {timestamp}")

# Carregar histórico
try:
    count = manager.load_from_file("minha_conversa.json")
    print(f"{count} mensagens carregadas")
except ConversationLoadError as e:
    print(f"Erro: {e}")

# Limpar histórico
manager.clear()
```

---

### `display.py` - Interface de Terminal

Componentes de UI para terminal usando a biblioteca Rich.

#### Classes

| Classe | Descrição |
|--------|-----------|
| `Display` | Facade principal para toda a UI |
| `RotatingSpinner` | Spinner animado com palavras rotativas |
| `StreamingTextDisplay` | Exibição em tempo real com Markdown |
| `ChatCompleter` | Autocompleção para comandos e arquivos |

#### Thread-Safety

- `RotatingSpinner`:
  - `_state_lock`: Protege transições start/stop
  - `_lock`: Protege estado interno (índices, contadores)
  - `_stop_event`: Coordena encerramento da thread de animação

- `StreamingTextDisplay`:
  - `_state_lock`: Protege transições start/stop
  - `_lock`: Protege acesso ao buffer de texto

#### Constantes

| Constante | Valor | Descrição |
|-----------|-------|-----------|
| `SPINNER_REFRESH_RATE` | 12 Hz | Taxa de atualização do spinner |
| `STREAMING_REFRESH_RATE` | 10 Hz | Taxa de atualização do streaming |
| `WORD_CHANGE_INTERVAL` | 5.0s | Rotação de palavras do spinner |
| `MAX_BUFFER_SIZE` | 1MB | Limite do buffer de streaming |

#### Uso

```python
from utils import Display

display = Display()

# Banner e ajuda
display.show_banner()
display.show_help()

# Mensagens
display.show_bot_message("Resposta em **markdown**")
display.show_error("Algo deu errado")
display.show_success("Operação concluída")
display.show_info("Informação adicional")

# Spinner (modo não-streaming)
display.start_spinner()
# ... aguarda resposta ...
display.update_spinner_tokens(150)
display.stop_spinner()

# Streaming
display.start_streaming()
display.add_streaming_chunk("Olá")
display.add_streaming_chunk(" mundo!")
full_text = display.stop_streaming()

# Input com autocompleção
user_input = display.prompt_input()

# Cleanup seguro
display.cleanup()
```

---

### `logging_config.py` - Sistema de Logging

Configuração de logging estruturado com suporte a JSON e console colorido.

#### Classes

| Classe | Descrição |
|--------|-----------|
| `StructuredFormatter` | Formatter JSON para produção |
| `ConsoleFormatter` | Formatter colorido para desenvolvimento |

#### Formato JSON (StructuredFormatter)

```json
{
  "timestamp": "2024-01-15T10:30:00.000000+00:00",
  "level": "INFO",
  "logger": "utils.api",
  "message": "Requisição enviada",
  "module": "api",
  "function": "send_message",
  "line": 386
}
```

#### Formato Console (ConsoleFormatter)

```
[10:30:00] INFO     utils.api: Requisição enviada
```

Cores por nível:
- DEBUG: Ciano
- INFO: Verde
- WARNING: Amarelo
- ERROR: Vermelho
- CRITICAL: Magenta

#### Uso

```python
from utils.logging_config import setup_logging

# Configuração básica
setup_logging()

# Configuração explícita
setup_logging(
    log_level="DEBUG",
    log_format="json",
    log_file="chatbot.log"
)

# Via variáveis de ambiente
# LOG_LEVEL=DEBUG LOG_FORMAT=json python chatbot.py
```

---

### `version.py` - Versão

Versão centralizada do projeto.

```python
from utils import __version__

print(f"Chatbot v{__version__}")  # Chatbot v1.0.0
```

---

## Exports do Pacote

O `__init__.py` exporta os seguintes símbolos:

```python
from utils import (
    # Versão
    __version__,

    # Configuração
    config,
    Config,
    ConfigurationError,

    # API
    OpenRouterClient,
    APIError,
    RateLimitError,

    # Conversação
    ConversationManager,
    ConversationLoadError,

    # Display
    Display,
)
```

---

## Padrões de Código

### Logging Lazy

```python
# Correto - avaliação lazy
logger.info("Mensagem: %s", variavel)

# Incorreto - f-string sempre avaliada
logger.info(f"Mensagem: {variavel}")
```

### Context Managers

```python
# Cliente API
with OpenRouterClient() as client:
    response = client.send_message(messages)

# Streaming
with client.send_message_stream(messages) as stream:
    for chunk in stream:
        process(chunk)
```

### Type Annotations

```python
def process_message(content: str) -> APIResponse:
    ...
```

### Repr para Debug

```python
class MyClass:
    def __repr__(self) -> str:
        return f"MyClass(attr={self.attr})"
```

---

## Testes

Cada módulo possui testes correspondentes em `tests/`:

```bash
# Todos os testes
pytest tests/ -v

# Módulo específico
pytest tests/test_api.py -v
pytest tests/test_config.py -v
pytest tests/test_conversation.py -v
pytest tests/test_display.py -v

# Com cobertura
pytest tests/ -v --cov=utils --cov-report=term-missing
```

Cobertura atual: **91%**
