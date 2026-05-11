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
    # Busca todos los PDFs en la carpeta raíz
    archivos = [f for f in os.listdir() if f.endswith('.pdf')]
    for a in archivos:
        try:
            with fitz.open(a) as doc:
                for pagina in doc:
                    texto_total += f"\n[FUENTE: {a}]\n{pagina.get_text()}"
        except: continue
    return texto_total

contexto_facultad = cargar_documentos()

# --- INTERFAZ ---
st.title("🧠 Psicobot: Asistente Académico")
st.caption("Resuelvo dudas sobre calendarios, reglamentos y la carrera de Psicología.")

# Mostrar historial
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Entrada de usuario
if prompt := st.chat_input("¿Qué deseas saber?"):
    # Agregar pregunta del usuario
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Respuesta del bot
    with st.chat_message("assistant"):
        try:
            # Seleccionamos el modelo más eficiente en costo
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Instrucciones estrictas
            instrucciones = (
                "Eres Psicobot. Tu respuesta debe ser amable y precisa.\n"
                "1. Usa el contexto de los documentos cargados.\n"
                "2. Si la pregunta es sobre FECHAS, indica si son ONLINE o PRESENCIALES.\n"
                "3. Si usas reglamentos, cita el Artículo (Art. X).\n"
                "4. Si no sabes algo, indica que no está en los registros.\n"
                "NO menciones que lees archivos PDF."
            )

            # Enviamos contexto + la pregunta actual
            # (Limitamos el contexto a 50k tokens para ahorrar costos)
            contenido_prompt = f"{instrucciones}\n\nCONTEXTO:\n{contexto_facultad[:100000]}\n\nPREGUNTA Estudiante: {prompt}"
            
            response = model.generate_content(contenido_prompt)
            
            respuesta_texto = response.text
            st.markdown(respuesta_texto)
            st.session_state.messages.append({"role": "assistant", "content": respuesta_texto})
            
        except Exception as e:
            if "429" in str(e):
                st.error("⏳ El sistema está muy solicitado. Por favor, intenta en un minuto.")
            else:
                st.error("Hubo un problema al procesar tu consulta. Reintenta en breve.")
