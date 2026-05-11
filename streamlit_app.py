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

pregunta = st.text_input("¿Qué deseas consultar?", placeholder="Ej: Fechas presenciales 6to semestre")

if st.button("Consultar"):
    if pregunta:
        with st.spinner("Conectando con la base de datos..."):
            # Intentamos conectar con diferentes variantes del nombre del modelo
            model = None
            errores = []
            
            # Lista de nombres posibles para el modelo
            nombres_posibles = ["gemini-1.5-flash", "models/gemini-1.5-flash", "gemini-1.5-flash-latest"]
            
            for nombre in nombres_posibles:
                try:
                    test_model = genai.GenerativeModel(nombre)
                    # Prueba rápida de conexión
                    test_model.generate_content("test", generation_config={"max_output_tokens": 1})
                    model = test_model
                    break # Si funciona, salimos del bucle
                except Exception as e:
                    errores.append(f"{nombre}: {str(e)[:50]}")
            
            if model is None:
                st.error(f"No se pudo establecer conexión. Detalles: {errores}")
                st.stop()

            try:
                safety = {
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                }

                config_inst = (
                    "Eres Psicobot. Responde con precisión académica.\n"
                    "FECHAS: Diferencia claramente 'Online' de 'Presencial'.\n"
                    "REGLAMENTO: Cita artículos (Art. X).\n"
                    "No menciones archivos PDF."
                )

                prompt = f"{config_inst}\n\nDATOS:\n{contexto[:45000]}\n\nPREGUNTA: {pregunta}"
                
                response = model.generate_content(prompt, safety_settings=safety)
                
                if response.text:
                    st.markdown("---")
                    st.markdown(response.text)
                else:
                    st.warning("Respuesta vacía. Intenta reformular.")

            except Exception as e:
                st.error(f"Error en la generación: {str(e)}")
    else:
        st.warning("Escribe una pregunta.")

st.markdown("---")
st.caption("Psicobot v1.9 - Conexión Multi-Protocolo")
