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
                        # Añadimos etiquetas claras para que la IA no se confunda de semestre
                        texto_total += f"\n--- INICIO DE DOCUMENTO: {nombre} ---\n"
                        texto_total += pagina.get_text("text")
                        texto_total += f"\n--- FIN DE DOCUMENTO: {nombre} ---\n"
            except:
                continue
    return texto_total.strip()

# --- INTERFAZ ---
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)

st.markdown("<h1 style='text-align: center;'>🧠 Psicobot</h1>", unsafe_allow_html=True)

contexto_contenido = cargar_informacion()

# --- LÓGICA DE CONSULTA ---
pregunta = st.text_input("¿En qué puedo ayudarte?", placeholder="Ej: ¿Cuáles son las clases presenciales de 10mo semestre?")

if st.button("Consultar"):
    if pregunta:
        with st.spinner("Analizando calendarios y modalidades..."):
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

                # INSTRUCCIONES DE PRECISIÓN EXTREMA
                instrucciones_sistema = (
                    "Eres Psicobot, experto en la programación académica 2026-1 de Psicología. "
                    "Cuando el usuario pregunte por fechas de un semestre o asignatura, DEBES:\n"
                    "1. Identificar el archivo exacto correspondiente al semestre solicitado.\n"
                    "2. Listar las fechas de clases diferenciando claramente cuáles son PRESENCIALES y cuáles son ONLINE.\n"
                    "3. Si la asignatura es 100% online, indícalo explícitamente.\n"
                    "4. Usa un formato de lista o tabla simple para que las fechas sean fáciles de leer.\n"
                    "5. Si mencionas artículos de reglamentos, cítalos (ej: Art. X).\n"
                    "6. NO menciones que estás leyendo PDFs."
                )

                prompt_final = f"{instrucciones_sistema}\n\nDATOS ACADÉMICOS:\n{contexto_contenido}\n\nPREGUNTA DEL ALUMNO: {pregunta}"

                response = model.generate_content(prompt_final, safety_settings=filtros_seguridad)
                
                if response.text:
                    st.markdown("---")
                    st.markdown(response.text) # Usamos markdown para que las tablas/listas se vean bien
                else:
                    st.warning("No pude encontrar fechas exactas para esa consulta.")

            except Exception as e:
                st.error("Error de conexión. Intenta nuevamente.")
    else:
        st.warning("Escribe una pregunta para ayudarte.")

st.markdown("---")
st.caption("Psicobot v1.7 - Especialista en Calendarios Académicos")
