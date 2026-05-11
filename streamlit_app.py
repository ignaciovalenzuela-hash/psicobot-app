import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import os

# 1. Configuración de API Key (Secrets de Streamlit)
api_key = st.secrets["GOOGLE_API_KEY"]
genai.configure(api_key=api_key)

st.set_page_config(page_title="Psicobot", page_icon="🧠")

# 2. Función Optimizada: Solo lee los archivos UNA VEZ (Caché)
@st.cache_resource
def obtener_contexto():
    texto_acumulado = ""
    archivos = ["Doc1base.pdf", "Reunión 2026-1 1.pdf", "Calendario semi.pdf"]
    for nombre in archivos:
        if os.path.exists(nombre):
            try:
                doc = fitz.open(nombre)
                for pagina in doc:
                    texto_acumulado += pagina.get_text()
            except Exception:
                continue
    return texto_acumulado

# 3. Diseño de Interfaz
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)

st.markdown("<h1 style='text-align: center;'>🧠 Psicobot</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'>Asistente Virtual de la Facultad de Psicología</p>", unsafe_allow_html=True)
st.markdown("---")

# Cargar el contexto (esto será instantáneo después de la primera vez)
contexto_documentos = obtener_contexto()

if contexto_documentos:
    st.write("👋 **¡Hola! Soy Psicobot.** ¿En qué puedo ayudarte hoy?")
    
    # Campo de pregunta
    pregunta_usuario = st.text_input("Escribe tu consulta:", placeholder="Ej: ¿Cuándo es el próximo examen?")
    
    if st.button("Consultar a Psicobot"):
        if pregunta_usuario:
            with st.spinner("Psicobot está pensando..."):
                try:
                    # Configurar el modelo de IA
                    model = genai.GenerativeModel("gemini-1.5-flash")
                    
                    # Instrucciones de personalidad
                    prompt_instrucciones = (
                        "Eres Psicobot, el asistente oficial de la Facultad de Psicología. "
                        "Responde de forma amable, empática y muy profesional. "
                        "Usa EXCLUSIVAMENTE la información de los documentos proporcionados. "
                        "No menciones que lees archivos PDF ni nombres de documentos. "
                        "Si la información no está en los documentos, indícalo amablemente."
                    )
                    
                    # Generar respuesta
                    respuesta = model.generate_content(
                        f"{prompt_instrucciones}\n\nContexto:\n{contexto_documentos}\n\nPregunta: {pregunta_usuario}"
                    )
                    
                    st.markdown("### 📝 Respuesta:")
                    st.info(respuesta.text)
                    
                except Exception as e:
                    st.error("Lo siento, hubo un pequeño error técnico. Intenta de nuevo en unos segundos.")
        else:
            st.warning("Por favor, escribe una pregunta primero.")
else:
    st.error("⚠️ No se encontraron los archivos PDF en el servidor. Revisa tu GitHub.")
