import streamlit as st
import google.generativeai as genai
import fitz  # Para los PDFs (PyMuPDF)
import pandas as pd  # Para el Excel
import os
import unicodedata
import datetime  # Mantiene la noción del tiempo real

# --- 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS VISUALES PERSONALIZADOS (CSS) ---
st.set_page_config(page_title="Psicobot", page_icon="🧠", layout="centered")

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    .titulo-psicobot {
        background: linear-gradient(45deg, #cc609b, #ff89c9);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        font-weight: 800;
        font-size: 3.2rem;
        margin-bottom: 0rem;
    }

    .online-indicator {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 8px;
        color: #555;
        font-size: 0.95rem;
        margin-top: -5px;
        margin-bottom: 25px;
        font-weight: 500;
    }
    .dot {
        height: 10px;
        width: 10px;
        background-color: #ff89c9;
        border-radius: 50%;
        display: inline-block;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0% { transform: scale(0.9); box-shadow: 0 0 0 0 rgba(255, 137, 201, 0.7); }
        70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(255, 137, 201, 0); }
        100% { transform: scale(0.9); box-shadow: 0 0 0 0 rgba(255, 137, 201, 0); }
    }

    .welcome-card {
        background-color: #ffffff;
        border-left: 5px solid #cc609b;
        padding: 18px;
        border-radius: 8px;
        box-shadow: 0px 4px 15px rgba(0, 0, 0, 0.05);
        margin-bottom: 15px;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    .welcome-card:hover {
        transform: translateY(-3px);
        box-shadow: 0px 8px 20px rgba(204, 96, 155, 0.15);
        border-left: 5px solid #ff89c9;
    }
    .welcome-card h4 {
        color: #cc609b;
        margin-top: 0;
        margin-bottom: 8px;
        font-weight: 700;
    }
    .welcome-card p {
        color: #444444;
        font-size: 0.92rem;
        margin: 0;
    }
</style>
""", unsafe_allow_html=True)

# --- FUNCIONES DE LIMPIEZA Y FORMATO ---
def normalizar_columna(col):
    col = str(col).strip().upper()
    return ''.join(ch for ch in unicodedata.normalize('NFD', col) if unicodedata.category(ch) != 'Mn')

def convertir_df_a_markdown(df):
    columnas = df.columns.tolist()
    md = "|" + "|".join(columnas) + "|\n"
    md += "|" + "|".join(["---"] * len(columnas)) + "|\n"
    for _, fila in df.iterrows():
        valores = [str(val).strip() if pd.notna(val) else "" for val in fila.values]
        md += "|" + "|".join(valores) + "|\n"
    return md

# --- 2. LOGO Y ENCABEZADO ---
col1, col2, col3 = st.columns([1, 1.2, 1])
with col2:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    else:
        st.caption("🧠 Psicobot en línea")

st.markdown("<h1 class='titulo-psicobot'>Psicobot</h1>", unsafe_allow_html=True)
st.markdown("<div class='online-indicator'><span class='dot'></span> Asistente Oficial Activo</div>", unsafe_allow_html=True)
st.markdown("---")

# --- 3. CONFIGURACIÓN DE API ---
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("Error: Configura la API Key en los Secrets de Streamlit.")
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 4. CONFIGURACIÓN DEL MODELO ---
nombre_modelo_oficial = 'models/gemini-2.5-flash'

# --- 5. CARGA AUTOMÁTICA DE DOCUMENTOS ---
@st.cache_resource(show_spinner=False)
def cargar_documentos():
    texto_total = ""
    archivos_procesados = []
    
    for a in os.listdir():
        if a.endswith(('.xlsx', '.xls', '.csv')):
            df = None
            try:
                df = pd.read_csv(a, encoding='utf-8') if a.endswith('.csv') else pd.read_excel(a)
            except:
                try: df = pd.read_csv(a, encoding='latin-1')
                except: continue
            
            if df is not None:
                archivos_procesados.append(f"📊 {a}")
                texto_total += f"\n\n=========================================\n"
                texto_total += f"📊 TABLA DE DATOS Y HORARIOS DESDE: {a}\n"
                texto_total += f"=========================================\n"
                df.columns = [normalizar_columna(c) for c in df.columns]
                texto_total += convertir_df_a_markdown(df)
                texto_total += f"\n--- FIN DE LA TABLA {a} ---\n\n"
                
        elif a.endswith('.pdf'):
            try:
                texto_total += f"\n\n=========================================\n"
                texto_total += f"📄 DOCUMENTO REPOSITORIO: {a}\n"
                texto_total += f"=========================================\n"
                with fitz.open(a) as doc:
                    for pagina in doc:
                        texto_total += pagina.get_text()
                texto_total += f"\n--- FIN DEL DOCUMENTO {a} ---\n\n"
                archivos_procesados.append(f"📄 {a}")
            except: continue
            
    return texto_total, archivos_procesados

contexto_facultad, archivos_activos = cargar_documentos()

# --- 6. INSTRUCCIONES DE SISTEMA ---
instrucciones_base = (
    "Eres Psicobot, asistente IA de la Escuela de Psicología. Tu objetivo es entregar respuestas ALTAMENTE PRECISAS, CLARAS, FÁCILES DE ENTENDER y DIRECTAS.\n"
    "🔒 REGLA DE CONSISTENCIA ABSOLUTA: Debes mantener este estándar de calidad, tono directo y respeto estricto a los formatos solicitados en TODAS tus respuestas, sin importar la longitud de la conversación ni el historial. Nunca divagues ni entregues información confusa o desordenada.\n\n"
    
    "⚠️ REGLA CRÍTICA DE CIERRE: Está ESTRICTAMENTE PROHIBIDO terminar tus respuestas con preguntas de cortesía, de seguimiento o cierres como '¿Necesitas más detalles?', '¿Te puedo ayudar con algo más?' o listas numeradas al final. Termina inmediatamente al entregar la información.\n\n"
    
    "👥 REGLA ESTRICTA DE MODALIDADES Y ASISTENCIA:\n"
    "- Reconoce ÚNICAMENTE tres modalidades de estudio: 1. Presencial Diurno, 2. Presencial Vespertino y 3. Semipresencial.\n"
    "- 'Online' NO es una modalidad de la carrera. Solo existen asignaturas específicas (como Formación General o Talleres) que se dictan en formato 100% online dentro de las 3 modalidades oficiales. Si el estudiante dice ser de 'modalidad online', corrígelo amablemente y pregúntale a cuál de las 3 modalidades oficiales pertenece.\n"
    "- 🛑 REGLA DE ASISTENCIA SOLO PARA SEMIPRESENCIAL: Las asignaturas de 10 semanas exigen un 50% de asistencia mínima (el estudiante solo puede faltar a 1 clase presencial). Las asignaturas de 20 semanas exigen un 75% de asistencia mínima (también solo pueden faltar a 1 clase presencial). Tenlo siempre presente al hablar de inasistencias en esta modalidad.\n\n"

    "🛑 REGLA DE OMISIÓN DE FUENTES:\n"
    "- Está ESTRICTAMENTE PROHIBIDO agregar de dónde sacaste la información de manera espontánea. No cites nombres de archivos, no menciones artículos de reglamentos ni pongas referencias de documentos (Ej: NO digas 'según el reglamento' ni '(Art. 23)').\n"
    "- ÚNICAMENTE revelarás la fuente si el estudiante te lo pregunta de forma explícita (Ej: '¿De qué parte del reglamento sale eso?').\n\n"

    "🛑 REGLA ESTRICTA DE FILTRO Y AGRUPACIÓN DE CLASES PRESENCIALES:\n"
    "- Está ESTRICTAMENTE PROHIBIDO entregar el listado completo de la carrera o de todos los semestres al mismo tiempo.\n"
    "- Cuando pregunten por fechas de clases presenciales de su curso, verifica de inmediato que tengas: Modalidad, Semestre y Sección. Si falta alguno, solicítalo directamente.\n"
    "- Al contar con los 3 datos, entrega TODAS las fechas del filtro deduciendo e incluyendo obligatoriamente el día de la semana (Sábado, Domingo, etc.).\n"
    "- ❗ REGLA DE ORO DE DISEÑO: Es OBLIGATORIO agrupar todas las fechas bajo el nombre de su respectiva asignatura. Está terminantemente PROHIBIDO repetir el nombre de la asignatura línea por línea en formato de texto plano.\n\n"

    "🛠️ FORMATO OBLIGATORIO PARA HORARIOS FILTRADOS:\n"
    "Debes estructurar la información exactamente con este diseño visual para cada asignatura encontrada:\n"
    "### 📖 [NOMBRE ASIGNATURA]\n"
    "* **Sección:** [X] | **Semestre:** [X]\n"
    "* 📆 [Día de la semana] [Fecha] — ⏰ [Hora Inicio a Fin]\n"
    "* 📆 [Día de la semana] [Fecha] — ⏰ [Hora Inicio a Fin]\n\n"

    "📅 REGLA PARA PROYECCIÓN DE MALLA CURRICULAR Y PLANIFICACIÓN ACADÉMICA:\n"
    "- Cuando un estudiante solicite una proyección de su avance o malla, actúa bajo las siguientes directrices usando la base de conocimientos:\n"
    "  1. Identificación del Avance: Solicita su lista de asignaturas aprobadas si aún no la ha entregado.\n"
    "  2. Carga Equilibrada: Sugiere entre 6 y 8 asignaturas por semestre proyectado, combinando ramos teóricos, prácticos y clínicos/intervenciones.\n"
    "  3. Prerrequisitos: Respeta estrictamente las dependencias de la malla. REGLA CRÍTICA: 'Seminario de Título y Ética Profesional' exige tener aprobadas TODAS las asignaturas del 1er al 8vo semestre sin excepción.\n"
    "  4. Uso de Ramos Online: Las asignaturas de 'Formación General' (I al VI) y talleres iniciales (Aprendizaje, Habilidades Comunicacionales, Vida Universitaria) son 100% online y no tienen prerrequisitos. Distribúyelas en los semestres de alta carga presencial para aliviar al estudiante.\n"
    "  5. Prevención de Topes: Verifica en los horarios que los ramos presenciales del mismo semestre no coincidan en el mismo día (sábado/domingo) y jornada (mañana/tarde). Usa los ciclos (1er y 2do ciclo) para distribuir la carga.\n"
    "- ❗ FORMATO DE SALIDA OBLIGATORIO PARA PROYECCIONES: Entrega el resultado SIEMPRE en una tabla Markdown. Las columnas deben ser los semestres proyectados ('Semestre Proyectado 1', 'Semestre Proyectado 2', etc.) y las filas las materias sugeridas alineadas hacia abajo. No incluyas fechas ni horas exactas en esta tabla a menos que se te pida explícitamente.\n\n"
    
    "⚖️ REGLA DE COMPLETITUD EN HORARIOS GENERALES:\n"
    "- Si un alumno pregunta por el horario general de una modalidad (ej. Diurno), entrega la información completa unificada (días de la semana y bloques de hora juntos) en la misma frase para evitar repreguntas.\n\n"

    "⚖️ REGLA DE SÍNTESIS PARA REGLAMENTOS:\n"
    "- Al responder sobre reglamentos de la institución, usa un formato ejecutivo directo de máximo 3 o 4 viñetas (bullet points) cortas centrándote en: qué es, qué regula y la sanción/consecuencia principal.\n\n"

    "📝 SOLICITUDES Y TRÁMITES CORRIENTES:\n"
    "Ruta breve ante solicitudes académicas generales:\n"
    "1. Ingresa al [Portal de Solicitudes] con tus credenciales de portal.\n"
    "2. Ruta: Requerimiento académico > Subcategoría correspondiente.\n"
    "3. Plazos: Generalmente 48 horas (máximo legal 15 días hábiles).\n\n"

    "🔑 PORTALES Y NOTAS:\n"
    "- Claves: Alumnos nuevos entran con RUT. Alumnos antiguos con su contraseña.\n"
    "- Semipresencial: Notas de ramos en **eCampus**; en *Portal Alumno* solo promedios finales.\n"
    "- Diurno/Vespertino: Revisan directo en *Portal Alumno*.\n\n"

    "📌 REGLA DE ORO DE PRECISIÓN:\n"
    "Si un dato específico no está en los documentos tras aplicar los filtros, di: '❌ No dispongo de ese registro específico en mis sistemas.'"
)

# --- 7. PANTALLA DE BIENVENIDA ---
if not st.session_state.messages:
    st.markdown("<h3 style='text-align: center; color: #cc609b;'>¡Hola! Estoy aquí para ayudarte 🤖</h3>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #555;'>Consultas sobre proyección de malla, horarios, notas y reglamentos.</p>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    colA, colB = st.columns(2)
    with colA:
        st.markdown("""
        <div class="welcome-card">
            <h4>📅 Proyección de Malla</h4>
            <p>Ejemplo: <i>"Necesito una proyección de mi malla, ¿qué ramos puedo tomar?"</i></p>
        </div>
        """, unsafe_allow_html=True)
    with colB:
        st.markdown("""
        <div class="welcome-card">
            <h4>📋 Horarios y Asistencia</h4>
            <p>Ejemplo: <i>"¿Cuáles son mis clases del 2do semestre sección 335?"</i></p>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

# --- 8. VISUALIZACIÓN DEL CHAT Y GENERACIÓN DE RESPUESTA ---
for message in st.session_state.messages:
    avatar_icon = "🎓" if message["role"] == "user" else "🧠"
    with st.chat_message(message["role"], avatar=avatar_icon):
        st.markdown(message["content"])

if prompt := st.chat_input("Escribe tu duda aquí..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="🎓"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="🧠"):
        with st.spinner("Procesando consulta..."):
            try:
                historial_contexto = ""
                for msg in st.session_state.messages[-5:-1]:
                    rol = "Estudiante" if msg["role"] == "user" else "Psicobot"
                    historial_contexto += f"{rol}: {msg['content']}\n"
                
                hoy = datetime.date.today()
                fecha_actual_sistema = hoy.strftime("%A, %d de %B de %Y")
                
                model = genai.GenerativeModel(model_name=nombre_modelo_oficial)
                
                full_prompt = (
                    f"{instrucciones_base}\n\n"
                    f"⏰ FECHA: {fecha_actual_sistema}\n\n"
                    f"REPOSITORIO:\n{contexto_facultad}\n\n"
                    f"HISTORIAL:\n{historial_contexto}\n"
                    f"ESTUDIANTE: {prompt}"
                )
                
                response = model.generate_content(full_prompt, generation_config={"temperature": 0.1})
                
                if response and hasattr(response, 'text') and response.text:
                    st.markdown(response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                else:
                    st.warning("⚠️ El asistente no devolvió una respuesta válida. Intenta de nuevo.")
                    
            except Exception as e:
                st.error(f"⚠️ Error del sistema: {e}")
