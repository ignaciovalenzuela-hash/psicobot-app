import streamlit as st
import google.generativeai as genai
import fitz  # Para los PDFs
import pandas as pd  # Para el Excel/CSV
import os
import unicodedata

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Psicobot", page_icon="🧠", layout="centered")

# Función auxiliar para limpiar acentos y espacios de los encabezados del Excel
def normalizar_columna(col):
    col = str(col).strip().upper()
    return ''.join(ch for ch in unicodedata.normalize('NFD', col) if unicodedata.category(ch) != 'Mn')

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

# --- 5. CARGA ULTRA ROBUSTA DE REGLAMENTOS Y HORARIOS ---
@st.cache_resource(show_spinner=False)
def cargar_documentos():
    texto_total = ""
    archivos_procesados_exitosamente = []
    
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
            
        # --- PROCESAR HORARIOS SEMIPRESENCIAL (CSV/Excel) ---
        # Los procesamos primero para asegurar su prioridad en el texto
        if a.endswith('.csv'):
            df = None
            # Probamos múltiples codificaciones para evitar caídas por tildes (Ó, Í)
            for encoding_opt in ['utf-8', 'latin-1', 'utf-8-sig', 'cp1252']:
                try:
                    df = pd.read_csv(a, encoding=encoding_opt)
                    break
                except:
                    continue
            
            if df is not None:
                archivos_procesados_exitosamente.append(f"📊 Excel Horarios: {a}")
                texto_total += f"\n\n--- INICIO BASE DE DATOS HORARIOS PRESENCIALES SEMIPRESENCIAL: {a} ---\n"
                
                # Normalizamos las columnas (quita espacios y tildes: SECCIÓN -> SECCION)
                df.columns = [normalizar_columna(c) for c in df.columns]
                
                for index, fila in df.iterrows():
                    fecha_raw = str(fila.get('FECHA DE LA CLASE', fila.get('FECHAS DE LA CLASE', '')))
                    fecha_limpia = fecha_raw.split(' ')[0] if ' ' in fecha_raw else fecha_raw
                    
                    texto_total += (
                        f"Asignatura: {fila.get('ASIGNATURAS', fila.get('ASIGNATURA', ''))} ({fila.get('CODIGO DE ASIGNATURAS', '')}) | "
                        f"Seccion: {fila.get('SECCION', '')} | "
                        f"Docente: {fila.get('NOMBRES DOCENTE', '')} {fila.get('APELLIDO PATERNO DOCENTE', '')} {fila.get('APELLIDO MATERNO DOCENTE', '')} | "
                        f"Dia de la semana: {fila.get('DIA', '')} | "
                        f"Fecha: {fecha_limpia} | "
                        f"Horario: {fila.get('HORA INICIO DE LA CLASE', '')} a {fila.get('HORA FINALIZACION DE LA CLASE', '')} | "
                        f"Sala: {fila.get('CODIGO DE SALA DE CLASES', fila.get('SALA', ''))} | "
                        f"Semestre: {fila.get('SEMESTRE', '')}\n"
                    )
                texto_total += f"--- FIN BASE DE DATOS HORARIOS SEMIPRESENCIAL ---\n"
            
        # --- PROCESAR REGLAMENTOS (PDFs) ---
        elif a.endswith('.pdf'):
            try:
                with fitz.open(a) as doc:
                    for pagina in doc:
                        texto_total += f"\n\n--- INICIO DOCUMENTO: {a} ---\n"
                        texto_total += pagina.get_text()
                        texto_total += f"\n--- FIN DOCUMENTO: {a} ---\n"
                archivos_procesados_exitosamente.append(f"📄 Documento PDF: {a}")
            except: 
                continue
            
    return texto_total, archivos_procesados_exitosamente

# Ejecutamos la carga
contexto_facultad, archivos_activos = cargar_documentos()

# --- 5.1 BARRA LATERAL DE CONTROL INTERNO ---
with st.sidebar:
    st.subheader("📁 Sistema de Archivos Activo")
    st.write("Verifica qué documentos está leyendo Psicobot actualmente:")
    if archivos_activos:
        for arch in archivos_activos:
            st.success(arch)
    else:
        st.error("⚠️ No se ha detectado ningún archivo PDF o CSV en la raíz de tu GitHub.")

# --- 6. VISUALIZACIÓN DEL HISTORIAL EN PANTALLA ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 7. LÓGICA DE PREGUNTAS Y RESPUESTAS ---
if prompt := st.chat_input("Escribe tu duda aquí..."):
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
                    "temperature": 0.0, 
                    "max_output_tokens": 2048,
                }
            )
            
            # INSTRUCCIONES FORMATEADAS AL DETALLE SOLICITADO
            instrucciones = (
                "Eres Psicobot, un tutor académico experto y muy cercano para la carrera de Psicología.\n\n"
                "REGLA 1: FILTRO DE MODALIDAD OBLIGATORIO\n"
                "Si el estudiante pregunta por fechas de clases presenciales, horarios, o asignaturas de un semestre (ej. '¿cuándo son las clases presenciales de semipresencial?', '¿cuándo son las clases de 4to semestre?'):\n"
                "- Revisa si en su pregunta o en el HISTORIAL de la conversación ya se ha aclarado explícitamente el término 'semipresencial'.\n"
                "- Si NO se ha mencionado la modalidad, detén la entrega de datos y di exactamente: '¡Hola! Para darte la información exacta de tus jornadas, ¿me podrías confirmar para qué modalidad necesitas saber esto?'.\n\n"
                "REGLA 2: FORMATO ESTRICTO DE ENTREGA (MÁXIMA PRIORIDAD)\n"
                "Si se confirma la modalidad semipresencial, busca en la 'BASE DE DATOS HORARIOS PRESENCIALES SEMIPRESENCIAL'. Debes entregar la información usando de forma milimétrica la siguiente estructura (Respeta los saltos de línea exactos, NO uses viñetas como '*' ni '-'):\n\n"
                "📅 [Día de la semana] [Día] de [Mes] de [Año]\n\n"
                "🕒 Horario: [Hora Inicio] a [Hora Fin] hrs.\n"
                "📍 Sala: [Sala]\n"
                "👨‍🏫 Docente: [Nombre Completo del Docente]\n\n"
                "EJEMPLO DE SALIDA EXACTA REQUERIDA:\n"
                "📅 Sábado 28 de marzo de 2026\n\n"
                "🕒 Horario: 11:05 a 14:05 hrs.\n"
                "📍 Sala: CCC302\n"
                "👨‍🏫 Docente: Marila Del Carmen García Puelpan\n\n"
                "Si la asignatura o el semestre consultado contiene múltiples fechas asignadas, pon un bloque abajo del otro separados por un salto de línea."
            )

            historial_contexto = ""
            for msg in st.session_state.messages[:-1]:
                rol = "Estudiante" if msg["role"] == "user" else "Psicobot"
                historial_contexto += f"{rol}: {msg['content']}\n"

            # Ampliamos el rango de lectura a 300,000 caracteres para evitar recortes accidentales
            full_prompt = (
                f"{instrucciones}\n\n"
                f"CONTEXTO DE LA FACULTAD:\n{contexto_facultad[:300000]}\n\n"
                f"HISTORIAL DE LA CONVERSACIÓN:\n{historial_contexto}\n"
                f"PREGUNTA ACTUAL DEL ESTUDIANTE: {prompt}"
            )
            
            response = model.generate_content(full_prompt)
            
            if response.text:
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            
        except Exception as e:
            st.error("Se produjo una breve interrupción en la línea. Por favor, intenta enviar tu pregunta de nuevo.")
