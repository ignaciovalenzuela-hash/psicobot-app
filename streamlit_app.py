import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import os
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# --- CONFIGURACIÓN DE SEGURIDAD ---
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("Falta la API Key en Secrets.")
    st.stop()

st.set_page_config(page_title="Psicobot", page_icon="🧠")

# --- LECTURA OPTIMIZADA ---
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

pregunta = st.text_input("¿Qué deseas consultar?", placeholder="Ej: Calendario presencial 4to semestre")

if st.button("Consultar"):
    if pregunta:
        with st.spinner("Buscando información..."):
            try:
                # Forzamos el uso de la versión estable
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                safety = {
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                }

                config = (
                    "Eres Psicobot. Tu respuesta debe ser precisa y basada en los documentos.\n"
                    "SI PREGUNTAN POR FECHAS: Revisa el calendario del semestre exacto.\n"
                    "FORMATO: Diferencia 'Clases Online' de 'Clases Presenciales' con viñetas.\n"
                    "REGLAMENTO: Cita artículos si corresponde (Ej: Art. 4).\n"
                    "No menciones archivos PDF."
                )

                # Si el error persiste, intentamos reducir el tamaño del envío
                prompt = f"{config}\n\nDATOS:\n{contexto[:50000]}\n\nPREGUNTA: {pregunta}"
                
                response = model.generate_content(prompt, safety_settings=safety)
                
                if response.text:
                    st.markdown("---")
                    st.markdown(response.text)
                else:
                    st.warning("La IA no pudo procesar la respuesta. Intenta con una pregunta más específica.")

            except Exception as e:
                # Error detallado para saber si es por la cuota (QuotaExceeded)
                if "429" in str(e):
                    st.error("⏳ ¡Límite alcanzado! Espera 60 segundos antes de volver a preguntar.")
                else:
                    st.error(f"Se perdió la conexión temporalmente. Por favor, intenta de nuevo. (Detalle: {str(e)[:50]})")
    else:
        st.warning("Escribe tu pregunta.")

st.markdown("---")
st.caption("Psicobot v1.8")
