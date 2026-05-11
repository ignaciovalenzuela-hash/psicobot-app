import streamlit as st
import google.generativeai as genai
import fitz
import os

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Psicobot", page_icon="🧠", layout="centered")

# --- 2. LOGO Y ENCABEZADO ---
col1, col2, col3 = st.columns([1, 1.2, 1])
with col2:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    else:
        st.caption("🚀 Psicobot en línea")

st.markdown("<h1 style='text-align: center;'>Psicobot</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: gray;'>Asistente Oficial de Psicología</p>", unsafe_allow_html=True)
st.markdown("---")

# --- 3. CONFIGURACIÓN DE API ---
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("Error: Configura la API Key en los Secrets.")
    st.stop()

# --- 4. MEMORIA DEL CHAT ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 5. CARGA DE DOCUMENTOS ---
@st.cache_resource(show_spinner=False)
def cargar_documentos():
    texto_total = ""
    archivos = [f for f in os.listdir() if f.endswith('.pdf')]
    for a in archivos:
        try:
            with fitz.open(a) as doc:
                for pagina in doc:
                    texto_total += f"\n[FUENTE: {a}]\n{pagina.get_text()}"
        except:
            continue
    return texto_total

contexto_facultad = cargar_documentos()

# --- 6. VISUALIZACIÓN DEL HISTORIAL ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 7. LÓGICA DE PREGUNTAS Y RESPUESTAS ---
if prompt := st.chat_input("¿En qué puedo ayudarte hoy?"):
    # Guardar y mostrar pregunta del usuario
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Respuesta del asistente
    with st.chat_message("assistant"):
        try:
            # Probamos la ruta que suele funcionar en versiones recientes
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            instrucciones = (
                "Eres Psicobot. Respuestas amables, breves y precisas.\n"
                "1. Diferencia CLASES ONLINE de CLASES PRESENCIALES.\n"
                "2. Cita Artículos si hablas de reglamentos.\n"
                "3. Si preguntan por un semestre, busca el archivo de ese semestre.\n"
                "4. No inventes información."
            )

            full_prompt = f"{instrucciones}\n\nCONTEXTO:\n{contexto_facultad[:100000]}\n\nPREGUNTA: {prompt}"
            
            response = model.generate_content(full_prompt)
            respuesta = response.text
            
            st.markdown(respuesta)
            st.session_state.messages.append({"role": "assistant", "content": respuesta})
            
        except Exception as e:
            st.error(f"Error de conexión: {str(e)[:100]}")
