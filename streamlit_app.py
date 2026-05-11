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
    # LISTA ACTUALIZADA DE ARCHIVOS
    archivos = [
        "Doc1base.pdf", 
        "Reunión 2026-1 1.pdf", 
        "Calendario semi.pdf",
        "Documento informativo carrera de psicología.pdf",
        "Preguntas Frecuentes Cierre Seminario.pdf"
    ]
    
    encontrados = []
    for nombre in archivos:
        if os.path.exists(nombre):
            try:
                doc = fitz.open(nombre)
                for pagina in doc:
                    texto_total += pagina.get_text() + " "
                doc.close()
                encontrados.append(nombre)
            except:
                continue
    return texto_total.strip(), encontrados

# --- INTERFAZ ---
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)

st.markdown("<h1 style='text-align: center;'>🧠 Psicobot</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #555;'>Asistente de la Facultad de Psicología</p>", unsafe_allow_html=True)

contenido_contexto, lista_exito = cargar_informacion()

# --- LÓGICA DE RESPUESTA ---
pregunta = st.text_input("¿En qué puedo ayudarte?", placeholder="Ej: ¿Cuáles son las fechas del seminario?")

if st.button("Consultar"):
    if pregunta:
        with st.spinner("Psicobot está revisando los documentos..."):
            try:
                # Selección dinámica de modelo
                modelos_disponibles = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                nombre_modelo = "models/gemini-1.5-flash" if "models/gemini-1.5-flash" in modelos_disponibles else modelos_disponibles[0]
                
                model = genai.GenerativeModel(nombre_modelo)
                
                # Configuración para evitar bloqueos por temas sensibles de psicología
                filtros_paz = {
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                }

                if not contenido_contexto:
                    prompt = f"Eres Psicobot, asistente de psicología. Responde de forma amable: {pregunta}"
                else:
                    # Limitamos el contexto para no saturar la memoria (aprox 30k caracteres)
                    prompt = f"Eres Psicobot, el asistente oficial. Usa esta información institucional para responder:\n\n{contenido_contexto[:35000]}\n\nPregunta: {pregunta}"

                response = model.generate_content(prompt, safety_settings=filtros_paz)
                
                if response.text:
                    st.markdown("### 📝 Respuesta:")
                    st.info(response.text)
                else:
                    st.warning("No se pudo generar una respuesta detallada.")

            except Exception as e:
                st.error(f"Error de conexión: {str(e)}")
    else:
        st.warning("Por favor, escribe una pregunta.")

# Mostrar archivos cargados (opcional, ayuda a verificar)
with st.expander("Ver documentos cargados"):
    if lista_exito:
        for f in lista_exito:
            st.write(f"✅ {f}")
    else:
        st.write("❌ No se detectaron archivos PDF.")

st.markdown("---")
st.caption("Psicobot v1.4 - Base de conocimientos ampliada")
