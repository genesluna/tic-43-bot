# Chatbot Conversacional com IA

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: Educational](https://img.shields.io/badge/license-Educational-green.svg)](#licença)
[![Tests](https://img.shields.io/badge/tests-129%20passed-brightgreen.svg)](#testes)
[![Coverage](https://img.shields.io/badge/coverage-95%25-brightgreen.svg)](#testes)

**Projeto de Conclusão do Curso TIC-43**

Desenvolvido como trabalho de conclusão do curso **TIC 43 - Capacitação Tecnológica em Visão Computacional e Inteligência Artificial Generativa**, oferecido pelo [Instituto Vertex](https://www.vertex.org.br/tic-43/).

Um chatbot interativo via terminal que utiliza modelos de IA generativa através da API [OpenRouter](https://openrouter.ai) para manter conversas contextualizadas.

---

## Funcionalidades

| Recurso | Descrição |
|---------|-----------|
| **Interface Rica** | Terminal com formatação colorida e suporte a Markdown |
| **Multi-modelo** | Compatível com GPT-4, Claude, Llama e outros via OpenRouter |
| **Contexto Persistente** | Mantém histórico da conversa para respostas contextualizadas |
| **Streaming** | Respostas em tempo real com indicador de progresso |
| **Retry Inteligente** | Recuperação automática de erros de rede com backoff exponencial |
| **Personalizável** | System prompt, idioma, tom e formato configuráveis |
| **Salvamento** | Exporta conversas para JSON |

---

## Requisitos

- Python 3.10 ou superior
- Conta e chave de API do [OpenRouter](https://openrouter.ai)

---

## Instalação

```bash
# 1. Clone o repositório
git clone https://github.com/genesluna/chatbot-tic43.git
cd chatbot-tic43

# 2. Crie um ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou: venv\Scripts\activate  # Windows

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Configure o ambiente
cp .env.example .env
# Edite .env e adicione sua OPENROUTER_API_KEY
```

---

## Uso

```bash
python chatbot.py
```

### Comandos Disponíveis

| Comando | Descrição |
|---------|-----------|
| `sair`, `exit`, `quit` | Encerra o chatbot |
| `/limpar`, `/clear` | Limpa o histórico da conversa |
| `/salvar`, `/save` | Salva o histórico em arquivo JSON |
| `/ajuda`, `/help` | Mostra comandos disponíveis |
| `/modelo` | Mostra o modelo atual |

### Exemplo de Conversa

```
    ████████╗██╗ ██████╗    ██████╗  ██████╗ ████████╗    ██╗  ██╗██████╗
    ╚══██╔══╝██║██╔════╝    ██╔══██╗██╔═══██╗╚══██╔══╝    ██║  ██║╚════██╗
       ██║   ██║██║         ██████╔╝██║   ██║   ██║       ███████║ █████╔╝
       ██║   ██║██║         ██╔══██╗██║   ██║   ██║       ╚════██║ ╚═══██╗
       ██║   ██║╚██████╗    ██████╔╝╚██████╔╝   ██║            ██║██████╔╝
       ╚═╝   ╚═╝ ╚═════╝    ╚═════╝  ╚═════╝    ╚═╝            ╚═╝╚═════╝

    > Chatbot Conversacional com IA Generativa
    > Powered by OpenRouter

> Olá! Me explique o que é machine learning.

Machine Learning é um subcampo da Inteligência Artificial que permite
que sistemas aprendam padrões a partir de dados, melhorando seu
desempenho em tarefas específicas sem serem explicitamente programados.

> sair
Até logo!
```

---

## Configuração

Todas as configurações são feitas via variáveis de ambiente no arquivo `.env`:

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `OPENROUTER_API_KEY` | Chave da API OpenRouter | **(obrigatório)** |
| `OPENROUTER_MODEL` | Modelo de IA | `openai/gpt-4o-mini` |
| `SYSTEM_PROMPT` | Persona do chatbot | `Você é um assistente virtual útil...` |
| `RESPONSE_LANGUAGE` | Idioma das respostas | `português` |
| `RESPONSE_LENGTH` | Tamanho das respostas | `conciso` |
| `RESPONSE_TONE` | Tom/estilo | `amigável` |
| `RESPONSE_FORMAT` | Formato do texto | `markdown` |
| `MAX_MESSAGE_LENGTH` | Limite de caracteres/mensagem | `10000` |
| `MAX_HISTORY_SIZE` | Máximo de mensagens no histórico | `50` |
| `HISTORY_DIR` | Diretório para salvar histórico | `./history` |

### Exemplos de Personalização

<details>
<summary><b>Assistente Técnico Formal</b></summary>

```env
SYSTEM_PROMPT=Você é um especialista em tecnologia.
RESPONSE_LENGTH=detalhado
RESPONSE_TONE=técnico
RESPONSE_FORMAT=markdown
```
</details>

<details>
<summary><b>Assistente Casual em Inglês</b></summary>

```env
SYSTEM_PROMPT=You are a friendly assistant.
RESPONSE_LANGUAGE=inglês
RESPONSE_LENGTH=conciso
RESPONSE_TONE=casual
RESPONSE_FORMAT=texto
```
</details>

### Modelos Disponíveis

Alguns modelos populares via OpenRouter:

| Modelo | Descrição |
|--------|-----------|
| `openai/gpt-4o-mini` | Rápido e econômico (padrão) |
| `openai/gpt-4o` | Mais capaz, multimodal |
| `anthropic/claude-3.5-sonnet` | Excelente para código e análise |
| `anthropic/claude-3-haiku` | Rápido e econômico |
| `meta-llama/llama-3.1-70b-instruct` | Open source, alta qualidade |
| `google/gemini-pro-1.5` | Contexto longo (1M tokens) |

Consulte a [lista completa](https://openrouter.ai/models) no OpenRouter.

---

## Testes

O projeto possui 129 testes com 95% de cobertura.

```bash
# Executar testes
pytest tests/ -v

# Com cobertura
pytest tests/ -v --cov=utils --cov=chatbot --cov-report=term-missing
```

---

## Arquitetura

```
chatbot-tic43/
├── chatbot.py             # Ponto de entrada e loop principal
├── utils/
│   ├── api.py             # Cliente OpenRouter (retry, streaming)
│   ├── config.py          # Configurações via ambiente
│   ├── conversation.py    # Gerenciamento de histórico
│   └── display.py         # Interface rica do terminal
├── tests/
│   ├── test_api.py        # Testes do cliente API
│   ├── test_chatbot.py    # Testes do módulo principal
│   ├── test_config.py     # Testes de configuração
│   ├── test_conversation.py
│   ├── test_display.py
│   └── test_integration.py
├── requirements.txt       # Dependências de produção
├── requirements-dev.txt   # Dependências de desenvolvimento
└── .env.example           # Template de configuração
```

---

## Licença

Projeto desenvolvido para fins educacionais como trabalho de conclusão do curso TIC-43 - [Instituto Vertex](https://www.vertex.org.br/).
