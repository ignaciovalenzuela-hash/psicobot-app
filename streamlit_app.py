import streamlit as st
import google.generativeai as genai
import fitz  # Para los PDFs (PyMuPDF)
import pandas as pd  # Para el Excel y analíticas
import os
import unicodedata
import datetime  # Mantiene la noción del tiempo real

# --- 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS VISUALES PERSONALIZADOS (CSS) ---
st.set_page_config(
    page_title="Psicobot Pro", 
    page_icon="🧠", 
    layout="wide",
    initial_sidebar_state="expanded"  # Fuerza a que el menú lateral aparezca abierto
)

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

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

# --- SISTEMA DE LOGS Y ANALÍTICAS GENERALES ---
LOG_FILE = "psicobot_logs.csv"

def registrar_log(pregunta, respuesta, no_registro=False):
    fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d")
    hora_actual = datetime.datetime.now().strftime("%H:%M:%S")
    nuevo_registro = pd.DataFrame([{
        "Fecha": fecha_actual,
        "Hora": hora_actual,
        "Pregunta": pregunta,
        "Respuesta": respuesta,
        "Vacio_Informacion": "SÍ" if no_registro else "NO",
        "Feedback": "No evaluado"
    }])
    if not os.path.exists(LOG_FILE):
        nuevo_registro.to_csv(LOG_FILE, index=False, encoding='utf-8')
    else:
        nuevo_registro.to_csv(LOG_FILE, mode='a', header=False, index=False, encoding='utf-8')

def actualizar_ultimo_feedback(tipo_feedback):
    if os.path.exists(LOG_FILE):
        df = pd.read_csv(LOG_FILE, encoding='utf-8')
        if not df.empty:
            df.at[df.index[-1], 'Feedback'] = tipo_feedback
            df.to_csv(LOG_FILE, index=False, encoding='utf-8')

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

# --- 2. CARGA AUTOMÁTICA DE DOCUMENTOS ---
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

# --- 3. CONFIGURACIÓN DE INSTRUCCIONES BASE ---
instrucciones_base = (
    "Eres Psicobot, asistente IA de la Escuela de Psicología de UNIACC. Tu objetivo es entregar respuestas ALTAMENTE PRECISAS, CLARAS, FÁCILES DE ENTENDER y DIRECTAS.\n"
    "🔒 REGLA DE CONSISTENCIA ABSOLUTA: Debes mantener este estándar de calidad, tono directo y respeto estricto a los formatos solicitados en TODAS tus respuestas, sin importar la longitud de la conversación ni el historial. Nunca divagues ni entregues información confusa o desordenada.\n\n"
    
    "🛑 REGLA DE BREVEDAD Y CONCISIÓN EXTREMA:\n"
    "- Está ESTRICTAMENTE PROHIBIDO entregar respuestas extensas, detalladas en exceso o con introducciones largas. Ve directo al grano. El exceso de texto confunde al estudiante. Si una respuesta puede darse en un párrafo corto o un par de viñetas breves, hazlo así.\n\n"

    "⚠️ REGLA CRÍTICA DE CIERRE: Está ESTRICTAMENTE PROHIBIDO terminar tus respuestas con preguntas de cortesía, de seguimiento o cierres como '¿Necesitas más detalles?', '¿Te puedo ayudar con algo más?' o listas numeradas al final. Termina inmediatamente al entregar la información.\n\n"
    
    "👥 REGLA ESTRICTA DE MODALIDADES, ASISTENCIA Y TOMA DE RAMOS:\n"
    "- Reconoce ÚNICAMENTE tres modalidades de estudio: 1. Presencial Diurno, 2. Presencial Vespertino y 3. Semipresencial.\n"
    "- 'Online' NO es una modalidad de la carrera. Solo existen asignaturas específicas (como Formación General o Talleres) que se dictan en formato 100% online dentro de las 3 modalidades oficiales. Si el estudiante dice ser de 'modalidad online', corrígelo amablemente y pregúntale a cuál de las 3 modalidades oficiales pertenece.\n"
    "- 🛑 REGLA DE ASISTENCIA SOLO PARA SEMIPRESENCIAL: Las asignaturas de 10 semanas exigen un 50% de asistencia mínima (el estudiante solo puede faltar a 1 clase presencial). Las asignaturas de 20 semanas exigen un 75% de asistencia mínima (también solo pueden faltar a 1 clase presencial).\n"
    "- 📅 REGLA CRÍTICA PARA TOMA DE RAMOS: Al informar las fechas de toma de ramos (inscripción de asignaturas), sé sumamente cuidadoso:\n"
    "  * Para la modalidad **Semipresencial**, existen estrictamente **dos fechas diferentes dependiendo del cohorte** del estudiante. Debes especificar ambas fechas indicando a qué cohorte corresponde cada una, o pedir al estudiante que te indique su cohorte.\n"
    "  * Para las modalidades **Presencial Diurno** y **Presencial Vespertino**, entrega la fecha exactas que corresponda según los documentos oficiales, sin mezclarlas ni confundirlas entre sí.\n\n"

    "❄️ REGLA OBLIGATORIA PARA CONGELAMIENTO (RETIRO TEMPORAL):\n"
    "- Cuando un estudiante pregunte por congelamiento, cómo congelar o retiro temporal, debes estructurar la respuesta siguiendo estrictamente este orden jerárquico:\n"
    "  1. **Orientación de Acompañamiento:** Antes de dar los pasos operativos, indícale de forma clara que antes de congelar puede contactarse directamente con la Escuela para revisar diferentes opciones y apoyos personalizados que se le pueden brindar para continuar sus estudios y evitar la suspensión.\n"
    "  2. **Advertencia de Plazos Extratemporales:** Advierte explícitamente sobre los plazos normativos incluyendo exactamente la siguiente frase textual: \"Si presentas la solicitud de retiro temporal fuera de los plazos establecidos, tu carga académica no será eliminada y las evaluaciones realizadas durante el periodo serán consideradas para el cálculo del resultado final de las asignaturas (Art. 43).\"\n"
    "  3. **Procedimiento Operativo:** Entrega los pasos breves para ingresar el requerimiento a través del respectivo portal.\n\n"

    "🛑 REGLA DE OMISIÓN DE FUENTES:\n"
    "- Está ESTRICTAMENTE PROHIBIDO agregar de dónde sacaste la información de manera espontánea. No cites nombres de archivos ni pongas referencias de documentos (Ej: NO digas 'según el reglamento' ni '(Art. 23)').\n"
    "- 🚨 EXCEPCIÓN ÚNICA: Se autoriza y exige mostrar el '(Art. 43)' únicamente dentro de la frase literal obligatoria de la regla de congelamiento.\n"
    "- ÚNICAMENTE revelarás otra fuente si el estudiante te lo pregunta de forma explícita (Ej: '¿De qué parte del reglamento sale eso?').\n\n"

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
    "1. Ingresa al [Portal de Solicitudes](https://solicitudes.uniacc.cl/login) con tus credenciales de portal.\n"
    "2. Ruta: Requerimiento académico > Subcategoría correspondiente.\n"
    "3. Plazos: Generalmente 48 horas (máximo legal 15 días hábiles).\n\n"

    "🔑 PORTALES Y ENLACES OBLIGATORIOS (BLINDAJE DE LINKS):\n"
    "- 🔗 REGLA DE ENLACES ESTRICTOS: Queda terminantemente PROHIBIDO inventar, omitir, truncar o usar URLs distintas a las configuradas a continuación. Cada vez que tu respuesta implique realizar una acción en una plataforma, debes incrustar de forma obligatoria el enlace Markdown hipervinculado con los siguientes destinos exactos de UNIACC:\n"
    "  * Para gestionar trámites, retiros o requerimientos académicos institucionales: [Portal de Solicitudes](https://solicitudes.uniacc.cl/login)\n"
    "  * Para revisar horarios presenciales, avance curricular y notas finales de Diurno/Vespertino: [Portal Alumno](https://portal.uniacc.cl)\n"
    "  * Para acceder a aulas virtuales, evaluaciones continuas y asignaturas online de Semipresencial: [eCampus](https://ecampus.uniacc.cl)\n"
    "- Claves: Alumnos nuevos entran con RUT. Alumnos antiguos con su contraseña.\n"
    "- Semipresencial: Notas de ramos en [eCampus](https://ecampus.uniacc.cl); en [Portal Alumno](https://portal.uniacc.cl) solo promedios finales.\n"
    "- Diurno/Vespertino: Revisan directo en [Portal Alumno](https://portal.uniacc.cl).\n\n"

    "📌 REGLA DE ORO DE PRECISIÓN:\n"
    "Si un dato específico no está en los documentos tras aplicar los filtros, di: '❌ No dispongo de ese registro específico en mis sistemas.'"
)

# --- 4. BARRA LATERAL (NAVEGACIÓN DE ROLES Y FILTROS DINÁMICOS) ---
st.sidebar.markdown("<h2 style='color:#cc609b;'>⚙️ Panel de Control</h2>", unsafe_allow_html=True)
rol_seleccionado = st.sidebar.selectbox("Selecciona tu Rol:", ["Estudiante 🎓", "Escuela (Admin) 🔑"])

# Inicializar estados de chat obligatorios
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- VISTA DE ESTUDIANTE ---
if rol_seleccionado == "Estudiante 🎓":
    st.sidebar.markdown("---")
    st.sidebar.markdown("<h4 style='color:#cc609b;'>🔍 Filtro Rápido de Horarios</h4>", unsafe_allow_html=True)
    st.sidebar.caption("Usa estos controles dinámicos para armar tu consulta automáticamente.")
    
    mod_ui = st.sidebar.selectbox("Modalidad:", ["Presencial Diurno", "Presencial Vespertino", "Semipresencial"])
    sem_ui = st.sidebar.text_input("Semestre (Ej: 2)", value="")
    sec_ui = st.sidebar.text_input("Sección (Ej: 335)", value="")
    
    if st.sidebar.button("Generar Consulta de Horario"):
        if sem_ui and sec_ui:
            prompt_automatico = f"¿Cuáles son mis clases del semestre {sem_ui} sección {sec_ui} en la modalidad {mod_ui}?"
            st.session_state.messages.append({"role": "user", "content": prompt_automatico})
        else:
            st.sidebar.warning("Por favor rellena Semestre y Sección.")

    # Encabezado Principal
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        if os.path.exists("logo.png"):
            st.image("logo.png", use_container_width=True)
        else:
            st.caption("🧠 Psicobot en línea")

    st.markdown("<h1 class='titulo-psicobot'>Psicobot</h1>", unsafe_allow_html=True)
    st.markdown("<div class='online-indicator'><span class='dot'></span> Asistente Oficial Activo</div>", unsafe_allow_html=True)
    st.markdown("---")

    # API configuration
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    else:
        st.error("Error: Configura la API Key en los Secrets de Streamlit.")
        st.stop()

    # Pantalla de Bienvenida Inicial
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

    # Renderizar historial de chat
    for message in st.session_state.messages:
        avatar_icon = "🎓" if message["role"] == "user" else "🧠"
        with st.chat_message(message["role"], avatar=avatar_icon):
            st.markdown(message["content"])

    # Captura de nueva consulta
    if prompt := st.chat_input("Escribe tu duda aquí..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()

    # Si hay mensajes y el último es del usuario, generar respuesta
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        prompt_actual = st.session_state.messages[-1]["content"]
        
        # Forzar render visual inmediato del input del usuario
        with st.chat_message("user", avatar="🎓"):
            st.markdown(prompt_actual)
            
        with st.chat_message("assistant", avatar="🧠"):
            with st.spinner("Procesando consulta..."):
                try:
                    historial_contexto = ""
                    for msg in st.session_state.messages[-5:-1]:
                        rol_ctx = "Estudiante" if msg["role"] == "user" else "Psicobot"
                        historial_contexto += f"{rol_ctx}: {msg['content']}\n"
                    
                    hoy = datetime.date.today()
                    fecha_actual_sistema = hoy.strftime("%A, %d de %B de %Y")
                    
                    nombre_modelo_oficial = 'models/gemini-2.5-flash'
                    model = genai.GenerativeModel(model_name=nombre_modelo_oficial)
                    
                    full_prompt = (
                        f"{instrucciones_base}\n\n"
                        f"⏰ FECHA: {fecha_actual_sistema}\n\n"
                        f"REPOSITORIO:\n{contexto_facultad}\n\n"
                        f"HISTORIAL:\n{historial_contexto}\n"
                        f"ESTUDIANTE: {prompt_actual}"
                    )
                    
                    response = model.generate_content(full_prompt, generation_config={"temperature": 0.1})
                    
                    if response and hasattr(response, 'text') and response.text:
                        respuesta_texto = response.text
                        st.markdown(respuesta_texto)
                        st.session_state.messages.append({"role": "assistant", "content": respuesta_texto})
                        
                        # Guardar logs de analíticas de forma desatendida
                        es_vacio = "❌ No dispongo de ese registro" in respuesta_texto
                        registrar_log(prompt_actual, respuesta_texto, no_registro=es_vacio)
                        st.rerun()
                    else:
                        st.warning("⚠️ El asistente no devolvió una respuesta válida. Intenta de nuevo.")
                        
                except Exception as e:
                    st.error(f"⚠️ Error del sistema: {e}")

    # Sistema Dinámico de Feedback para la última respuesta del asistente
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
        st.write("---")
        st.caption("¿Te fue útil esta respuesta?")
        col_feed1, col_feed2, _ = st.columns([1, 1, 8])
        with col_feed1:
            if st.button("👍 Sí"):
                actualizar_ultimo_feedback("Útil (Positivo)")
                st.success("¡Gracias por tu feedback!")
        with col_feed2:
            if st.button("👎 No"):
                actualizar_ultimo_feedback("No útil (Negativo)")
                st.error("Registrado. Trabajaremos en mejorarlo.")

# --- VISTA DE ADMINISTRACIÓN (ESCUELA) ---
elif rol_seleccionado == "Escuela (Admin) 🔑":
    st.markdown("<h1 style='color:#cc609b;'>📊 Panel de Analíticas Institucionales</h1>", unsafe_allow_html=True)
    st.markdown("Clave de acceso de prueba: `psico2026`")
    
    password = st.text_input("Introduce la contraseña de acceso:", type="password")
    if password == "psico2026":
        st.success("Acceso Autorizado.")
        st.markdown("---")
        
        if os.path.exists(LOG_FILE):
            df_logs = pd.read_csv(LOG_FILE, encoding='utf-8')
            
            # 1. Métricas clave (KPIs)
            total_consultas = len(df_logs)
            vacios_info = len(df_logs[df_logs["Vacio_Informacion"] == "SÍ"])
            feedback_positivo = len(df_logs[df_logs["Feedback"] == "Útil (Positivo)"])
            
            kpi1, kpi2, kpi3 = st.columns(3)
            with kpi1:
                st.metric(label="Total Consultas Alumnos", value=total_consultas)
            with kpi2:
                st.metric(label="⚠️ Alertas de Vacíos de Información", value=vacios_info, delta="Acción requerida" if vacios_info > 0 else "Todo cubierto")
                st.caption("Frecuencia con la que el bot activó la regla 'No dispongo de ese registro'.")
            with kpi3:
                st.metric(label="Valoraciones Positivas (👍)", value=feedback_positivo)
            
            st.markdown("---")
            
            # 2. Gráficos de tendencias temporales
            st.markdown("### 📈 Volumen Diario de Consultas")
            if "Fecha" in df_logs.columns and not df_logs.empty:
                conteo_fechas = df_logs["Fecha"].value_counts().sort_index()
                st.bar_chart(conteo_fechas)
            
            st.markdown("---")
            
            # 3. Registro bruto de auditoría
            st.markdown("### 📋 Historial Completo de Interacciones")
            st.dataframe(df_logs, use_container_width=True)
            
        else:
            st.info("Aún no se registran interacciones en los logs para mostrar analíticas.")
            
    elif password != "":
        st.error("Contraseña incorrecta. Inténtalo nuevamente.")
