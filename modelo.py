import os
import pandas as pd
import numpy as np
import json
import datetime
import traceback
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
import base64
from io import BytesIO
from langchain.tools import Tool
from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
from langchain_community.callbacks import get_openai_callback
from dotenv import load_dotenv
from pathlib import Path
from rapidfuzz import process,  fuzz
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle,Paragraph
from reportlab.lib import colors
import unicodedata
import re
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from dateutil.relativedelta import relativedelta
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
caminho = os.path.join(BASE_DIR, "dados", "sapore_funcionario.xlsx")


ultimo_grafico_base64 = None # Guarda imagem
# api_key = st.secrets["OPENAI_API_KEY"]
ultimo_pdf_base64 = None

# --- CONFIGURAÇÃO INICIAL ---

# Carregar variáveis de ambiente
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# Arquivo json
LOG_FILE = "log_interacoes.jsonl"

# Carregar DataFrame
try:
    df = pd.read_excel(caminho)
    #df_remedios = pd.read_csv("data/BASE RBG - POC(PRODUTOS).csv")  
    # df_exemplo = df.head(3).to_string()
    # df_remedio_exemplo = df_remedios.head(3).to_string()


except Exception as e:
    print(f"Erro ao carregar o banco de dados: {e}")
    exit(1)

# --- FERRAMENTA DE CONSULTA (sem alterações) ---

def query_dataframe(query: str) -> str:
    try:
        df_preparado = preparar_dataframe(df)

        safe_env = {
            'df': df_preparado,
            'pd': pd,
            'np': np,
            'result': None
        }

        # Execução do código
        if '\n' in query:
            lines = query.strip().split('\n')
            last_line = lines[-1].strip()

            if '=' not in last_line and not last_line.startswith('print'):
                lines[-1] = f"result = {last_line}"
            elif last_line.startswith('print'):
                lines[-1] = f"result = {last_line[6:-1]}"

            exec('\n'.join(lines), safe_env)
            result = safe_env.get('result')

            if result is None:
                for line in reversed(lines):
                    if '=' in line:
                        var_name = line.split('=')[0].strip()
                        if var_name in safe_env:
                            result = safe_env[var_name]
                            break
        else:
            result = eval(query, {}, safe_env)

        # CORREÇÃO PRINCIPAL: se vier máscara booleana, vira DataFrame
        if isinstance(result, pd.Series) and result.dtype == bool:
            result = df_preparado[result]

        if result is None:
            return "Operação executada (sem retorno)"

        # Ordenação segura (se tiver coluna meses)
        if isinstance(result, pd.DataFrame) and 'meses' in result.columns:
            result = result.sort_values(by='meses', ascending=False)

        # Tratamento de saída
        if isinstance(result, (pd.DataFrame, pd.Series)):
            if len(result) > 10:
                return (
                    f"Resultado truncado (10 de {len(result)} linhas):\n"
                    f"{result.head(10).to_string()}"
                )
            return f"Resultado:\n{result.to_string()}"

        if isinstance(result, (list, dict, set)):
            result_str = str(result)
            if len(result_str) > 300:
                return f"Resultado ({type(result).__name__}) truncado:\n{result_str[:300]}..."
            return f"Resultado ({type(result).__name__}):\n{result_str}"

        result_str = str(result)
        if len(result_str) > 200:
            return f"Resultado truncado: {result_str[:200]}..."

        return f"Resultado: {result_str}"

    except Exception as e:
        return f"ERRO: {str(e)}\nDica: Use 'df' para referenciar o DataFrame principal"


def plot_chart(query: str) -> str:
    """
    Executa código para criar gráficos usando matplotlib/seaborn
    """
    df_copy = preparar_dataframe(df)

    try:
        # Configurar o ambiente seguro
        plt.style.use('default')
        fig, ax = plt.subplots(figsize=(10, 6))
        
        safe_env = {
            'df': df_copy,
            #'df_remedios':  df_remedios,
            'pd': pd,
            'np': np,
            'plt': plt,
            'sns': sns,
            'fig': fig,
            'ax': ax
        }
        
        # Executar o código
        exec(query, safe_env)
        
        # Salvar o gráfico em base64 para o Streamlit
        buffer = BytesIO()
        plt.tight_layout()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        
        # Converter para base64
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        
        # IMPORTANTE: Salvar o gráfico em uma variável global para o Streamlit
        # e retornar apenas uma mensagem curta para o LLM
        global ultimo_grafico_base64
        ultimo_grafico_base64 = img_base64
        
        return "GRAFICO_CRIADO_COM_SUCESSO"
        
    except Exception as e:
        plt.close()
        return f"ERRO ao criar gráfico: {str(e)}"


#########


# função para encontrar cargos similares 


def normalizar_texto(texto):
    return str(texto).strip().lower()


# toll para buscar canrgos
def buscar_cargos_similares(cargo_input: str) -> str:
    cargos_unicos = (
        df['Descricao']
        .dropna()
        .astype(str)
        .str.strip()
        .str.lower()
        .unique()
    )

    # se o input for exatamente igual a um cargo do banco, confirmar direto...
    cargo_normalizado = cargo_input.strip().lower()
    if cargo_normalizado in cargos_unicos:
        return f"CARGO_CONFIRMADO:{cargo_normalizado}"

    resultados = process.extract(
        cargo_normalizado,
        cargos_unicos,
        scorer=fuzz.token_set_ratio,
        limit=5
    )

    similares = [r[0] for r in resultados if r[1] >= 70]

    if not similares:
        return "Nenhum cargo similar encontrado."

    if len(similares) == 1:
        return f"CARGO_UNICO:{similares[0]}"

    return "CARGOS_MULTIPLOS:\n" + "\n".join(similares)


#### novas tolss ######

def normalizar_texto(texto):
    if pd.isna(texto):
        return ""

    # minúsculo
    texto = texto.lower()

    # remover acento
    texto = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('utf-8')

    # remover caracteres especiais
    texto = re.sub(r'[^a-z0-9\s]', '', texto)

    # remover espaços extras
    texto = re.sub(r'\s+', ' ', texto).strip()

    return texto



def preparar_dataframe(df):
    df_copy = df.copy()
    df_copy['Descricao'] = df_copy['Descricao'].apply(normalizar_texto)


    df_copy['DataAdmissao'] = pd.to_datetime(df_copy['DataAdmissao'], errors='coerce')
    df_copy['DataDemissao'] = pd.to_datetime(df_copy['DataDemissao'], errors='coerce')

    hoje = pd.Timestamp.now()
    def _meses_relativedelta(row):
        inicio = row['DataAdmissao']
        fim    = row['DataDemissao'] if pd.notna(row['DataDemissao']) else hoje
        if pd.isna(inicio):
            return 0
        delta = relativedelta(fim, inicio)
        return delta.years * 12 + delta.months
 
    df_copy['meses'] = df_copy.apply(_meses_relativedelta, axis=1)
 
    
    df_copy['meses_desde_saida'] = (
        (hoje.year  - df_copy['DataDemissao'].dt.year)  * 12 +
        (hoje.month - df_copy['DataDemissao'].dt.month)
    )
 
    return df_copy



def gerar_pdf_colaboradores(df_filtrado):
    buffer = BytesIO()

    # Página A4 com margens
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=10*mm,
        rightMargin=10*mm,
        topMargin=10*mm,
        bottomMargin=10*mm
    )

    styles = getSampleStyleSheet()
    styleN = ParagraphStyle(
    name='NormalSmall',
    fontSize=6,     # 🔥 aqui está o segredo
    leading=7       # espaçamento entre linhas
    )

    
    data = []

    # Cabeçalho
    header = [Paragraph(str(col), styleN) for col in df_filtrado.columns]
    data.append(header)

    # Linhas
    for _, row in df_filtrado.iterrows():
        linha = [Paragraph(str(cell), styleN) for cell in row]
        data.append(linha)

  
    num_cols = len(df_filtrado.columns)
    largura_total = A4[0] - 20*mm  # largura útil (menos margens)
    col_width = largura_total / num_cols

    col_widths = [col_width] * num_cols

    tabela = Table(data, colWidths=col_widths, repeatRows=1)

    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR',(0,0),(-1,0),colors.white),

        ('GRID', (0,0), (-1,-1), 0.5, colors.black),

        ('FONTSIZE', (0,0), (-1,-1), 5),

        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),

        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))

    doc.build([tabela])

    buffer.seek(0)

    pdf_base64 = base64.b64encode(buffer.read()).decode()

    return pdf_base64



def buscar_colaboradores(filtro: str) -> str:
    try:
        df_copy = preparar_dataframe(df)

        safe_env = {
            'df': df_copy,
            'pd': pd,
            'np': np
        }

        result = eval(filtro, {}, safe_env)

        if isinstance(result, pd.Series) and result.dtype == bool:
            df_filtrado = df_copy[result]
        else:
            df_filtrado = result

        if df_filtrado.empty:
            return "Nenhum colaborador encontrado."

        if 'meses' in df_filtrado.columns:
            df_filtrado = df_filtrado.sort_values(by='meses', ascending=False)

        # ✅ SEMPRE gerar o PDF, independente da quantidade
        global ultimo_pdf_base64
        ultimo_pdf_base64 = gerar_pdf_colaboradores(df_filtrado)

        if len(df_filtrado) > 10:
            return f"Foram encontrados {len(df_filtrado)} colaboradores. PDF disponível para download."

        # ≤10: mostrar no chat E PDF disponível
        top = df_filtrado.head(10)
        resposta = []
        for _, row in top.iterrows():
            resposta.append(
                f"{row['Nome']} | {row['meses']} meses | {row['RazaoSocial']} | {row['Celular']}"
            )

        return "\n".join(resposta) + f"\n\n({len(df_filtrado)} colaborador(es) — PDF disponível para download)"

    except Exception as e:
        return f"ERRO: {str(e)}"


def metricas_rh(query: str) -> str:
    try:
        df_copy = preparar_dataframe(df)

        safe_env = {
            'df': df_copy,
            'pd': pd,
            'np': np
        }

        result = eval(query, {}, safe_env)

        return f"Resultado: {result}"

    except Exception as e:
        return f"ERRO: {str(e)}"
    
    
######



# --- CONFIGURAÇÃO DO AGENTE ---

tools = [
    Tool(
        name="dataframe_query",
        func=query_dataframe,
        description="""Ferramenta para consultar o DataFrame 'doencas' já carregado.
       Use essa ferramenta para fazer consultas usando pandas no dataframe"""
    ),
    Tool(
        name="plot_chart",
        func=plot_chart,
        description="""Ferramenta para criar gráficos usando matplotlib/seaborn.
        Use 'df' para o DataFrame, 'plt' para matplotlib, 'sns' para seaborn.
        Sempre use plt.title(), plt.xlabel(), plt.ylabel() para rotular o gráfico.
        Exemplo: plt.bar(df['coluna'].value_counts().index, df['coluna'].value_counts().values)"""
    ),
    Tool(
    name="buscar_cargos_similares",
    func=buscar_cargos_similares,
    description="""
    Use essa ferramenta quando o usuário mencionar um cargo (ex: "atendente", "analista").

    Ela retorna cargos semelhantes existentes no banco.

    Retornos possíveis:
    - "CARGO_UNICO:<cargo>" → apenas um cargo encontrado
    - "CARGOS_MULTIPLOS:\n..." → lista de cargos para o usuário escolher

    Sempre use essa ferramenta antes de buscar candidatos.
    """
    ),
    Tool(
        name="buscar_colaboradores",
        func=buscar_colaboradores,
        description=""" 
    Use para listar colaboradores com filtros.

    Exemplos:
    - cozinheiros com mais de 6 meses:
    df[(df['Descricao'].str.contains('cozinheiro', case=False)) & (df['meses'] >= 6)]

    - trabalharam na empresa X:
    df[df['RazaoSocial'].str.contains('empresa x', case=False)]

    - trabalharam em 2025:
    df[df['DataAdmissao'].dt.year == 2025]

    Combine filtros com & e |.
    """
    ),
        Tool(
            name="metricas_rh",
            func=metricas_rh,
            description="""
    Use para responder perguntas de quantidade.
    Exemplo:
    df['Nome'].nunique()
    """
    )
    ]

llm = ChatOpenAI(
    model="gpt-4.1-mini-2025-04-14",     #"gpt-4.1-mini-2025-04-14"
    openai_api_key=api_key,
    temperature=0.1,
)

prompt = ChatPromptTemplate.from_messages([
    ("system",f"""
Você é um assistente de RH.

Você responde dois tipos de perguntas:

========================
1) LISTAR COLABORADORES
========================
Use 'buscar_colaboradores'

Quando usar:
- "me indique"
- "quem são"
- "listar"

Filtros possíveis:
- cargo → df['Descricao']
- empresa → df['RazaoSocial']
- ano → df['DataAdmissao'].dt.year
- tempo empregado → df['meses']
- tempo desde saída da empresa → df['meses_desde_saida']
========================
TEMPO (IMPORTANTE)
========================

Existem dois tipos de tempo:

1) Tempo de empresa:
→ coluna: df['meses']

2) Tempo desde saída:
→ coluna: df['meses_desde_saida']
→ usar quando o usuário falar:
   - "saiu há X meses"
   - "demitidos há X meses"
   - "recentemente saíram"

Exemplo:
"saíram há menos de 6 meses"
df[
 (df['DataDemissao'].notna()) &
 (df['meses_desde_saida'] <= 6)
]     

========================
2) MÉTRICAS
========================
Use 'metricas_rh'

Quando usar:
- "quantas pessoas"
- "quantidade"

========================
TRATAMENTO DE CARGOS
========================

Sempre que o usuário mencionar um cargo:

1. Use 'buscar_cargos_similares'

2. Se retorno for:

- CARGO_UNICO:
  → use diretamente e continue

- CARGOS_MULTIPLOS:
  → NÃO continue
  → NÃO chame nenhuma outra ferramenta
  → pergunte ao usuário qual cargo deseja usar

Formato da pergunta:
"Encontrei múltiplos cargos similares:
- cargo 1
- cargo 2
- cargo 3

Qual deles você deseja usar?"

3. Só continue após o usuário escolher um cargo

========================
 IMPORTANTE
========================

NUNCA use str.contains para cargos quando houver ambiguidade.

========================
REGRAS
========================
- Sempre usar ferramentas
- Nunca responder direto
- Sempre gerar código pandas válido
  
========================
EXEMPLOS
========================

Pergunta: cozinheiros com 6 meses
df[(df['Descricao'].str.contains('cozinheiro', case=False)) & (df['meses'] >= 6)]

Pergunta: cozinheiros empresa X com 3 meses
df[
 (df['Descricao'].str.contains('cozinheiro', case=False)) &
 (df['RazaoSocial'].str.contains('empresa x', case=False)) &
 (df['meses'] >= 3)
]

Pergunta: atendentes em 2025 com até 2 meses
df[
 (df['Descricao'].str.contains('atendente', case=False)) &
 (df['DataAdmissao'].dt.year == 2025) &
 (df['meses'] <= 2)
]

Pergunta: quantas pessoas empresa X em 2025
df[
 (df['RazaoSocial'].str.contains('empresa x', case=False)) &
 (df['DataAdmissao'].dt.year == 2025)
]['Nome'].nunique()


Colunas do dataframe: 
     - 'Nome': nome do colaborador 
     - 'DataAdmissao': data de saída da empresa
     - 'DataDemissao' : data de entrada na empresa
     - 'Email' : email para contato com colaborador
     - 'Celular': celular para contato com colaborador
     - 'CodigoFuncao'
     - 'Descricao' : cargo 
     - 'CodigoCliente'
     - 'RazaoSocial': empresa

========================
EXTRAÇÃO DE TEMPO
========================
- "1 ano" → 12 meses
- "6 meses" → 6
- se não informado → 0

========================
MEMÓRIA DE CARGO (IMPORTANTE)
========================

Se o usuário já escolheu um cargo anteriormente na conversa:

- NÃO pergunte novamente
- reutilize o cargo escolhido

Considere como escolha de cargo quando o usuário responder com:
- nome do cargo
- ou uma das opções listadas anteriormente

Exemplo:

Assistente:
"Encontrei:
- cozinheiro i
- cozinheiro ii
Qual deseja?"

Usuário:
"cozinheiro ii"

→ A partir daqui, usar "cozinheiro ii" até que ele cite outro cargo.


"""),
    MessagesPlaceholder(variable_name="chat_history"),
    ("user", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad")
])

memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

agent = create_openai_functions_agent(llm, tools, prompt)

agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    memory=memory,
    verbose=True,
    handle_parsing_errors=True,
    # ALTERAÇÃO: Habilitar o retorno dos passos intermediários
    return_intermediate_steps=True
)



# --- FUNÇÃO PRINCIPAL DE PROCESSAMENTO E LOG ---

def processar_pergunta(pergunta: str, chat_history: list = None) -> str:
    """
    Recebe uma pergunta, executa o agente, salva um log detalhado em JSON
    e retorna a resposta final para o usuário.
    """
    global ultimo_grafico_base64
    ultimo_grafico_base64 = None  # IMPORTANTE: Limpar antes de processar

    global ultimo_pdf_base64
    ultimo_pdf_base64 = None

    
    entrada = {"input": pergunta}
    if chat_history:
        entrada["chat_history"] = chat_history

    log_data = {
        "timestamp": datetime.datetime.now().isoformat(),
        "pergunta_usuario": pergunta,
        "historico_usado": [
            {"type": msg.type, "content": msg.content} for msg in (chat_history or [])
        ],
    }
    
    resposta_para_usuario = ""

    try:
        # Usar o callback para capturar custos e tokens 
        with get_openai_callback():
            resposta_agente = agent_executor.invoke(entrada)

        # Formatar os passos intermediários para o log
        passos_formatados = []
        for step in resposta_agente.get("intermediate_steps", []):
            action, observation = step
            passos_formatados.append({
                "ferramenta": action.tool,
                "input_ferramenta": action.tool_input,
                "log_agente": action.log,
                "output_ferramenta": observation,
            })

        # Preencher o resto do log com dados de sucesso
        log_data.update({
            "status": "sucesso",
            "resposta_final_agente": resposta_agente.get("output"),
            "passos_intermediarios": passos_formatados,
        })
        resposta_para_usuario = resposta_agente.get("output")
        
        # Se foi criado um gráfico, adicionar o base64 na resposta
        if ultimo_grafico_base64:
            resposta_para_usuario += f"\nGRAFICO_BASE64:{ultimo_grafico_base64}"
            ultimo_grafico_base64 = None  # Limpar após usar

        if ultimo_pdf_base64:
            resposta_para_usuario += f"\nPDF_BASE64:{ultimo_pdf_base64}"
            ultimo_pdf_base64 = None

    except Exception as e:
        ultimo_grafico_base64 = None  # Limpar em caso de erro também
        ultimo_pdf_base64 = None
        # Guarda erro
        log_data.update({
            "status": "erro",
            "erro_mensagem": str(e),
            "erro_traceback": traceback.format_exc(),
        })
        resposta_para_usuario = "Ocorreu um erro ao processar sua solicitação."
        print(f"ERRO NO AGENTE: {e}") 

    finally:
        # Escrever o log 
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_data, ensure_ascii=False, indent=2) + "\n")

    return resposta_para_usuario