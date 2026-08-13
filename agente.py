import ast
import json
import math
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path



PROVEDOR = os.getenv("PROVEDOR_LLM", "ollama").lower()
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
OLLAMA_MODELO = os.getenv("OLLAMA_MODELO", "llama3.1")
GROQ_MODELO = os.getenv("GROQ_MODELO", "llama-3.1-8b-instant")
MAX_PASSOS = int(os.getenv("MAX_PASSOS_AGENTE", "6"))


PROMPT_SISTEMA = """
Voce e um agente de IA didatico, em portugues, que pode usar ferramentas.

Voce SEMPRE deve responder usando apenas JSON valido, sem markdown e sem texto extra.

Quando precisar usar uma ferramenta, responda exatamente neste formato:
{"acao": "nome_ferramenta", "entrada": "valor"}

Quando ja souber a resposta final para o usuario, responda exatamente neste formato:
{"resposta_final": "texto"}

Ferramentas disponiveis:
- calculadora: resolve expressoes matematicas. Entrada: uma expressao como "2 + 2 * sqrt(9)".
- data_hora: retorna a data e hora atuais. Entrada: pode ser uma string vazia.
- ler_arquivo: le um arquivo de texto local dentro da pasta atual. Entrada: caminho do arquivo.

Use ferramentas quando elas forem uteis. Nao invente resultados de arquivos, contas ou data/hora.
""".strip()


def avaliar_expressao_matematica(expressao):
    """Avalia uma expressao matematica usando AST, sem liberar eval arbitrario."""
    funcoes_permitidas = {
        "abs": abs,
        "round": round,
        "sqrt": math.sqrt,
        "pow": pow,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "log": math.log,
        "log10": math.log10,
        "floor": math.floor,
        "ceil": math.ceil,
    }
    constantes_permitidas = {"pi": math.pi, "e": math.e}

    operadores_binarios = {
        ast.Add: lambda a, b: a + b,
        ast.Sub: lambda a, b: a - b,
        ast.Mult: lambda a, b: a * b,
        ast.Div: lambda a, b: a / b,
        ast.FloorDiv: lambda a, b: a // b,
        ast.Mod: lambda a, b: a % b,
        ast.Pow: lambda a, b: a**b,
    }
    operadores_unarios = {
        ast.UAdd: lambda a: +a,
        ast.USub: lambda a: -a,
    }

    def resolver(no):
        if isinstance(no, ast.Expression):
            return resolver(no.body)

        if isinstance(no, ast.Constant) and isinstance(no.value, (int, float)):
            return no.value

        if isinstance(no, ast.BinOp) and type(no.op) in operadores_binarios:
            esquerda = resolver(no.left)
            direita = resolver(no.right)
            return operadores_binarios[type(no.op)](esquerda, direita)

        if isinstance(no, ast.UnaryOp) and type(no.op) in operadores_unarios:
            return operadores_unarios[type(no.op)](resolver(no.operand))

        if isinstance(no, ast.Name) and no.id in constantes_permitidas:
            return constantes_permitidas[no.id]

        if isinstance(no, ast.Call) and isinstance(no.func, ast.Name):
            nome_funcao = no.func.id
            if nome_funcao not in funcoes_permitidas:
                raise ValueError(f"Funcao nao permitida: {nome_funcao}")
            argumentos = [resolver(argumento) for argumento in no.args]
            return funcoes_permitidas[nome_funcao](*argumentos)

        raise ValueError("Expressao contem operacao nao permitida.")

    arvore = ast.parse(expressao, mode="eval")
    return resolver(arvore)


def ferramenta_calculadora(entrada):
    try:
        resultado = avaliar_expressao_matematica(str(entrada))
        return f"Resultado: {resultado}"
    except Exception as erro:
        return f"Erro na calculadora: {erro}"


def ferramenta_data_hora(_entrada):
    agora = datetime.now().astimezone()
    return agora.strftime("Data e hora atuais: %Y-%m-%d %H:%M:%S %Z")


def ferramenta_ler_arquivo(entrada):
    try:
        caminho_base = Path.cwd().resolve()
        caminho = (caminho_base / str(entrada)).resolve()

        # Mantemos a leitura dentro da pasta atual para evitar acesso acidental a outros locais.
        if caminho_base not in caminho.parents and caminho != caminho_base:
            return "Erro ao ler arquivo: o caminho precisa estar dentro da pasta atual."

        if not caminho.is_file():
            return "Erro ao ler arquivo: arquivo nao encontrado."

        return caminho.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return "Erro ao ler arquivo: o arquivo nao parece ser texto UTF-8."
    except Exception as erro:
        return f"Erro ao ler arquivo: {erro}"


FERRAMENTAS = {
    "calculadora": ferramenta_calculadora,
    "data_hora": ferramenta_data_hora,
    "ler_arquivo": ferramenta_ler_arquivo,
}


def chamar_ollama(mensagens):
    """Envia o historico para o Ollama usando apenas biblioteca padrao do Python."""
    payload = {
        "model": OLLAMA_MODELO,
        "messages": mensagens,
        "stream": False,
        "options": {"temperature": 0},
    }

    requisicao = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(requisicao, timeout=120) as resposta:
            dados = json.loads(resposta.read().decode("utf-8"))
            return dados["message"]["content"]
    except urllib.error.URLError as erro:
        raise RuntimeError(
            "Nao consegui conectar ao Ollama. Verifique se ele esta rodando "
            f"em {OLLAMA_URL} e se o modelo {OLLAMA_MODELO} foi baixado."
        ) from erro


def chamar_groq(mensagens):
    """Envia o historico para a Groq. Esta funcao so precisa da lib groq instalada."""
    try:
        from groq import Groq
    except ImportError as erro:
        raise RuntimeError("Instale a biblioteca da Groq com: pip install groq") from erro

    cliente = Groq(api_key=os.getenv("GROQ_API_KEY"))
    resposta = cliente.chat.completions.create(
        model=GROQ_MODELO,
        messages=mensagens,
        temperature=0,
    )
    return resposta.choices[0].message.content


def chamar_llm(mensagens):
    if PROVEDOR == "ollama":
        return chamar_ollama(mensagens)
    if PROVEDOR == "groq":
        return chamar_groq(mensagens)
    raise ValueError("PROVEDOR_LLM precisa ser 'ollama' ou 'groq'.")


def extrair_json(texto):
    """Tenta converter a resposta do modelo em JSON, inclusive se vier com texto ao redor."""
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        inicio = texto.find("{")
        fim = texto.rfind("}")
        if inicio == -1 or fim == -1 or fim <= inicio:
            raise
        return json.loads(texto[inicio : fim + 1])


def executar_agente(pergunta_usuario):
    mensagens = [
        {"role": "system", "content": PROMPT_SISTEMA},
        {"role": "user", "content": pergunta_usuario},
    ]

    for passo in range(1, MAX_PASSOS + 1):
        resposta_texto = chamar_llm(mensagens)
        mensagens.append({"role": "assistant", "content": resposta_texto})

        try:
            decisao = extrair_json(resposta_texto)
        except json.JSONDecodeError:
            observacao = (
                "A resposta anterior nao era JSON valido. Responda novamente usando "
                'apenas {"acao": "...", "entrada": "..."} ou {"resposta_final": "..."}'
            )
            mensagens.append({"role": "user", "content": observacao})
            continue

        if "resposta_final" in decisao:
            return decisao["resposta_final"]

        nome_ferramenta = decisao.get("acao")
        entrada = decisao.get("entrada", "")

        if nome_ferramenta not in FERRAMENTAS:
            resultado = f"Ferramenta desconhecida: {nome_ferramenta}"
        else:
            resultado = FERRAMENTAS[nome_ferramenta](entrada)

        # A observacao entra no historico para o modelo usar no proximo passo.
        mensagens.append(
            {
                "role": "user",
                "content": (
                    f"Resultado da ferramenta '{nome_ferramenta}' no passo {passo}:\n"
                    f"{resultado}\n\n"
                    "Agora continue. Se ja tiver informacao suficiente, retorne resposta_final."
                ),
            }
        )

    return "O agente atingiu o limite de passos sem chegar a uma resposta final."


def loop_terminal():
    print("Agente de IA do zero em Python")
    print(f"Provedor ativo: {PROVEDOR}")
    print("Digite 'sair' para encerrar.\n")

    while True:
        try:
            pergunta = input("Voce: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nEncerrando.")
            break

        if pergunta.lower() in {"sair", "exit", "quit"}:
            print("Encerrando.")
            break

        if not pergunta:
            continue

        try:
            resposta = executar_agente(pergunta)
            print(f"Agente: {resposta}\n")
        except Exception as erro:
            print(f"Erro: {erro}\n", file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        pergunta_cli = " ".join(sys.argv[1:])
        print(executar_agente(pergunta_cli))
    else:
        loop_terminal()
