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

# --- LECTURA PROFUNDA DE DOCUMENTOS ---
@st.cache_resource(show_spinner=False)
def cargar_informacion():
    texto_total = ""
    # Nombres exactos de tus archivos en GitHub
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
                # Abrimos el archivo de forma explícita
                with fitz.open(nombre) as doc:
                    for pagina in doc:
                        # Extraemos texto limpio y agregamos saltos de línea
                        texto_total += f"\n--- ORIGEN: {nombre} ---\n"
                        texto_total += pagina.get_text("text")
            except Exception as e:
                print(f"Error cargando {nombre}: {e}")
    return texto_total.strip()

# --- INTERFAZ ---
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)

st.markdown("<h1 style='text-align: center;'>🧠 Psicobot</h1>", unsafe_allow_html=True)

contexto_contenido = cargar_informacion()

# --- LÓGICA DE CONSULTA ---
pregunta = st.text_input("¿En qué puedo ayudarte?", placeholder="Consulta sobre la carrera o el seminario...")

if st.button("Consultar"):
    if pregunta:
        if not contexto_contenido:
            st.error("⚠️ Atención: El bot no está detectando contenido en los archivos PDF.")
        
        with st.spinner("Buscando en la base de datos..."):
            try:
                modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                nombre_modelo = "models/gemini-1.5-flash" if "models/gemini-1.5-flash" in modelos else modelos[0]
                model = genai.GenerativeModel(nombre_modelo)
                
                filtros = {
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                }

                instrucciones = (
                    "Eres Psicobot, el asistente oficial. Tu conocimiento viene de los documentos cargados. "
                    "REGLAS:\n"
                    "1. NO menciones que lees PDFs o archivos.\n"
                    "2. Si la info está en un reglamento, CITA el artículo (ej: Art. 5).\n"
                    "3. Responde con seguridad sobre la carrera de psicología y el cierre de seminario.\n"
                    "4. Si no sabes algo, dilo amablemente."
                )

                # Enviamos el contexto completo (Gemini 1.5 Flash soporta mucho texto)
                prompt_final = f"{instrucciones}\n\nCONTEXTO INSTITUCIONAL:\n{contexto_contenido}\n\nPREGUNTA: {pregunta}"

                response = model.generate_content(prompt_final, safety_settings=filtros)
                
                if response.text:
                    st.markdown("---")
                    st.info(response.text)
            except Exception as e:
                st.error(f"Error técnico: {str(e)}")
    else:
        st.warning("Por favor, ingresa una pregunta.")
