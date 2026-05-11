import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import os
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# --- CONFIGURACIÓN DE LA LLAVE ---
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("Falta la API Key en Secrets.")
    st.stop()

st.set_page_config(page_title="Psicobot", page_icon="🧠")

# --- LECTURA DE DOCUMENTOS ---
@st.cache_resource(show_spinner=False)
def cargar_informacion():
    texto_total = ""
    archivos = [
        "Doc1base.pdf", "Reunión 2026-1 1.pdf", "Calendario semi.pdf",
        "Documento informativo carrera de psicología.pdf",
        "Preguntas Frecuentes Cierre Seminario.pdf",
        "Calendario 1er semestre 2026-1.pdf", "Calendario 2do semestre 2026-1.pdf",
        "Calendario 3er semestre 2026-1.pdf", "Calendario 4to semestre 2026-1.pdf",
        "Calendario 5to semestre 2026-1.pdf", "Calendario 6to semestre 2026-1.pdf",
        "Calendario 7mo semestre 2026-1.pdf", "Calendario 8vo semestre 2026-1.pdf",
        "Calendario 9no semestre 2026-1.pdf", "Calendario 10mo semestre 2026-1.pdf"
    ]
    
    for nombre in archivos:
        if os.path.exists(nombre):
            try:
                with fitz.open(nombre) as doc:
                    for pagina in doc:
                        texto_total += f"\n[DOC: {nombre}]\n{pagina.get_text()}\n"
            except: continue
    return texto_total

# --- INTERFAZ ---
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)

st.markdown("<h1 style='text-align: center;'>🧠 Psicobot</h1>", unsafe_allow_html=True)

contexto = cargar_informacion()

pregunta = st.text_input("¿Qué deseas consultar?", placeholder="Ej: Fechas de exámenes 2026")

if st.button("Consultar"):
    if pregunta:
        with st.spinner("Estableciendo conexión segura..."):
            try:
                # PASO 1: Listar modelos disponibles REALES
                modelos_reales = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                
                if not modelos_reales:
                    st.error("No se encontraron modelos disponibles en tu cuenta de Google AI.")
                    st.stop()
                
                # PASO 2: Intentar usar Flash, si no, el primero de la lista
                seleccionado = next((m for m in modelos_reales if "flash" in m), modelos_reales[0])
                model = genai.GenerativeModel(seleccionado)

                # PASO 3: Generación de respuesta
                safety = {
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                }

                instrucciones = (
                    "Eres Psicobot. Responde con precisión académica basándote en los documentos.\n"
                    "Cita artículos de reglamentos (Art. X).\n"
                    "Diferencia clases Presenciales de Online.\n"
                    "No menciones que lees archivos."
                )

                prompt = f"{instrucciones}\n\nDATOS:\n{contexto[:40000]}\n\nPREGUNTA: {pregunta}"
                
                response = model.generate_content(prompt, safety_settings=safety)
                
                if response.text:
                    st.markdown("---")
                    st.markdown(response.text)
                else:
                    st.warning("La IA no generó texto. Intenta de nuevo.")

            except Exception as e:
                st.error(f"Error crítico de sistema: {str(e)}")
    else:
        st.warning("Escribe una pregunta.")

st.markdown("---")
st.caption("Psicobot v2.0 - Auto-Configuración Activa")
