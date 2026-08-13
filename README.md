# Agente de IA do zero em Python

Exemplo didatico de um agente conversacional no terminal, sem LangChain ou frameworks de agentes.
O modelo responde em JSON dizendo se quer chamar uma ferramenta ou finalizar a resposta.

## Ambiente virtual

Antes de rodar o projeto, ative o ambiente virtual:

```bash
source venv/bin/activate
```

Instale as dependencias dentro do venv:

```bash
pip install -r requirements.txt
```

Sempre que abrir um terminal novo, ative o venv de novo com:

```bash
source venv/bin/activate
```

## Ferramentas

- `calculadora`: avalia expressoes matematicas simples com seguranca.
- `data_hora`: retorna a data e hora atuais.
- `ler_arquivo`: le arquivos de texto dentro da pasta atual.

## Rodar com Ollama

1. Instale e abra o Ollama.
2. Baixe o modelo:

```bash
ollama pull llama3.1
```

3. Rode o agente:

```bash
source venv/bin/activate
PROVEDOR_LLM=ollama python3 agente.py
```

Por padrao, o script usa `http://localhost:11434/api/chat` e o modelo `llama3.1`.

## Rodar com Groq

1. Configure sua chave:

```bash
export GROQ_API_KEY="sua_chave_aqui"
```

2. Rode o agente:

```bash
source venv/bin/activate
PROVEDOR_LLM=groq python3 agente.py
```

Por padrao, o script usa o modelo `llama-3.1-8b-instant`.

## Variaveis uteis

```bash
PROVEDOR_LLM=ollama              # ollama ou groq
OLLAMA_URL=http://localhost:11434/api/chat
OLLAMA_MODELO=llama3.1
GROQ_MODELO=llama-3.1-8b-instant
MAX_PASSOS_AGENTE=6
```

## Exemplos de perguntas

```text
Quanto e 12 * (8 + 3)?
Que horas sao agora?
Leia o arquivo promises/promises.js e resuma em uma frase.
```
