import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import os
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# --- CONFIGURACIÓN DE LA LLAVE ---
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("❌ Error: No se encuentra la API Key en los Secrets.")
    st.stop()

st.set_page_config(page_title="Psicobot", page_icon="🧠")

# --- LECTURA DE DOCUMENTOS ---
@st.cache_resource
def cargar_informacion():
    texto_total = ""
    # Asegúrate de que estos nombres coincidan EXACTO con GitHub
    archivos = ["Doc1base.pdf", "Reunión 2026-1 1.pdf", "Calendario semi.pdf"]
    for nombre in archivos:
        if os.path.exists(nombre):
            try:
                doc = fitz.open(nombre)
                for pagina in doc:
                    texto_total += pagina.get_text() + " "
                doc.close()
            except:
                continue
    return texto_total.strip()

# --- INTERFAZ ---
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)

st.markdown("<h1 style='text-align: center;'>🧠 Psicobot</h1>", unsafe_allow_html=True)

contenido_contexto = cargar_informacion()

# --- LÓGICA DE RESPUESTA ---
pregunta = st.text_input("¿En qué puedo ayudarte?", placeholder="Escribe aquí...")

if st.button("Consultar"):
    if pregunta:
        with st.spinner("Psicobot está analizando..."):
            try:
                # --- SOLUCIÓN AL ERROR 404 ---
                # Buscamos dinámicamente el nombre del modelo disponible
                modelos_disponibles = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                # Priorizamos gemini-1.5-flash, si no, usamos el primero que funcione
                nombre_modelo = "models/gemini-1.5-flash" if "models/gemini-1.5-flash" in modelos_disponibles else modelos_disponibles[0]
                
                model = genai.GenerativeModel(nombre_modelo)
                
                filtros_paz = {
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                }

                if not contenido_contexto:
                    prompt = f"Eres Psicobot, asistente amable de psicología. Responde: {pregunta}"
                else:
                    prompt = f"Eres Psicobot. Usa esta info: {contenido_contexto[:30000]}\n\nPregunta: {pregunta}"

                response = model.generate_content(prompt, safety_settings=filtros_paz)
                
                if response.text:
                    st.markdown("### 📝 Respuesta:")
                    st.info(response.text)
                else:
                    st.warning("No se pudo generar respuesta.")

            except Exception as e:
                st.error(f"Fallo de conexión con la IA: {str(e)}")
    else:
        st.warning("Por favor, escribe una pregunta.")

st.markdown("---")
st.caption("Psicobot v1.3 - Conexión Adaptativa")
