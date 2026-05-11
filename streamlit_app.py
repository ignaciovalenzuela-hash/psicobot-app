import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import os
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# --- CONFIGURACIÓN DE LA LLAVE ---
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("❌ Error de configuración en Secrets.")
    st.stop()

st.set_page_config(page_title="Psicobot", page_icon="🧠")

# --- LECTURA MASIVA DE DOCUMENTOS ---
@st.cache_resource(show_spinner=False)
def cargar_informacion():
    texto_total = ""
    # LISTA COMPLETA DE ARCHIVOS
    archivos = [
        "Doc1base.pdf", 
        "Reunión 2026-1 1.pdf", 
        "Calendario semi.pdf",
        "Documento informativo carrera de psicología.pdf",
        "Preguntas Frecuentes Cierre Seminario.pdf",
        "Calendario 1er semestre 2026-1.pdf",
        "Calendario 2do semestre 2026-1.pdf",
        "Calendario 3er semestre 2026-1.pdf",
        "Calendario 4to semestre 2026-1.pdf",
        "Calendario 5to semestre 2026-1.pdf",
        "Calendario 6to semestre 2026-1.pdf",
        "Calendario 7mo semestre 2026-1.pdf",
        "Calendario 8vo semestre 2026-1.pdf",
        "Calendario 9no semestre 2026-1.pdf",
        "Calendario 10mo semestre 2026-1.pdf"
    ]
    
    for nombre in archivos:
        if os.path.exists(nombre):
            try:
                with fitz.open(nombre) as doc:
                    for pagina in doc:
                        texto_total += f"\n[ARCHIVO: {nombre}]\n"
                        texto_total += pagina.get_text("text")
            except:
                continue
    return texto_total.strip()

# --- INTERFAZ ---
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)

st.markdown("<h1 style='text-align: center;'>🧠 Psicobot</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'>Asistente Académico Integral</p>", unsafe_allow_html=True)

contexto_contenido = cargar_informacion()

# --- LÓGICA DE CONSULTA ---
pregunta = st.text_input("¿En qué puedo ayudarte?", placeholder="Consulta sobre fechas de cualquier semestre...")

if st.button("Consultar"):
    if pregunta:
        with st.spinner("Analizando calendarios y reglamentos..."):
            try:
                modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                nombre_modelo = "models/gemini-1.5-flash" if "models/gemini-1.5-flash" in modelos else modelos[0]
                model = genai.GenerativeModel(nombre_modelo)
                
                filtros_seguridad = {
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                }

                instrucciones_sistema = (
                    "Eres Psicobot, el asistente oficial de la Facultad de Psicología. "
                    "Tienes acceso a los calendarios de clases desde 1er a 10mo semestre del año 2026. "
                    "REGLAS:\n"
                    "1. NO menciones que lees archivos o PDFs.\n"
                    "2. Si te preguntan por fechas, identifica primero a qué semestre corresponde la consulta.\n"
                    "3. Cita siempre el número de artículo si respondes sobre reglamentos.\n"
                    "4. Si la información no está en los archivos, indica que no tienes el dato para ese semestre específico."
                )

                prompt_final = f"{instrucciones_sistema}\n\nCONTEXTO:\n{contexto_contenido}\n\nPREGUNTA: {pregunta}"

                response = model.generate_content(prompt_final, safety_settings=filtros_seguridad)
                
                if response.text:
                    st.markdown("---")
                    st.info(response.text)
            except Exception as e:
                st.error("Error de conexión. Intenta nuevamente.")
    else:
        st.warning("Escribe una pregunta.")

st.markdown("---")
st.caption("Psicobot v1.6 - Base de datos completa 2026-1")
