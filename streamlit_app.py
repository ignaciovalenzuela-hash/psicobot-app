import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import os

# Configurar API Key desde los secretos de Streamlit
api_key = st.secrets["GOOGLE_API_KEY"]
genai.configure(api_key=api_key)

st.set_page_config(page_title="Psicobot", page_icon="🧠")

# Título y Logo
st.markdown("<h1 style='text-align: center;'>🧠 Psicobot</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'>Asistente Virtual de la Facultad de Psicología</p>", unsafe_allow_html=True)
st.markdown("---")

# Función para leer PDFs
def leer_pdfs():
    texto = ""
    archivos = ["Doc1base.pdf", "Reunión 2026-1 1.pdf", "Calendario semi.pdf"]
    for a in archivos:
        if os.path.exists(a):
            doc = fitz.open(a)
            for p in doc: texto += p.get_text()
    return texto

contexto = leer_pdfs()

pregunta = st.text_input("Haz tu consulta:", placeholder="¿En qué puedo ayudarte?")
if st.button("Consultar"):
    if pregunta:
        with st.spinner("Analizando..."):
            model = genai.GenerativeModel("gemini-1.5-flash")
            prompt = "Eres Psicobot, asistente oficial. Responde amable y profesional. No menciones archivos PDF."
            res = model.generate_content(f"{prompt}\n\nContexto:\n{contexto}\n\nPregunta: {pregunta}")
            st.info(res.text)
