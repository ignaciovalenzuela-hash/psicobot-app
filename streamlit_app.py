import streamlit as st
import google.generativeai as genai
import fitz  # Para los PDFs (PyMuPDF)
import pandas as pd  # Para el Excel
import os
import unicodedata
import datetime  # Mantiene la noción del tiempo real

# --- 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS VISUALES PERSONALIZADOS (CSS) ---
st.set_page_config(page_title="Psicobot", page_icon="🧠", layout="centered")

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    .titulo-psicobot {
        background: linear-gradient(45deg, #cc609b, #ff89c9);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        font-weight: 800;
        font-size: 3.2rem;
        margin-bottom: 0rem;
    }

    .online-indicator {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 8px;
        color: #555;
        font-size: 0.95rem;
        margin-top: -5px;
        margin-bottom: 25px;
        font-weight: 500;
    }
    .dot {
        height: 10px;
        width: 10px;
        background-color: #ff89c9;
        border-radius: 50%;
        display: inline-block;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0% { transform: scale(0.9); box-shadow: 0 0 0 0 rgba(255, 137, 201, 0.7); }
        70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(255, 137, 201, 0); }
        100% { transform: scale(0.9); box-shadow: 0 0 0 0 rgba(255, 137, 201, 0); }
    }

    .welcome-card {
        background-color: #ffffff;
        border-left: 5px solid #cc609b;
        padding: 18px;
        border-radius: 8px;
        box-shadow: 0px 4px 15px rgba(0, 0, 0, 0.05);
        margin-bottom: 15px;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    .welcome-card:hover {
        transform: translateY(-3px);
        box-shadow: 0px 8px 20px rgba(204, 96, 155, 0.15);
        border-left: 5px solid #ff89c9;
    }
    .welcome-card h4 {
        color: #cc609b;
        margin-top: 0;
        margin-bottom: 8px;
        font-weight: 700;
    }
    .welcome-card p {
        color: #444444;
        font-size: 0.92rem;
        margin: 0;
    }
</style>
""", unsafe_allow_html=True)

# --- FUNCIONES DE LIMPIEZA Y FORMATO ---
def normalizar_columna(col):
    col = str(col).strip().upper()
    return ''.join(ch for ch in unicodedata.normalize('NFD', col) if unicodedata.category(ch) != 'Mn')

def convertir_df_a_markdown(df):
    columnas = df.columns.tolist()
    md = "|" + "|".join(columnas) + "|\n"
    md += "|" + "|".join(["---"] * len(columnas)) + "|\n"
    for _, fila in df.iterrows():
        valores = [str(val).strip() if pd.notna(val) else "" for val in fila.values]
        md += "|" + "|".join(valores) + "|\n"
    return md

# --- 2. LOGO Y ENCABEZADO ---
col1, col2, col3 = st.columns([1, 1.2, 1])
with col2:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    else:
        st.caption("🧠 Psicobot en línea")

st.markdown("<h1 class='titulo-psicobot'>Psicobot</h1>", unsafe_allow_html=True)
st.markdown("<div class='online-indicator'><span class='dot'></span> Asistente Oficial Activo</div>", unsafe_allow_html=True)
st.markdown("---")

# --- 3. CONFIGURACIÓN DE API ---
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("Error: Configura la API Key en los Secrets de Streamlit.")
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 4. CONFIGURACIÓN DEL MODELO ---
nombre_modelo_oficial = 'models/gemini-2.5-flash'

# --- 5. CARGA AUTOMÁTICA DE DOCUMENTOS ---
@st.cache_resource(show_spinner=False)
def cargar_documentos():
    texto_total = ""
    archivos_procesados =
