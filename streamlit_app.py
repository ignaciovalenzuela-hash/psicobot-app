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
    # Lee todos los archivos PDF en la carpeta raíz
    archivos = [f for f in os.listdir() if f.endswith('.pdf')]
    for a in archivos:
        try:
            with fitz.open(a) as doc:
                for pagina in doc:
                    # Incluimos el nombre del archivo en cada página para que el bot sepa la fuente
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
    # Guardar y mostrar pregunta del usuario
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Respuesta del asistente
    with st.chat_message("assistant"):
        try:
            # Buscamos modelos disponibles para evitar errores 404
            modelos_disponibles = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            nombre_modelo = next((m for m in modelos_disponibles if "flash" in m), modelos_disponibles[0])
            
            # CONFIGURACIÓN PRO: Temperatura baja para máxima precisión
            model = genai.GenerativeModel(
                model_name=nombre_modelo,
                generation_config={
                    "temperature": 0.1,
                    "top_p": 0.95,
                    "max_output_tokens": 1024,
                }
            )
            
            # INSTRUCCIONES ESTRICTAS DE EXTRACCIÓN
            instrucciones = (
                "Eres Psicobot, el asistente oficial de la carrera de Psicología. Tu objetivo es ahorrarle tiempo al alumno dando datos EXACTOS.\n\n"
                "REGLAS CRÍTICAS:\n"
                "1. EXTRACCIÓN TOTAL: Si te preguntan por una asignatura, busca en los calendarios: Fecha inicio/término, Jornadas Presenciales (días exactos), Horarios y Salas.\n"
                "2. NO SEAS VAGO: No digas 'revisa el calendario' o 'mira tu portal' si la información está en los documentos. Entrega el dato aquí mismo.\n"
                "3. MODALIDAD: Indica siempre si la clase es Online, Presencial o Híbrida según lo indique el documento.\n"
                "4. FORMATO: Usa listas con puntos y negritas para que la información sea fácil de escanear visualmente.\n"
                "5. SEMESTRES: Ten cuidado de no confundir calendarios. Si el alumno pregunta por una materia de 10mo, busca solo en el archivo de 10mo.\n"
                "6. REGLAMENTOS: Si la duda es normativa, cita el número de Artículo correspondiente."
            )

            # Construcción del prompt con contexto limitado para eficiencia
            full_prompt = f"{instrucciones}\n\nCONTEXTO DE LA FACULTAD:\n{contexto_facultad[:120000]}\n\nPREGUNTA DEL ESTUDIANTE: {prompt}"
            
            # Generar respuesta
            response = model.generate_content(full_prompt)
            
            if response.text:
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            
        except Exception as e:
            st.error(f"Error de conexión: {str(e)[:100]}")
            st.info("💡 Si este error persiste, intenta refrescar la página.")
