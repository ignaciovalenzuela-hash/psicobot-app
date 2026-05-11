import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import os

# 1. Configuración de API Key (Seguridad)
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("Falta la clave GOOGLE_API_KEY en los Secrets de Streamlit.")

st.set_page_config(page_title="Psicobot", page_icon="🧠")

# 2. CARGA INTELIGENTE DE TEXTO (Optimizado para velocidad)
@st.cache_resource
def obtener_contexto_mejorado():
    texto_acumulado = ""
    archivos = ["Doc1base.pdf", "Reunión 2026-1 1.pdf", "Calendario semi.pdf"]
    encontrados = 0
    for nombre in archivos:
        if os.path.exists(nombre):
            try:
                doc = fitz.open(nombre)
                for pagina in doc:
                    texto_acumulado += pagina.get_text("text") + "\n"
                doc.close()
                encontrados += 1
            except Exception as e:
                print(f"Error leyendo {nombre}: {e}")
    return texto_acumulado if encontrados > 0 else None

# --- INTERFAZ ---
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)

st.markdown("<h1 style='text-align: center;'>🧠 Psicobot</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: gray;'>Asistente de la Facultad de Psicología</p>", unsafe_allow_html=True)

# Cargamos el contenido una sola vez
contexto_full = obtener_contexto_mejorado()

if not contexto_full:
    st.error("⚠️ No se pudieron leer los archivos PDF. Verifica que estén en GitHub.")
else:
    pregunta = st.text_input("Haz tu pregunta:", placeholder="Ej: ¿Cuándo terminan las clases?")
    
    if st.button("Preguntar a Psicobot"):
        if pregunta:
            # Creamos un espacio vacío para la respuesta
            contenedor_respuesta = st.empty()
            with st.spinner("🔍 Psicobot está buscando en los reglamentos..."):
                try:
                    # Usamos el modelo más rápido
                    model = genai.GenerativeModel("gemini-1.5-flash")
                    
                    config_prompt = (
                        "Eres Psicobot, asistente oficial de la Facultad de Psicología. "
                        "Responde de forma breve, amable y profesional. "
                        "Básate SOLO en este texto:\n\n"
                    )
                    
                    # Llamada a la IA
                    response = model.generate_content(f"{config_prompt}{contexto_full}\n\nPregunta: {pregunta}")
                    
                    # Mostramos el resultado
                    if response.text:
                        contenedor_respuesta.success(response.text)
                    else:
                        contenedor_respuesta.warning("La IA no pudo generar una respuesta clara.")
                        
                except Exception as e:
                    error_msg = str(e)
                    if "429" in error_msg:
                        st.error("⏳ Demasiadas preguntas seguidas. Espera 60 segundos.")
                    else:
                        st.error(f"❌ Error técnico: {error_msg}")
        else:
            st.warning("Escribe algo antes de preguntar.")

st.markdown("---")
st.caption("Psicobot v1.2 - Desarrollado para la Facultad de Psicología")
