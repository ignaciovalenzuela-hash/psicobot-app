import streamlit as st
import google.generativeai as genai
import fitz  # Para los PDFs
import pandas as pd  # Para el Excel/CSV
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
st.markdown("<p style='text-align: center; color: gray;'>Tu asistente oficial de Psicología</p>", unsafe_allow_html=True)
st.markdown("---")

# --- 3. CONFIGURACIÓN DE API ---
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("Error: Configura la API Key en los Secrets.")
    st.stop()

# --- 4. MEMORIA DEL CHAT (Inicialización) ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 5. CARGA INTELIGENTE DE REGLAMENTOS Y HORARIOS ---
@st.cache_resource(show_spinner=False)
def cargar_documentos():
    texto_total = ""
    
    # Lista negra de archivos excluidos
    archivos_excluidos = {
        "Calendario 10mo semestre 2026-1.pdf", "Calendario 1er semestre 2026-1.pdf",
        "Calendario 2do semestre 2026-1.pdf", "Calendario 3er semestre 2026-1.pdf",
        "Calendario 4to semestre 2026-1.pdf", "Calendario 5to semestre 2026-1.pdf",
        "Calendario 6to semestre 2026-1.pdf", "Calendario 7mo semestre 2026-1.pdf",
        "Calendario 8vo semestre 2026-1.pdf", "Calendario 9no semestre 2026-1.pdf"
    }
    
    archivos = os.listdir()
    
    for a in archivos:
        if a in archivos_excluidos:
            continue
            
        # --- PROCESAR REGLAMENTOS O TEXTOS (PDFs) ---
        if a.endswith('.pdf'):
            try:
                with fitz.open(a) as doc:
                    for pagina in doc:
                        texto_total += f"\n\n--- INICIO DOCUMENTO: {a} ---\n"
                        texto_total += pagina.get_text()
                        texto_total += f"\n--- FIN DOCUMENTO: {a} ---\n"
            except: continue
            
        # --- PROCESAR HORARIOS SEMIPRESENCIAL (CSV/Excel) ---
        elif a.endswith('.csv'):
            try:
                df = pd.read_csv(a)
                texto_total += f"\n\n--- INICIO BASE DE DATOS HORARIOS PRESENCIALES SEMIPRESENCIAL: {a} ---\n"
                for index, fila in df.iterrows():
                    # Limpiamos la fecha para quitar las horas ceros si vienen del Excel
                    fecha_raw = str(fila.get('FECHAS DE LA CLASE', fila.get('FECHA DE LA CLASE', '')))
                    fecha_limpia = fecha_raw.split(' ')[0] if ' ' in fecha_raw else fecha_raw
                    
                    texto_total += (
                        f"Asignatura: {fila.get('ASIGNATURAS', '')} ({fila.get('CODIGO DE ASIGNATURAS', '')}) | "
                        f"Sección: {fila.get('SECCIÓN', '')} | "
                        f"Docente: {fila.get('NOMBRES DOCENTE', '')} {fila.get('APELLIDO PATERNO DOCENTE', '')} {fila.get('APELLIDO MATERNO DOCENTE', '')} | "
                        f"Día de la semana: {fila.get('DÍA', '')} | "
                        f"Fecha: {fecha_limpia} | "
                        f"Horario: {fila.get('HORA INICIO DE LA CLASE', '')} a {fila.get('HORA FINALIZACIÓN DE LA CLASE', '')} | "
                        f"Sala: {fila.get('CODIGO DE SALA DE CLASES', '')} | "
                        f"Semestre: {fila.get('SEMESTRE', '')}\n"
                    )
                texto_total += f"--- FIN BASE DE DATOS HORARIOS SEMIPRESENCIAL ---\n"
            except: continue
            
    return texto_total

contexto_facultad = cargar_documentos()

# --- 6. VISUALIZACIÓN DEL HISTORIAL EN PANTALLA ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 7. LÓGICA DE PREGUNTAS Y RESPUESTAS ---
if prompt := st.chat_input("Escribe tu duda aquí..."):
    # Mostrar y registrar pregunta actual del usuario
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
                    "temperature": 0.0, # Volvemos a 0.0 para evitar cualquier desvío de formato
                    "max_output_tokens": 2048,
                }
            )
            
            # INSTRUCCIONES ULTRA ESTRICTAS DE ENRUTAMIENTO Y FORMATO
            instrucciones = (
                "Eres Psicobot, un tutor académico experto y empático de la carrera de Psicología.\n\n"
                "REGLA 1: FILTRO OBLIGATORIO DE MODALIDAD\n"
                "Si el estudiante pregunta por fechas de clases, horarios, o asignaturas de un semestre (ej. '¿cuándo son las clases presenciales de semipresencial?', '¿cuándo son las clases de X semestre?', '¿cuándo tengo clases de X materia?'):\n"
                "- DEBES verificar si en su pregunta actual O en el HISTORIAL DE LA CONVERSACIÓN ya se especificó la palabra 'semipresencial'.\n"
                "- Si NO se ha especificado la modalidad, NO entregues ninguna fecha. Detén la respuesta y pregunta amablemente: '¡Hola! Para darte el dato exacto, ¿me podrías confirmar para qué modalidad necesitas saber esto?'.\n\n"
                "REGLA 2: FORMATO EXCLUSIVO PARA SEMIPRESENCIAL\n"
                "Si se detecta que es para la modalidad 'semipresencial', busca los datos en la 'BASE DE DATOS HORARIOS PRESENCIALES SEMIPRESENCIAL' y devuelve la información de las fechas utilizando ESTRICTAMENTE el siguiente formato (Respeta los saltos de línea exactos, NO uses viñetas como '*' ni '-'):\n\n"
                "📅 [Día de la semana] [Día] de [Mes] de [Año]\n\n"
                "🕒 Horario: [Hora Inicio] a [Hora Fin] hrs.\n"
                "📍 Sala: [Sala]\n"
                "👨‍🏫 Docente: [Nombre Completo del Docente]\n\n"
                "Ejemplo de salida exacta requerida:\n"
                "📅 Sábado 28 de marzo de 2026\n\n"
                "🕒 Horario: 11:05 a 14:05 hrs.\n"
                "📍 Sala: CCC302\n"
                "👨‍🏫 Docente: Marila Del Carmen García Puelpan\n\n"
                "Si la asignatura tiene múltiples fechas presenciales en esa sección/semestre, colócalas una abajo de la otra siguiendo este mismo patrón estructural."
            )

            # Construimos el texto del historial para que el modelo tenga memoria real
            historial_contexto = ""
            for msg in st.session_state.messages[:-1]:
                rol = "Estudiante" if msg["role"] == "user" else "Psicobot"
                historial_contexto += f"{rol}: {msg['content']}\n"

            # Prompt unificado definitivo
            full_prompt = (
                f"{instrucciones}\n\n"
                f"CONTEXTO DE LA FACULTAD:\n{contexto_facultad[:100000]}\n\n"
                f"HISTORIAL DE LA CONVERSACIÓN:\n{historial_contexto}\n"
                f"PREGUNTA ACTUAL DEL ESTUDIANTE: {prompt}"
            )
            
            response = model.generate_content(full_prompt)
            
            if response.text:
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            
        except Exception as e:
            st.error("Se produjo una breve interrupción en la línea. Por favor, intenta enviar tu pregunta de nuevo.")
