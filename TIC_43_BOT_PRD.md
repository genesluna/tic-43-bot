# PRD - Chatbot Conversacional com IA em Python

## Visão Geral do Produto

**Projeto:** Chatbot TIC43
**Tipo:** Chatbot conversacional com IA generativa
**Formato:** Scripts Python (.py)
**Interface:** Terminal com formatação aprimorada
**API:** OpenRouter (acesso a múltiplos modelos de LLM)

---

## Objetivos

Desenvolver um chatbot interativo via terminal que:
- Mantenha conversas contextualizadas usando modelos de IA generativa
- Ofereça experiência de usuário agradável com formatação visual
- Implemente todos os requisitos obrigatórios + diferenciais

---

## Requisitos Funcionais

### Obrigatórios (Core)

| ID | Requisito | Descrição |
|----|-----------|-----------|
| RF01 | Interface de entrada | Input de texto via terminal para o usuário digitar mensagens |
| RF02 | Integração OpenRouter | Envio de mensagens para API OpenRouter e recebimento de respostas |
| RF03 | Exibição de respostas | Apresentação clara e formatada das respostas do bot |
| RF04 | Histórico de conversa | Manutenção do contexto entre mensagens na sessão |
| RF05 | Encerramento controlado | Comandos `sair`, `exit`, `quit` para finalizar |

### Diferenciais (Extras)

| ID | Requisito | Descrição |
|----|-----------|-----------|
| RD01 | Tratamento de erros | Captura e exibição amigável de erros de conexão/API |
| RD02 | Indicador de carregamento | Spinner/animação durante processamento |
| RD03 | Limpar histórico | Comando `/limpar` ou `/clear` para resetar contexto |
| RD04 | System prompt customizável | Personalização do comportamento do bot |
| RD05 | Formatação terminal | Cores, separadores, bordas estilizadas |
| RD06 | Salvamento de histórico | Exportar conversa para arquivo |

---

## Arquitetura Técnica

### Estrutura de Arquivos

```
chatbot-tic43/
├── README.md              # Documentação do projeto
├── requirements.txt       # Dependências Python
├── .env.example           # Template de variáveis de ambiente
├── .gitignore             # Arquivos ignorados pelo git
├── chatbot.py             # Ponto de entrada principal
└── utils/
    ├── __init__.py
    ├── api.py             # Cliente OpenRouter
    ├── conversation.py    # Gerenciamento de histórico
    ├── display.py         # Formatação e exibição terminal
    └── config.py          # Configurações e constantes
```

### Dependências (requirements.txt)

```
httpx>=0.27.0          # Cliente HTTP async para API
python-dotenv>=1.0.0   # Carregar variáveis de ambiente
rich>=13.7.0           # Formatação rica no terminal
```

### Fluxo de Dados

```
[Usuário] → [Input Terminal] → [Histórico] → [OpenRouter API]
                                    ↑               ↓
                              [Atualiza]     [Resposta IA]
                                    ↑               ↓
                              [Display] ← [Formatação]
```

---

## Especificações Técnicas

### API OpenRouter

- **Base URL:** `https://openrouter.ai/api/v1/chat/completions`
- **Autenticação:** Bearer token via header
- **Modelo padrão:** `openai/gpt-4o-mini` (configurável via .env)
- **Formato:** OpenAI-compatible API

### System Prompt (Configurável)

O usuário poderá definir a persona do chatbot via variável de ambiente `SYSTEM_PROMPT` no arquivo `.env`. Valor padrão:

```
Você é um assistente virtual útil e amigável. Responda de forma clara e concisa.
```

### Interface Terminal

- **Biblioteca:** Rich (formatação avançada)
- **Cores:**
  - Verde para mensagens do usuário
  - Azul/Cyan para respostas do bot
  - Amarelo para avisos
  - Vermelho para erros
- **Elementos visuais:**
  - Banner de título estilizado
  - Separadores entre mensagens
  - Spinner durante carregamento
  - Timestamps opcionais

### Comandos Especiais

| Comando | Ação |
|---------|------|
| `sair`, `exit`, `quit` | Encerra a aplicação |
| `/limpar`, `/clear` | Limpa o histórico de conversa |
| `/salvar`, `/save` | Exporta histórico para arquivo |
| `/ajuda`, `/help` | Mostra comandos disponíveis |
| `/modelo` | Mostra/altera modelo atual |

---

## Plano de Implementação

### Fase 0: Documentação PRD
1. Salvar este PRD como `TIC_43_BOT_PRD.md` no diretório do projeto

### Fase 1: Estrutura Base
2. Criar estrutura de diretórios
3. Criar `requirements.txt`
4. Criar `.env.example` e `.gitignore`
5. Criar `utils/config.py` com configurações

### Fase 2: Core - API
5. Implementar `utils/api.py` - cliente OpenRouter
6. Implementar tratamento de erros da API

### Fase 3: Core - Conversação
7. Implementar `utils/conversation.py` - gerenciamento de histórico
8. Implementar system prompt configurável

### Fase 4: Core - Interface
9. Implementar `utils/display.py` - formatação terminal
10. Criar banner, separadores e estilos

### Fase 5: Integração
11. Implementar `chatbot.py` - loop principal
12. Integrar todos os módulos
13. Implementar comandos especiais

### Fase 6: Extras
14. Adicionar spinner de carregamento
15. Implementar salvamento de histórico
16. Implementar comando de ajuda

### Fase 7: Documentação
17. Criar README.md completo
18. Adicionar comentários/docstrings

---

## Critérios de Aceite

- [ ] Usuário consegue iniciar conversa e receber respostas
- [ ] Contexto é mantido entre mensagens
- [ ] Comandos de saída funcionam corretamente
- [ ] Erros de API são tratados graciosamente
- [ ] Interface terminal é visualmente agradável
- [ ] Histórico pode ser limpo e salvo
- [ ] Documentação está completa

---

## Arquivos a Criar/Modificar

1. `TIC_43_BOT_PRD.md` (este documento)
2. `requirements.txt`
3. `.env.example`
4. `.gitignore`
5. `utils/__init__.py`
6. `utils/config.py`
7. `utils/api.py`
8. `utils/conversation.py`
9. `utils/display.py`
10. `chatbot.py`
11. `README.md`
