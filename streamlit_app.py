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

# --- 5. CARGA DE DOCUMENTOS (Cache inteligente) ---
@st.cache_resource(show_spinner=False)
def cargar_documentos():
    texto_total = ""
    archivos = [f for f in os.listdir() if f.endswith('.pdf')]
    for a in archivos:
        try:
            with fitz.open(a) as doc:
                for pagina in doc:
                    texto_total += f"\n\n[ARCHIVO: {a}]\n" + pagina.get_text()
        except:
            continue
    return texto_total

contexto_facultad = cargar_documentos()

# --- 6. VISUALIZACIÓN DEL HISTORIAL ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 7. LÓGICA DE PREGUNTAS Y RESPUESTAS ---
if prompt := st.chat_input("¿Qué deseas consultar hoy?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            modelos_disponibles = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            nombre_modelo = next((m for m in modelos_disponibles if "flash" in m), modelos_disponibles[0])
            
            # Ajustamos la configuración para permitir respuestas más largas
            model = genai.GenerativeModel(
                model_name=nombre_modelo,
                generation_config={
                    "temperature": 0.1,
                    "max_output_tokens": 2048, # Aumentado para evitar cortes
                }
            )
            
            instrucciones = (
                "Eres Psicobot. Debes ser exhaustivo y dar la información COMPLETA.\n"
                "Si encuentras una asignatura, responde con este formato:\n"
                "- **Periodo de dictación:** (fechas)\n"
                "- **Clases Presenciales:** (días y fechas exactas)\n"
                "- **Horario y Sala:** (detalles)\n"
                "- **Modalidad:** (Online/Presencial)\n"
                "Usa negritas para que la información destaque."
            )

            full_prompt = f"{instrucciones}\n\nCONTEXTO:\n{contexto_facultad[:100000]}\n\nPREGUNTA: {prompt}"
            
            response = model.generate_content(full_prompt)
            
            if response.text:
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            
        except Exception as e:
            st.error("Se interrumpió la respuesta o hubo un error de conexión. Por favor, intenta preguntar de nuevo.")
