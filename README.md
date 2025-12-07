# Chatbot Conversacional com IA

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: Educational](https://img.shields.io/badge/license-Educational-green.svg)](#licença)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](#testes)
[![Coverage](https://img.shields.io/badge/coverage->80%25-brightgreen.svg)](#testes)
[![Wiki](https://img.shields.io/badge/docs-wiki-blue.svg)](https://github.com/genesluna/tic-43-bot/wiki)

**Projeto de Conclusão do Curso TIC-43**

Desenvolvido como trabalho de conclusão do curso **TIC 43 - Capacitação Tecnológica em Visão Computacional e Inteligência Artificial Generativa**, oferecido pelo [Instituto Vertex](https://www.vertex.org.br/tic-43/).

Um chatbot interativo via terminal que utiliza modelos de IA generativa através da API [OpenRouter](https://openrouter.ai) para manter conversas contextualizadas.

---

## Funcionalidades

| Recurso                  | Descrição                                                       |
| ------------------------ | --------------------------------------------------------------- |
| **Interface Rica**       | Terminal com formatação colorida e suporte a Markdown           |
| **Multi-modelo**         | Compatível com GPT-4, Claude, Llama e outros via OpenRouter     |
| **Contexto Persistente** | Mantém histórico da conversa para respostas contextualizadas    |
| **Streaming**            | Modo streaming ou contagem de tokens animada (configurável)     |
| **Retry Inteligente**    | Recuperação automática de erros de rede com backoff exponencial |
| **Personalizável**       | System prompt, idioma, tom e formato configuráveis              |
| **Salvamento**           | Exporta conversas para JSON com nome personalizado              |
| **Autocompletar**        | Tab para completar comandos e nomes de arquivo                  |
| **Segurança**            | TLS 1.2+, validação de entrada, proteção contra path traversal  |

---

## Segurança

O projeto implementa práticas de segurança robustas:

| Controle | Descrição |
|----------|-----------|
| **Dependências fixas** | Versões pinadas para proteção contra supply chain attacks |
| **TLS 1.2+** | Comunicação segura com enforcement de versão mínima |
| **Validação de entrada** | Limites de tamanho, validação de tipos e roles |
| **Proteção de credenciais** | Mascaramento de API keys em logs e erros |
| **Path traversal** | Sanitização de nomes de arquivo e validação de diretório |
| **Symlink protection** | Rejeição de links simbólicos em operações de arquivo |
| **Escrita atômica** | Arquivos temporários para prevenir corrupção |
| **Thread-safety** | Locks e condições para operações concorrentes |
| **Rate limiting** | Exponential backoff com jitter para retentativas |
| **Correlação de logs** | Request IDs para rastreabilidade |

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

### Opções de Linha de Comando

```bash
python chatbot.py --help              # Exibe ajuda
python chatbot.py --version           # Exibe versão
python chatbot.py -m anthropic/claude-3.5-sonnet  # Define modelo
python chatbot.py --no-stream         # Desativa streaming (mostra spinner com tokens)
python chatbot.py --log-level DEBUG   # Ativa logging detalhado
python chatbot.py --log-file app.log  # Salva logs em arquivo
```

### Comandos Disponíveis

| Comando                                  | Descrição                              |
| ---------------------------------------- | -------------------------------------- |
| `sair`, `exit`, `quit`                   | Encerra o chatbot                      |
| `/limpar`, `/clear`                      | Limpa o histórico da conversa          |
| `/salvar [nome]`, `/save [nome]`         | Salva histórico (nome opcional)        |
| `/listar`, `/list`                       | Lista históricos salvos                |
| `/carregar <arquivo>`, `/load <arquivo>` | Carrega histórico (Tab autocompleta)   |
| `/ajuda`, `/help`                        | Mostra comandos disponíveis            |
| `/modelo [nome]`, `/model [nome]`        | Mostra ou altera o modelo atual        |
| `/streaming`, `/stream`                  | Alterna modo streaming on/off          |

### Exemplo de Conversa

```
    ████████╗██╗ ██████╗    ██████╗  ██████╗ ████████╗    ██╗  ██╗██████╗
    ╚══██╔══╝██║██╔════╝    ██╔══██╗██╔═══██╗╚══██╔══╝    ██║  ██║╚════██╗
       ██║   ██║██║         ██████╔╝██║   ██║   ██║       ███████║ █████╔╝
       ██║   ██║██║         ██╔══██╗██║   ██║   ██║       ╚════██║ ╚═══██╗
       ██║   ██║╚██████╗    ██████╔╝╚██████╔╝   ██║            ██║██████╔╝
       ╚═╝   ╚═╝ ╚═════╝    ╚═════╝  ╚═════╝    ╚═╝            ╚═╝╚═════╝

    > Chatbot Conversacional com IA Generativa
    > Powered by Vertex

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

| Variável               | Descrição                        | Padrão                                 |
| ---------------------- | -------------------------------- | -------------------------------------- |
| `OPENROUTER_API_KEY`   | Chave da API OpenRouter          | **(obrigatório)**                      |
| `OPENROUTER_MODEL`     | Modelo de IA                     | `openai/gpt-4o-mini`                   |
| `SYSTEM_PROMPT`        | Persona do chatbot               | `Você é um assistente virtual útil...` |
| `RESPONSE_LANGUAGE`    | Idioma das respostas             | `português`                            |
| `RESPONSE_LENGTH`      | Tamanho das respostas            | `conciso`                              |
| `RESPONSE_TONE`        | Tom/estilo                       | `amigável`                             |
| `RESPONSE_FORMAT`      | Formato do texto                 | `markdown`                             |
| `MAX_MESSAGE_LENGTH`   | Limite de caracteres/mensagem    | `10000`                                |
| `MAX_HISTORY_SIZE`     | Máximo de pares de conversa      | `25`                                   |
| `HISTORY_DIR`          | Diretório para salvar histórico  | `./history`                            |
| `STREAM_RESPONSE`      | Modo streaming (true/false)      | `true`                                 |
| `LOG_LEVEL`            | Nível de logging                 | `WARNING`                              |
| `LOG_FORMAT`           | Formato do log (console/json)    | `console`                              |
| `LOG_FILE`             | Arquivo de log (opcional)        | -                                      |
| `HTTP_CONNECT_TIMEOUT` | Timeout de conexão (segundos)    | `10.0`                                 |
| `HTTP_READ_TIMEOUT`    | Timeout de leitura (segundos)    | `90.0`                                 |
| `HTTP_WRITE_TIMEOUT`   | Timeout de escrita (segundos)    | `10.0`                                 |
| `HTTP_POOL_TIMEOUT`    | Timeout do pool (segundos)       | `10.0`                                 |

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

| Modelo                              | Descrição                       |
| ----------------------------------- | ------------------------------- |
| `openai/gpt-4o-mini`                | Rápido e econômico (padrão)     |
| `openai/gpt-4o`                     | Mais capaz, multimodal          |
| `anthropic/claude-3.5-sonnet`       | Excelente para código e análise |
| `anthropic/claude-3-haiku`          | Rápido e econômico              |
| `meta-llama/llama-3.1-70b-instruct` | Open source, alta qualidade     |
| `google/gemini-pro-1.5`             | Contexto longo (1M tokens)      |

Consulte a [lista completa](https://openrouter.ai/models) no OpenRouter.

---

## Testes

O projeto possui uma suíte de testes abrangente com 338 testes e 92% de cobertura.

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
│   ├── api.py             # Cliente OpenRouter (retry, streaming, tokens)
│   ├── config.py          # Configurações via ambiente
│   ├── conversation.py    # Gerenciamento de histórico
│   ├── display.py         # Interface rica do terminal
│   ├── logging_config.py  # Configuração de logging estruturado
│   └── version.py         # Versão centralizada do projeto
├── tests/
│   ├── conftest.py            # Fixtures compartilhados
│   ├── helpers.py             # Utilitários de teste
│   ├── test_api.py            # Testes do cliente API
│   ├── test_chatbot.py        # Testes do módulo principal
│   ├── test_config.py         # Testes de configuração
│   ├── test_conversation.py   # Testes do gerenciador de conversa
│   ├── test_display.py        # Testes da interface do terminal
│   ├── test_integration.py    # Testes de integração
│   └── test_logging_config.py # Testes do sistema de logging
├── requirements.txt       # Dependências de produção (versões fixas)
├── requirements-dev.txt   # Dependências de desenvolvimento
└── .env.example           # Template de configuração
```

---

## Documentação

Para documentação completa, consulte a [Wiki do projeto](https://github.com/genesluna/tic-43-bot/wiki):

- [Instalação](https://github.com/genesluna/tic-43-bot/wiki/Instalação) - Guia completo de setup
- [Configuração](https://github.com/genesluna/tic-43-bot/wiki/Configuração) - Todas as variáveis de ambiente
- [Comandos](https://github.com/genesluna/tic-43-bot/wiki/Comandos) - Referência completa
- [Arquitetura](https://github.com/genesluna/tic-43-bot/wiki/Arquitetura) - Visão técnica
- [Segurança](https://github.com/genesluna/tic-43-bot/wiki/Segurança) - Controles implementados
- [FAQ](https://github.com/genesluna/tic-43-bot/wiki/FAQ) - Perguntas frequentes

---

## Licença

Projeto desenvolvido para fins educacionais como trabalho de conclusão do curso TIC-43 - [Instituto Vertex](https://www.vertex.org.br/).
