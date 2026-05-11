import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import os
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# 1. Configuración de API Key
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("Falta la clave GOOGLE_API_KEY en los Secrets.")

st.set_page_config(page_title="Psicobot", page_icon="🧠")

# 2. Carga de Texto
@st.cache_resource
def obtener_contexto_final():
    texto_acumulado = ""
    archivos = ["Doc1base.pdf", "Reunión 2026-1 1.pdf", "Calendario semi.pdf"]
    for nombre in archivos:
        if os.path.exists(nombre):
            try:
                doc = fitz.open(nombre)
                for pagina in doc:
                    texto_acumulado += pagina.get_text() + "\n"
                doc.close()
            except: continue
    return texto_acumulado if texto_acumulado else None

# --- INTERFAZ ---
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)

st.markdown("<h1 style='text-align: center;'>🧠 Psicobot</h1>", unsafe_allow_html=True)
st.markdown("---")

contexto = obtener_contexto_final()

if contexto:
    pregunta = st.text_input("Haz tu consulta:", placeholder="Escribe aquí...")
    
    if st.button("Preguntar"):
        if pregunta:
            with st.spinner("Psicobot está analizando..."):
                try:
                    model = genai.GenerativeModel("gemini-1.5-flash")
                    
                    # --- EL CAMBIO CLAVE: DESACTIVAR FILTROS ---
                    # Esto permite que la IA lea temas de psicología sin bloquearse
                    seguridad = {
                        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                    }
                    
                    prompt = "Eres Psicobot, asistente oficial. Responde usando este contexto:\n"
                    
                    response = model.generate_content(
                        f"{prompt}\n{contexto}\n\nPregunta: {pregunta}",
                        safety_settings=seguridad
                    )
                    
                    if response.text:
                        st.success(response.text)
                    else:
                        st.warning("La IA bloqueó la respuesta por políticas de seguridad. Intenta preguntar de otra forma.")
                        
                except Exception as e:
                    st.error(f"Error: {str(e)}")
else:
    st.error("No se encuentran los archivos en GitHub.")
