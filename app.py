import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
from modelo import processar_pergunta, ultimo_pdf_base64
import base64
import re
import uuid

# =============================
# Chatbot - funções auxiliares
# =============================

def corrigir_formatacao_moeda(texto):
    texto = re.sub(r'R(\d+,\d+)', r'R$ \1', texto)
    texto = re.sub(r'R (\d+,\d+)', r'R$ \1', texto)
    return texto

def exibir_mensagem(content):
    pdf_base64 = None

    if "PDF_BASE64:" in content:
        partes = content.split("PDF_BASE64:")
        texto = partes[0].strip()
        pdf_base64 = partes[1].strip()
    elif "GRAFICO_BASE64:" in content:
        partes = content.split("GRAFICO_BASE64:")
        texto = partes[0].strip()
    else:
        texto = content.strip()

    linhas = [l for l in texto.split("\n") if l.strip()]

    if linhas and all("|" in l for l in linhas):
        st.markdown("**Resultados encontrados**")
        for l in linhas:
            if l.strip().startswith("(") or "colaborador" in l.lower():
                st.markdown(f'<p style="font-size:12px;color:var(--color-text-secondary);margin:8px 0 0;">{l.strip()}</p>', unsafe_allow_html=True)
                continue
            partes = l.split("|")
            if len(partes) >= 4:
                nome, meses, empresa, telefone = [p.strip() for p in partes[:4]]
                st.markdown(f"""
                <div style="
                    background: var(--color-background-secondary);
                    border: 0.5px solid var(--color-border-secondary);
                    border-left: 2px solid #7F77DD;
                    border-radius: 8px;
                    padding: 10px 14px;
                    margin-bottom: 6px;
                ">
                    <p style="font-weight:500;font-size:14px;margin:0 0 4px;color:var(--color-text-primary);">{nome}</p>
                    <p style="font-size:12px;margin:0;color:var(--color-text-secondary);">
                        {meses} &nbsp;·&nbsp; {empresa} &nbsp;·&nbsp; {telefone}
                    </p>
                </div>
                """, unsafe_allow_html=True)
        if pdf_base64:
            pdf_bytes = base64.b64decode(pdf_base64)
            st.download_button(
                label="Baixar PDF",
                data=pdf_bytes,
                file_name="colaboradores.pdf",
                mime="application/pdf",
                key=f"dl_{uuid.uuid4()}"
            )
        return

    content_corrigido = corrigir_formatacao_moeda(texto)
    st.markdown(content_corrigido, unsafe_allow_html=True)

    if pdf_base64:
        pdf_bytes = base64.b64decode(pdf_base64)
        st.download_button(
            label="Baixar PDF",
            data=pdf_bytes,
            file_name="colaboradores.pdf",
            mime="application/pdf",
            key=f"dl_{uuid.uuid4()}"
        )

# =============================
# Estado do chatbot
# =============================

if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "assistant", "content": "Olá! Como posso ajudar com a recontratação hoje?"}
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
    st.markdown("""
    <div style="padding: 1.2rem 0 0.8rem;">
        <p style="font-size:11px;font-weight:500;letter-spacing:0.1em;text-transform:uppercase;
                  color:var(--color-text-secondary);margin:0 0 4px;">Assistente</p>
        <p style="font-size:18px;font-weight:500;margin:0;color:var(--color-text-primary);">Chat RH</p>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("Abrir conversa", expanded=True):
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                exibir_mensagem(msg["content"])

        if st.session_state.processing:
            with st.chat_message("assistant"):
                with st.spinner("Analisando..."):
                    st.write("Processando sua pergunta...")

        if prompt := st.chat_input("Pergunte algo...", disabled=st.session_state.processing):
            st.session_state.processing = True
            st.session_state.messages.append({"role": "user", "content": prompt})

            with st.chat_message("user"):
                st.write(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Processando..."):
                    resposta = processar_pergunta(prompt)

            st.session_state.messages.append({"role": "assistant", "content": resposta})
            st.session_state.processing = False
            st.rerun()

# =============================
# Estilos
# =============================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: #0c0d12 !important;
}

.stApp {
    background-color: #0c0d12;
    color: #e2ddd6;
}

header, [data-testid="stHeader"], [data-testid="stToolbar"] {
    background: transparent !important;
}

[data-testid="stMainBlockContainer"] {
    padding-top: 0rem !important;
}

/* ---- Sidebar ---- */
[data-testid="stSidebar"] {
    background-color: #10121a !important;
    border-right: 0.5px solid #1e2130 !important;
}

[data-testid="stSidebar"] * {
    color: #e2ddd6 !important;
}

/* ---- Expander ---- */
[data-testid="stExpander"] {
    background-color: #181b26 !important;
    border: 0.5px solid #242738 !important;
    border-radius: 10px !important;
}

[data-testid="stExpander"] > div:first-child {
    background-color: #181b26 !important;
    border-radius: 10px !important;
}

[data-testid="stExpander"] summary {
    background-color: transparent !important;
    color: #a9a4ff !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    letter-spacing: 0.02em;
}

[data-testid="stExpanderContent"] > div {
    background-color: #181b26 !important;
    padding: 10px !important;
    border-radius: 8px !important;
}

/* ---- Chat messages ---- */
[data-testid="stChatMessage"] {
    background-color: #1c1f2e !important;
    border: 0.5px solid #252840 !important;
    border-radius: 10px !important;
    padding: 0.55rem 0.8rem !important;
    margin-bottom: 6px !important;
}

[data-testid="stChatMessage"] *,
[data-testid="stChatMessage"] p {
    color: #e2ddd6 !important;
    font-size: 13px !important;
}

/* ---- Chat input ---- */
[data-testid="stChatInput"] {
    background-color: #181b26 !important;
    border-top: 0.5px solid #252840 !important;
    padding-top: 6px;
}

[data-testid="stChatInput"] textarea {
    background-color: #1c1f2e !important;
    color: #e2ddd6 !important;
    border: 0.5px solid #2e3255 !important;
    border-radius: 8px !important;
    font-size: 13px !important;
}

/* ---- Selectbox / NumberInput ---- */
.stSelectbox label, .stNumberInput label {
    color: #8b8fa8 !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}

.stSelectbox > div > div,
.stNumberInput > div > div > input {
    background-color: #14162050 !important;
    border: 0.5px solid #2a2d42 !important;
    border-radius: 8px !important;
    color: #e2ddd6 !important;
    font-size: 14px !important;
}

.stSelectbox > div > div:focus-within,
.stNumberInput > div > div:focus-within {
    border-color: #7F77DD !important;
    box-shadow: 0 0 0 2px rgba(127,119,221,0.15) !important;
}

/* ---- Dataframe ---- */
.stDataFrame {
    border-radius: 10px !important;
    overflow: hidden;
    border: 0.5px solid #1e2130 !important;
}

/* ---- Download button ---- */
[data-testid="stDownloadButton"] button {
    background: #1c1f2e !important;
    border: 0.5px solid #7F77DD !important;
    color: #a9a4ff !important;
    border-radius: 8px !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    padding: 6px 14px !important;
    margin-top: 8px;
}

[data-testid="stDownloadButton"] button:hover {
    background: #252840 !important;
}

/* ---- Divider ---- */
hr {
    border: none !important;
    border-top: 0.5px solid #1e2130 !important;
    margin: 1.5rem 0 !important;
}

/* ---- Warning ---- */
.stAlert {
    background-color: #16192260 !important;
    border: 0.5px solid #2a2d42 !important;
    border-radius: 8px !important;
    color: #8b8fa8 !important;
    font-size: 13px !important;
}

/* ---- Spinner ---- */
[data-testid="stSpinner"] {
    color: #7F77DD !important;
}
</style>
""", unsafe_allow_html=True)

# =============================
# Header
# =============================

st.markdown("""
<div style="padding: 2rem 0 1.5rem; border-bottom: 0.5px solid #1e2130; margin-bottom: 2rem;">
    <p style="
        font-size: 11px;
        font-weight: 500;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #7F77DD;
        margin: 0 0 6px;
    ">Módulo RH</p>
    <h1 style="
        font-family: 'Inter', sans-serif;
        font-size: 26px;
        font-weight: 500;
        color: #e2ddd6;
        margin: 0 0 6px;
        letter-spacing: -0.3px;
    ">Recontratação de Colaboradores</h1>
    <p style="
        font-size: 13px;
        color: #5a5e78;
        margin: 0;
        font-weight: 400;
    ">Identifique ex-colaboradores elegíveis para retorno com base em permanência e recência</p>
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
# Filtros
# =============================

st.markdown("""
<p style="font-size:11px;font-weight:500;letter-spacing:0.1em;text-transform:uppercase;
          color:#5a5e78;margin:0 0 10px;">Empresa</p>
""", unsafe_allow_html=True)

empresa = st.selectbox(
    "Selecione a empresa",
    sorted(df["empresa"].dropna().unique()),
    label_visibility="collapsed"
)

st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)

st.markdown("""
<p style="font-size:11px;font-weight:500;letter-spacing:0.1em;text-transform:uppercase;
          color:#5a5e78;margin:0 0 10px;">Critérios de busca</p>
""", unsafe_allow_html=True)

df_empresa = df[df["empresa"] == empresa]

col1, col2, col3 = st.columns(3)

with col1:
    cargo = st.selectbox("Cargo", sorted(df_empresa["cargo"].dropna().unique()))

with col2:
    min_meses = st.number_input("Permanência mínima (meses)", min_value=0, value=6)

with col3:
    ultimos_anos = st.number_input("Saída há no máximo (anos)", min_value=0, value=2)

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

st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)

st.markdown("""
<p style="font-size:11px;font-weight:500;letter-spacing:0.1em;text-transform:uppercase;
          color:#5a5e78;margin:0 0 1rem;">Resultados</p>
""", unsafe_allow_html=True)

if df_filtrado.empty:
    st.warning("Nenhum colaborador encontrado com os critérios selecionados. Tente ampliar os parâmetros.")
else:
    total = len(df_filtrado)
    media_meses = int(df_filtrado["meses_trabalhados"].mean())
    max_meses = int(df_filtrado["meses_trabalhados"].max())

    # Métricas
    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown(f"""
        <div style="background:#14162050;border:0.5px solid #1e2130;border-radius:10px;padding:1rem 1.2rem;">
            <p style="font-size:11px;text-transform:uppercase;letter-spacing:0.08em;color:#5a5e78;margin:0 0 6px;">Encontrados</p>
            <p style="font-size:28px;font-weight:500;color:#a9a4ff;margin:0;line-height:1;">{total}</p>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div style="background:#14162050;border:0.5px solid #1e2130;border-radius:10px;padding:1rem 1.2rem;">
            <p style="font-size:11px;text-transform:uppercase;letter-spacing:0.08em;color:#5a5e78;margin:0 0 6px;">Média de permanência</p>
            <p style="font-size:28px;font-weight:500;color:#a9a4ff;margin:0;line-height:1;">{media_meses} <span style="font-size:14px;color:#5a5e78;font-weight:400;">meses</span></p>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
        <div style="background:#14162050;border:0.5px solid #1e2130;border-radius:10px;padding:1rem 1.2rem;">
            <p style="font-size:11px;text-transform:uppercase;letter-spacing:0.08em;color:#5a5e78;margin:0 0 6px;">Maior permanência</p>
            <p style="font-size:28px;font-weight:500;color:#a9a4ff;margin:0;line-height:1;">{max_meses} <span style="font-size:14px;color:#5a5e78;font-weight:400;">meses</span></p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)

    resultado = df_filtrado[
        ["nome", "telefone", "email", "meses_trabalhados", "data_demissao"]
    ].rename(columns={
        "nome": "Nome",
        "telefone": "Telefone",
        "email": "E-mail",
        "meses_trabalhados": "Meses trabalhados",
        "data_demissao": "Data de saída"
    }).sort_values(by="Meses trabalhados", ascending=False)

    resultado["Data de saída"] = pd.to_datetime(resultado["Data de saída"]).dt.strftime("%d/%m/%Y")

    st.dataframe(
        resultado,
        use_container_width=True,
        hide_index=True,
    )