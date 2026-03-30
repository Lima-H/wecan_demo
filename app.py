import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
from modelo import processar_pergunta
import base64
import re

# =============================
# Chatbot - funções auxiliares
# =============================

def corrigir_formatacao_moeda(texto):  
    texto = re.sub(r'R(\d+,\d+)', r'R$ \1', texto)  
    texto = re.sub(r'R (\d+,\d+)', r'R$ \1', texto)  
    return texto  

def exibir_mensagem(content):  
    if "GRAFICO_BASE64:" in content:  
        partes = content.split("GRAFICO_BASE64:")  
        texto = partes[0].strip()  
    else:
        texto = content.strip()

    # 🔥 NOVO: detectar lista de candidatos
    linhas = texto.split("\n")
    
    if all("|" in l for l in linhas if l.strip()):
        st.markdown("### 👥 Resultados encontrados")
        
        for l in linhas:
            partes = l.split("|")
            if len(partes) >= 4:
                nome, meses, empresa, telefone = [p.strip() for p in partes]

                st.markdown(f"""
                <div style="
                    background:#1a1d26;
                    border:1px solid #2e3140;
                    border-radius:8px;
                    padding:10px;
                    margin-bottom:6px;
                ">
                    <b>{nome}</b><br>
                    ⏳ {meses} <br>
                    🏢 {empresa} <br>
                    📱 {telefone}
                </div>
                """, unsafe_allow_html=True)
        return

    # padrão
    content_corrigido = corrigir_formatacao_moeda(texto)
    st.markdown(content_corrigido, unsafe_allow_html=True)



# =============================
# Estado do chatbot
# =============================

if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "assistant", "content": "Como posso ajudar você?"}
    ]

if "processing" not in st.session_state:
    st.session_state["processing"] = False


st.set_page_config(
    page_title="Recontratação de Colaboradores",
    page_icon="👥",
    layout="wide"
)

# =============================
# Sidebar - Chatbot
# =============================

with st.sidebar:
    st.markdown("## 🤖 Chatbot")
    
    with st.expander("Abrir chat", expanded=True):

        # Histórico
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                exibir_mensagem(msg["content"])

        # Indicador de processamento
        if st.session_state.processing:
            with st.chat_message("assistant"):
                with st.spinner("Processando..."):
                    st.write("Analisando os dados...")

        # Input
        if prompt := st.chat_input("Digite sua pergunta...", disabled=st.session_state.processing):
            
            st.session_state.processing = True
            
            st.session_state.messages.append({
                "role": "user",
                "content": prompt
            })

            with st.chat_message("user"):
                st.write(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Processando..."):
                    resposta = processar_pergunta(prompt)

            st.session_state.messages.append({
                "role": "assistant",
                "content": resposta
            })

            st.session_state.processing = False
            st.rerun()


# =============================
# Estilo visual customizado
# =============================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@300;400;500;600&display=swap');

/* =============================
BASE
============================= */

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #0f1117 !important;
}

/* Fundo geral */
.stApp {
    background-color: #0f1117;
    color: #e8e3d8;
}

/* =============================
REMOVE TOPO BRANCO (Streamlit)
============================= */

header {
    background: transparent !important;
}

[data-testid="stHeader"] {
    background: transparent !important;
}

[data-testid="stToolbar"] {
    background: transparent !important;
}

[data-testid="stMainBlockContainer"] {
    padding-top: 0rem !important;
}

[data-testid="stMainBlockContainer"] > div:first-child {
    background-color: #0f1117 !important;
}


/* =============================
EXPANDER (CHAT MAIS CLARO)
============================= */

[data-testid="stExpander"] {
    background-color: #2c3145 !important;
    border: 1px solid #2c3145 !important;
    border-radius: 10px !important;
}

/* HEADER "Abrir chat" */
[data-testid="stExpander"] > div:first-child {
    background-color: #252a3a !important;
    border-radius: 10px !important;
}

/* Texto */
[data-testid="stExpander"] summary {
    background-color: transparent !important;
    color: #f5c842 !important;
    font-weight: 600;
}

/* Hover */
[data-testid="stExpander"] summary:hover {
    color: #ffd95a !important;
}

/*  CONTAINER REAL DO CHAT */
[data-testid="stExpanderContent"] > div {
    background-color: #2c3145 !important;
    padding: 12px !important;
    border-radius: 10px !important;
}


/* =============================
TEXTO SEMPRE BRANCO NO CHAT
============================= */

[data-testid="stChatMessage"],
[data-testid="stChatMessage"] * {
    color: #ffffff !important;
}


/* =============================
CHAT (mensagens MAIS CLARAS)
============================= */

[data-testid="stChatMessage"] {
    background-color: #32384d !important;
    border: 1px solid #3f4455 !important;
    border-radius: 10px !important;
    padding: 0.6rem 0.8rem !important;
    margin-bottom: 0.5rem !important;
}

/* texto */
[data-testid="stChatMessage"] p {
    color: #f1ede4 !important;
}

/* USER */
[data-testid="stChatMessage"][data-testid*="user"] {
    background-color: #3a4055 !important;
}

/* ASSISTANT */
[data-testid="stChatMessage"][data-testid*="assistant"] {
    background-color: #32384d !important;
}


/* =============================
INPUT DO CHAT 
============================= */

/* container do input */
[data-testid="stChatInput"] {
    background-color: #2c3145 !important;
    border-top: 1px solid #3f4455 !important;
    padding-top: 8px;
}

/* textarea */
[data-testid="stChatInput"] textarea {
    background-color: #3a4055 !important;
    color: #e8e3d8 !important;
    border: 1px solid #4a5166 !important;
    border-radius: 12px !important;
    padding: 10px !important;
}


/* =============================
HEADER PRINCIPAL
============================= */

.main-header {
    padding: 2.5rem 0 1rem 0;
    border-bottom: 1px solid #2a2d35;
    margin-bottom: 2rem;
}

.main-title {
    font-family: 'DM Serif Display', serif;
    font-size: 2.4rem;
    color: #f5c842;
    margin: 0;
    letter-spacing: -0.5px;
}

.main-subtitle {
    font-size: 0.95rem;
    color: #6b7280;
    margin-top: 0.3rem;
    font-weight: 300;
}

/* =============================
CARDS E INPUTS
============================= */

.filter-card {
    background: #161820;
    border: 1px solid #23262f;
    border-radius: 14px;
    padding: 1.6rem 2rem;
    margin-bottom: 1.4rem;
}

.filter-card-title {
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #f5c842;
    margin-bottom: 1rem;
}

.stSelectbox label,
.stNumberInput label {
    color: #9ca3af !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
}

.stSelectbox > div > div,
.stNumberInput > div > div > input {
    background-color: #1e2028 !important;
    border: 1px solid #2e3140 !important;
    border-radius: 8px !important;
    color: #e8e3d8 !important;
}

.stSelectbox > div > div:focus-within,
.stNumberInput > div > div:focus-within {
    border-color: #f5c842 !important;
    box-shadow: 0 0 0 2px rgba(245, 200, 66, 0.15) !important;
}

/* =============================
OUTROS
============================= */

hr {
    border-color: #23262f !important;
    margin: 1.8rem 0 !important;
}

.stDataFrame {
    border-radius: 10px !important;
    overflow: hidden;
}

.result-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    background: rgba(245, 200, 66, 0.1);
    border: 1px solid rgba(245, 200, 66, 0.3);
    color: #f5c842;
    font-size: 0.85rem;
    font-weight: 600;
    padding: 0.45rem 1rem;
    border-radius: 999px;
    margin-bottom: 1rem;
}

.stAlert {
    background-color: #1a1c25 !important;
    border-color: #2e3140 !important;
    color: #9ca3af !important;
}

.section-title {
    font-family: 'DM Serif Display', serif;
    font-size: 1.35rem;
    color: #e8e3d8;
    margin-bottom: 0.5rem;
}

.metric-row {
    display: flex;
    gap: 1rem;
    margin-bottom: 1.5rem;
}

.metric-box {
    background: #161820;
    border: 1px solid #23262f;
    border-radius: 10px;
    padding: 1rem 1.4rem;
    flex: 1;
    text-align: center;
}

.metric-value {
    font-family: 'DM Serif Display', serif;
    font-size: 1.8rem;
    color: #f5c842;
    line-height: 1;
}

.metric-label {
    font-size: 0.75rem;
    color: #6b7280;
    margin-top: 0.3rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}
            
/* =============================
SIDEBAR 
============================= */

[data-testid="stSidebar"] {
    background-color: rgba(15,17,23,0.95) !important; /* mesma cor do chat */
    color: #ffffff !important;
}

[data-testid="stSidebar"] * {
    color: #ffffff !important;
}

[data-testid="stSidebarNav"] {
    background-color: rgba(15,17,23,0.95) !important;
}

[data-testid="stSidebarNav"] a, 
[data-testid="stSidebarNav"] div {
    color: #ffffff !important;
}

""", unsafe_allow_html=True)


# =============================
# Header
# =============================

st.markdown("""
<div class="main-header">
    <p class="main-title">👥 Recontratação de Colaboradores</p>
    <p class="main-subtitle">Identifique ex-colaboradores elegíveis para retorno com base em critérios de permanência e recência</p>
</div>
""", unsafe_allow_html=True)

# =============================
# Carregar dados
# =============================

dicionario_colunas = {
    "DataAdmissao": "data_admissao",
    "DataDemissao": "data_demissao",
    "RazaoSocial": "empresa",
    "Descricao": "cargo",
    "Nome": "nome",
    "Celular": "telefone",
    "Email": "email"
}

@st.cache_data
def load_data():
    df = pd.read_excel("dados/sapore_funcionario.xlsx")
    df.rename(columns=dicionario_colunas, inplace=True)
    df.columns = df.columns.str.lower().str.strip()
    df["data_admissao"] = pd.to_datetime(df["data_admissao"])
    df["data_demissao"] = pd.to_datetime(df["data_demissao"], errors="coerce")
    return df

df = load_data()

# =============================
# Cálculo do tempo trabalhado
# =============================

def calcular_meses_trabalhados(row):
    data_inicio = row["data_admissao"]
    data_fim = row["data_demissao"]
    if pd.isna(data_fim):
        data_fim = datetime.today()
    diff = relativedelta(data_fim, data_inicio)
    return diff.years * 12 + diff.months

df["meses_trabalhados"] = df.apply(calcular_meses_trabalhados, axis=1)

# =============================
# Filtro 1 — Empresa (isolado no topo)
# =============================

# st.markdown('<div class="filter-card">', unsafe_allow_html=True)
st.markdown('<p class="filter-card-title">🏢 Empresa</p>', unsafe_allow_html=True)
empresa = st.selectbox(
    "Selecione a empresa",
    sorted(df["empresa"].dropna().unique()),
    label_visibility="collapsed"
)
st.markdown('</div>', unsafe_allow_html=True)

# =============================
# Filtros 2, 3, 4 — Cargo + Parâmetros
# =============================

df_empresa = df[df["empresa"] == empresa]

# st.markdown('<div class="filter-card">', unsafe_allow_html=True)
st.markdown('<p class="filter-card-title">🎯 Critérios de Busca</p>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    cargo = st.selectbox(
        "💼 Cargo",
        sorted(df_empresa["cargo"].dropna().unique())
    )

with col2:
    min_meses = st.number_input(
        "📅 Permanência mínima (meses)",
        min_value=0,
        value=6
    )

with col3:
    ultimos_anos = st.number_input(
        "🕐 Saída há no máximo (anos)",
        min_value=0,
        value=2
    )

st.markdown('</div>', unsafe_allow_html=True)

# =============================
# Aplicar filtros
# =============================

df_filtrado = df[
    (df["empresa"] == empresa) &
    (df["cargo"] == cargo) &
    (df["meses_trabalhados"] >= min_meses)
]

if ultimos_anos > 0:
    limite_data = datetime.today() - relativedelta(years=ultimos_anos)
    df_filtrado = df_filtrado[df_filtrado["data_demissao"] >= limite_data]

# =============================
# Resultado
# =============================

st.markdown("---")

st.markdown('<p class="section-title">📋 Possíveis Recontratações</p>', unsafe_allow_html=True)

if df_filtrado.empty:
    st.warning("⚠️ Nenhum colaborador encontrado com os critérios selecionados. Tente ampliar os parâmetros de busca.")
else:
    total = len(df_filtrado)
    media_meses = int(df_filtrado["meses_trabalhados"].mean())
    max_meses = int(df_filtrado["meses_trabalhados"].max())

    # Métricas rápidas
    st.markdown(f"""
    <div class="metric-row">
        <div class="metric-box">
            <div class="metric-value">{total}</div>
            <div class="metric-label">Colaboradores encontrados</div>
        </div>
        <div class="metric-box">
            <div class="metric-value">{media_meses}</div>
            <div class="metric-label">Média de meses trabalhados</div>
        </div>
        <div class="metric-box">
            <div class="metric-value">{max_meses}</div>
            <div class="metric-label">Máx. meses trabalhados</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    resultado = df_filtrado[
        ["nome", "telefone", "email", "meses_trabalhados", "data_demissao"]
    ].rename(columns={
        "nome": "👤 Nome",
        "telefone": "📱 Telefone",
        "email": "✉️ E-mail",
        "meses_trabalhados": "📅 Meses trabalhados",
        "data_demissao": "🗓️ Data de saída"
    }).sort_values(by="📅 Meses trabalhados", ascending=False)

    resultado["🗓️ Data de saída"] = pd.to_datetime(resultado["🗓️ Data de saída"]).dt.strftime("%d/%m/%Y")

    st.dataframe(
        resultado,
        use_container_width=True,
        hide_index=True,
    )