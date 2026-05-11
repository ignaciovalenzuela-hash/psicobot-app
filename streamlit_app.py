import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import os

# Configurar API Key desde los secretos de Streamlit
api_key = st.secrets["GOOGLE_API_KEY"]
genai.configure(api_key=api_key)

st.set_page_config(page_title="Psicobot", page_icon="🧠")

# --- DISEÑO: LOGO Y TÍTULO ---
# Usamos columnas para centrar el logo
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    # IMPORTANTE: Aquí corregimos la ruta del logo
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    else:
        st.info("Cargando logo...")

st.markdown("<h1 style='text-align: center;'>🧠 Psicobot</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'>Asistente Virtual de la Facultad de Psicología</p>", unsafe_allow_html=True)
st.markdown("---")

# Función para leer PDFs
def leer_pdfs():
    texto = ""
    # Nombres exactos de los archivos que subiste a GitHub
    archivos = ["Doc1base.pdf", "Reunión 2026-1 1.pdf", "Calendario semi.pdf"]
    for a in archivos:
        if os.path.exists(a):
            try:
                doc = fitz.open(a)
                for p in doc:
                    texto += p.get_text()
            except:
                continue
    return texto

contexto = leer_pdfs()

if contexto:
    pregunta = st.text_input("Haz tu consulta:", placeholder="¿En qué puedo ayudarte?")
    if st.button("Consultar"):
        if pregunta:
            with st.spinner("Psicobot está analizando los documentos..."):
                try:
                    model = genai.GenerativeModel("gemini-1.5-flash")
                    prompt = (
                        "Eres Psicobot, el asistente oficial de la Facultad de Psicología. "
                        "Responde de forma amable, empática y profesional. "
                        "Usa solo la información de los documentos proporcionados. "
                        "REGLA CRÍTICA: No menciones PDFs ni nombres de archivos."
                    )
                    res = model.generate_content(f"{prompt}\n\nContexto:\n{contexto}\n\nPregunta: {pregunta}")
                    st.info(res.text)
                except:
                    st.error("Hubo un problema al conectar con la IA.")
else:
    st.error("⚠️ No se detectan los archivos PDF en el repositorio de GitHub.")
