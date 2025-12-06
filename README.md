# Chatbot Conversacional com IA

**Projeto de Conclusão do Curso TIC-43**

Este projeto foi desenvolvido como trabalho de conclusão do curso **TIC 43 - Capacitação Tecnológica em Visão Computacional e Inteligência Artificial Generativa**, oferecido pelo [Instituto Vertex](https://www.vertex.org.br/tic-43/).

Um chatbot interativo via terminal que utiliza modelos de IA generativa através da API OpenRouter para manter conversas contextualizadas.

## Funcionalidades

- Interface de terminal com formatação rica (cores, markdown)
- Integração com múltiplos modelos de IA via OpenRouter
- Histórico de conversa com manutenção de contexto
- Comandos especiais para gerenciamento da sessão
- Tratamento de erros de conexão
- Indicador visual de carregamento
- Salvamento de histórico em arquivo JSON
- System prompt personalizável

## Requisitos

- Python 3.10 ou superior
- Conta e chave de API do [OpenRouter](https://openrouter.ai)

## Instalação

1. Clone o repositório:

```bash
git clone <url-do-repositorio>
cd chatbot-tic43
```

2. Crie um ambiente virtual (recomendado):

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows
```

3. Instale as dependências:

```bash
pip install -r requirements.txt
```

4. Configure as variáveis de ambiente:

```bash
cp .env.example .env
```

5. Edite o arquivo `.env` e adicione sua chave da API OpenRouter:

```
OPENROUTER_API_KEY=sua_chave_aqui
```

## Uso

Execute o chatbot:

```bash
python chatbot.py
```

### Comandos Disponíveis

| Comando                | Descrição                         |
| ---------------------- | --------------------------------- |
| `sair`, `exit`, `quit` | Encerra o chatbot                 |
| `/limpar`, `/clear`    | Limpa o histórico da conversa     |
| `/salvar`, `/save`     | Salva o histórico em arquivo JSON |
| `/ajuda`, `/help`      | Mostra comandos disponíveis       |
| `/modelo`              | Mostra o modelo atual             |

### Exemplo de Conversa

```
╭──────────────────────────────────────────╮
│      CHATBOT IA - Projeto TIC43          │
╰──────────────────────────────────────────╯

Você: Olá, tudo bem?
Bot: Olá! Tudo ótimo, obrigado por perguntar. Como posso ajudá-lo hoje?

Você: Me explique o que é machine learning.
Bot: Machine Learning é um subcampo da Inteligência Artificial que permite
     que sistemas aprendam padrões a partir de dados...

Você: sair
╭──────────────────────────────────────────╮
│ Até logo! Foi um prazer conversar.       │
╰──────────────────────────────────────────╯
```

## Configuração

As seguintes variáveis podem ser configuradas no arquivo `.env`:

| Variável             | Descrição                | Padrão               |
| -------------------- | ------------------------ | -------------------- |
| `OPENROUTER_API_KEY` | Chave da API OpenRouter  | (obrigatório)        |
| `OPENROUTER_MODEL`   | Modelo de IA a utilizar  | `openai/gpt-4o-mini` |
| `SYSTEM_PROMPT`      | Personalidade do chatbot | Assistente amigável  |

### Modelos Disponíveis

Alguns modelos populares disponíveis via OpenRouter:

- `openai/gpt-4o-mini` - Rápido e econômico

## Testes

O projeto inclui testes unitários.

### Executar testes

```bash
pytest tests/ -v
```

### Executar testes com cobertura

```bash
pytest tests/ -v --cov=utils --cov-report=term-missing
```

### Estrutura de testes

- `tests/test_config.py` - Testes de configuração
- `tests/test_conversation.py` - Testes do gerenciador de conversas
- `tests/test_api.py` - Testes do cliente OpenRouter
- `tests/test_display.py` - Testes da interface de exibição

## Estrutura do Projeto

```
chatbot-tic43/
├── README.md              # Esta documentação
├── requirements.txt       # Dependências Python
├── .env.example           # Template de configuração
├── .gitignore             # Arquivos ignorados pelo git
├── chatbot.py             # Ponto de entrada principal
├── TIC_43_BOT_PRD.md      # Documento de requisitos do produto
├── tests/                 # Testes unitários
│   ├── __init__.py
│   ├── test_api.py
│   ├── test_config.py
│   ├── test_conversation.py
│   └── test_display.py
└── utils/
    ├── __init__.py        # Inicialização do módulo
    ├── api.py             # Cliente OpenRouter
    ├── config.py          # Configurações
    ├── conversation.py    # Gerenciamento de histórico
    └── display.py         # Formatação do terminal
```

## Licença

Projeto desenvolvido para fins educacionais como trabalho de conclusão do curso TIC-43 - Instituto Vertex.
