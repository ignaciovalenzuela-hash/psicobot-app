import streamlit as st
import google.generativeai as genai
import fitz
import os

# --- INICIALIZACIÓN DE LA APP ---
st.set_page_config(page_title="Psicobot", page_icon="🧠")

# Configurar API Key desde Secrets
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("Configura la API Key en los Secrets de Streamlit.")
    st.stop()

# --- MEMORIA DEL CHAT ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- CARGA DE DOCUMENTOS (Cache inteligente) ---
@st.cache_resource(show_spinner=False)
def cargar_documentos():
    texto_total = ""
    archivos = [f for f in os.listdir() if f.endswith('.pdf')]
    for a in archivos:
        try:
            with fitz.open(a) as doc:
                for pagina in doc:
                    texto_total += f"\n[FUENTE: {a}]\n{pagina.get_text()}"
        except: continue
    return texto_total

contexto_facultad = cargar_documentos()

# --- ENCABEZADO CON LOGO ---
# Creamos columnas para centrar el logo
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    else:
        # Esto es solo por si acaso el archivo no se llama logo.png
        st.write("⚠️ Archivo 'logo.png' no encontrado en GitHub")

st.markdown("<h1 style='text-align: center;'>🧠 Psicobot</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #555;'>Asistente Académico de Psicología</p>", unsafe_allow_html=True)
st.markdown("---")

# --- VISUALIZACIÓN DEL CHAT ---
# Mostramos el historial de mensajes que están en la memoria
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- ENTRADA DE USUARIO Y RESPUESTA ---
if prompt := st.chat_input("Escribe tu duda aquí..."):
    # 1. Mostrar y guardar pregunta del usuario
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Generar y mostrar respuesta del bot
    with st.chat_message("assistant"):
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            instrucciones = (
                "Eres Psicobot. Tu respuesta debe ser amable y muy precisa.\n"
                "1. Usa el contexto de los documentos cargados.\n"
                "2. Si la pregunta es sobre FECHAS, indica claramente: ONLINE o PRESENCIAL.\n"
                "3. Si es sobre reglamentos, cita el Artículo (Art. X).\n"
                "4. Si la info no está, di que no tienes el registro exacto.\n"
                "5. IMPORTANTE: Si te preguntan por un semestre específico, busca SOLO en ese calendario."
            )

            contenido_prompt = f"{instrucciones}\n\nCONTEXTO:\n{contexto_facultad[:100000]}\n\nPREGUNTA: {prompt}"
            
            response = model.generate_content(contenido_prompt)
            respuesta_texto = response.text
            
            st.markdown(respuesta_texto)
            st.session_state.messages.append({"role": "assistant", "content": respuesta_texto})
            
        except Exception as e:
            if "429" in str(e):
                st.error("⏳ Límite alcanzado. Reintenta en un minuto.")
            else:
                st.error("Hubo un error al conectar. Reintenta en breve.")
