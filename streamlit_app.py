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

# --- LECTURA SILENCIOSA DE DOCUMENTOS ---
@st.cache_resource
def cargar_informacion():
    texto_total = ""
    archivos = [
        "Doc1base.pdf", 
        "Reunión 2026-1 1.pdf", 
        "Calendario semi.pdf",
        "Documento informativo carrera de psicología.pdf",
        "Preguntas Frecuentes Cierre Seminario.pdf"
    ]
    
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

# --- INTERFAZ LIMPIA ---
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)

st.markdown("<h1 style='text-align: center;'>🧠 Psicobot</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #555;'>Asistente Virtual - Facultad de Psicología</p>", unsafe_allow_html=True)

contexto_contenido = cargar_informacion()

# --- LÓGICA DE CONSULTA ---
pregunta = st.text_input("¿En qué puedo ayudarte?", placeholder="Escribe tu duda aquí...")

if st.button("Consultar"):
    if pregunta:
        with st.spinner("Procesando consulta..."):
            try:
                # Selección de modelo
                modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                nombre_modelo = "models/gemini-1.5-flash" if "models/gemini-1.5-flash" in modelos else modelos[0]
                
                model = genai.GenerativeModel(nombre_modelo)
                
                # Seguridad sin bloqueos para temas de psicología
                filtros = {
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                }

                # INSTRUCCIONES ESTRICTAS PARA EL BOT
                instrucciones = (
                    "Eres Psicobot, el asistente oficial de la Facultad de Psicología. "
                    "Tu tono es profesional, servicial y experto. "
                    "REGLAS DE ORO:\n"
                    "1. NUNCA menciones que estás leyendo archivos, PDFs o documentos.\n"
                    "2. NUNCA digas frases como 'según el documento' o 'en el archivo adjunto'.\n"
                    "3. Si la respuesta está basada en un reglamento, DEBES citar el número de artículo correspondiente (ej: Art. 12).\n"
                    "4. Si la información no está disponible, responde amablemente que no cuentas con ese dato específico por el momento.\n"
                    "5. Mantén las respuestas concisas y claras."
                )

                prompt_final = f"{instrucciones}\n\nContexto de la Facultad:\n{contexto_contenido[:38000]}\n\nPregunta del usuario: {pregunta}"

                response = model.generate_content(prompt_final, safety_settings=filtros)
                
                if response.text:
                    st.markdown("---")
                    st.info(response.text)
                else:
                    st.warning("No se pudo generar una respuesta. Por favor, intenta de nuevo.")

            except Exception as e:
                st.error("Hubo un inconveniente al procesar la respuesta. Por favor, intenta en un momento.")
    else:
        st.warning("Por favor, ingresa una pregunta.")

st.markdown("---")
st.caption("© 2026 Facultad de Psicología - Asistente Virtual")
