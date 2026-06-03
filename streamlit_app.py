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

# --- 5. CARGA DE DOCUMENTOS CON FILTRO ESTRICTO ---
@st.cache_resource(show_spinner=False)
def cargar_documentos():
    texto_total = ""
    
    # LISTA NEGRA: Archivos que el bot ignorará por completo
    archivos_excluidos = {
        "Calendario 10mo semestre 2026-1.pdf",
        "Calendario 1er semestre 2026-1.pdf",
        "Calendario 2do semestre 2026-1.pdf",
        "Calendario 3er semestre 2026-1.pdf",
        "Calendario 4to semestre 2026-1.pdf",
        "Calendario 5to semestre 2026-1.pdf",
        "Calendario 6to semestre 2026-1.pdf",
        "Calendario 7mo semestre 2026-1.pdf",
        "Calendario 8vo semestre 2026-1.pdf",
        "Calendario 9no semestre 2026-1.pdf"
    }
    
    archivos = [f for f in os.listdir() if f.endswith('.pdf')]
    for a in archivos:
        # Si el archivo está en la lista negra, lo saltamos
        if a in archivos_excluidos:
            continue
            
        try:
            with fitz.open(a) as doc:
                for pagina in doc:
                    # Enmarcamos el texto indicando claramente de qué archivo viene
                    texto_total += f"\n\n--- INICIO DOCUMENTO: {a} ---\n"
                    texto_total += pagina.get_text()
                    texto_total += f"\n--- FIN DOCUMENTO: {a} ---\n"
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
            
            model = genai.GenerativeModel(
                model_name=nombre_modelo,
                generation_config={
                    "temperature": 0.0,  # Reducido a 0 para máxima precisión (cero creatividad)
                    "max_output_tokens": 2048,
                }
            )
            
            # INSTRUCCIONES MEJORADAS PARA ULTRA PRECISIÓN
            instrucciones = (
                "Eres Psicobot, un asistente académico de precisión quirúrgica para la carrera de Psicología.\n\n"
                "INSTRUCCIONES DE RAZONAMIENTO ANTES DE RESPONDER:\n"
                "1. Lee la pregunta del alumno e identifica qué asignatura o tema busca.\n"
                "2. Busca en el CONTEXTO el documento exacto que contiene esa información (fíjate en las etiquetas --- INICIO DOCUMENTO ---).\n"
                "3. Si encuentras los datos, extrae TODO sin resumir de más: Periodos de clases, días exactos (si es sábado, indica cuál), horas exactas, modalidad (Online/Presencial) y salas.\n"
                "4. Si la información varía según el semestre, aclara a qué documento/reglamento estás indexando tu respuesta.\n"
                "5. Si el dato NO está explícito en el texto actual, di textualmente: 'No dispongo de ese registro exacto en la documentación actual'. No intentes adivinar ni generalizar.\n\n"
                "FORMATO OBLIGATORIO DE RESPUESTA:\n"
                "Presenta los datos usando viñetas bien estructuradas y destaca los horarios y fechas clave en **negrita**."
            )

            full_prompt = f"{instrucciones}\n\nCONTEXTO AUTORIZADO DE LA FACULTAD:\n{contexto_facultad[:110000]}\n\nPREGUNTA DEL ESTUDIANTE: {prompt}"
            
            response = model.generate_content(full_prompt)
            
            if response.text:
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            
        except Exception as e:
            st.error("Se interrumpió la respuesta o hubo un error de conexión. Por favor, intenta preguntar de nuevo.")
