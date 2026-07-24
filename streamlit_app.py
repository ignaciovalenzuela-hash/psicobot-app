import streamlit as st
import google.generativeai as genai
import pypdf  # Reemplazo seguro de fitz para evitar caídas del sistema
import pandas as pd  # Para el Excel y analíticas
import os
import unicodedata
import datetime  # Mantiene la noción del tiempo real
import base64 # NUEVO: Para procesar el video en la interfaz

# --- 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS VISUALES PERSONALIZADOS (CSS) ---
st.set_page_config(
    page_title="Psicobot Pro", 
    page_icon="🧠", 
    layout="wide",
    initial_sidebar_state="expanded"
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

# --- FUNCIÓN DE CONTROL DE RERUN SEGURO ---
def ejecutar_rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()

# --- SISTEMA DE LOGS Y ANALÍTICAS GENERALES ---
LOG_FILE = "psicobot_logs.csv"

def registrar_log(pregunta, respuesta, no_registro=False):
    try:
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
    except Exception as e:
        pass

def actualizar_ultimo_feedback(tipo_feedback):
    try:
        if os.path.exists(LOG_FILE):
            df = pd.read_csv(LOG_FILE, encoding='utf-8')
            if not df.empty:
                df.at[df.index[-1], 'Feedback'] = tipo_feedback
                df.to_csv(LOG_FILE, index=False, encoding='utf-8')
    except Exception as e:
        pass

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


# --- 2. CARGA AUTOMÁTICA DE DOCUMENTOS (ACTUALIZADA PARA CACHÉ DINÁMICO) ---
def obtener_lista_archivos():
    """Genera una tupla con los archivos del directorio para invalidar caché si hay cambios."""
    return tuple(sorted(os.listdir()))

@st.cache_data(show_spinner=False)
def cargar_documentos(lista_archivos):
    texto_total = ""
    archivos_procesados = []
    
    for a in lista_archivos:
        # Forzar lectura en minúscula para evitar que ignore ".PDF"
        a_lower = a.lower()
        if a_lower.endswith(('.xlsx', '.xls', '.csv')):
            df = None
            try:
                df = pd.read_csv(a, encoding='utf-8') if a_lower.endswith('.csv') else pd.read_excel(a)
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
                
        elif a_lower.endswith('.pdf'):
            try:
                texto_total += f"\n\n=========================================\n"
                texto_total += f"📄 DOCUMENTO REPOSITORIO: {a}\n"
                texto_total += f"=========================================\n"
                
                lector_pdf = pypdf.PdfReader(a)
                for pagina in lector_pdf.pages:
                    texto_pagina = pagina.extract_text()
                    if texto_pagina:
                        texto_total += texto_pagina + "\n"
                        
                texto_total += f"\n--- FIN DEL DOCUMENTO {a} ---\n\n"
                archivos_procesados.append(f"📄 {a}")
            except: continue
            
    return texto_total, archivos_procesados

# Ahora al inyectar la función, Streamlit vigilará el directorio
contexto_facultad, archivos_activos = cargar_documentos(obtener_lista_archivos())


# --- 3. CONFIGURACIÓN DE INSTRUCCIONES BASE ---
instrucciones_base = (
    "Eres Psicobot, asistente IA de la Escuela de Psicología de UNIACC. Tu objetivo es entregar respuestas ALTAMENTE PRECISAS, CLARAS, FÁCILES DE ENTENDER y DIRECTAS.\n"
    "🔒 REGLA DE CONSISTENCIA ABSOLUTA: Debes mantener este estándar de calidad, tono directo y respeto estricto a los formatos solicitados en TODAS tus respuestas. Nunca divagues ni entregues información confusa o desordenada.\n\n"
    
    "🛑 REGLA ANTI-ALUCINACIÓN Y PENSAMIENTOS INTERNOS (CRÍTICA): JAMÁS debes incluir tus razonamientos internos, notas, explicaciones de tus reglas, traducciones al inglés o debates sobre cómo resolver un conflicto de instrucciones en la respuesta final. Si tienes un conflicto, resuélvelo en silencio y entrega ÚNICAMENTE la respuesta final directa al estudiante en español.\n\n"

    "🛑 REGLA DE BREVEDAD Y CONCISIÓN EXTREMA:\n"
    "- PROHIBIDO entregar respuestas extensas o introducciones largas. Ve directo al grano.\n"
    "- PROHIBIDO terminar tus respuestas con preguntas de cortesía (ej. '¿Te ayudo en algo más?'). Termina inmediatamente al entregar la información.\n\n"
    
    "👥 REGLA ESTRICTA DE MODALIDADES Y ASISTENCIA:\n"
    "- 3 modalidades oficiales: 1. Presencial Diurno, 2. Presencial Vespertino y 3. Semipresencial.\n"
    "- 'Online' NO es modalidad, solo formato de ciertas asignaturas. Corrige amablemente si el alumno dice ser 'online'.\n"
    "- Asistencia Semipresencial: Ramos 10 semanas (50% min, 1 falta). Ramos 20 semanas (75% min, 1 falta).\n\n"

    "📅 REGLA CRÍTICA PARA TOMA DE RAMOS:\n"
    "- La toma de ramos (inscripción de asignaturas) NO se hace a través del portal de solicitudes.\n"
    "- Se realiza EXCLUSIVAMENTE a través del [Portal Alumno](https://portal.uniacc.cl) en la sección de 'Inscripción de asignaturas' que aparece en la pantalla principal.\n"
    "- Debes advertir siempre que esta sección NO se habilitará hasta que sea la fecha y horario indicados.\n"
    "- Para Semipresencial: hay dos fechas diferentes según cohorte (pide el cohorte o informa ambas).\n"
    "- Para Diurno/Vespertino: entrega la fecha exacta oficial sin mezclar modalidades.\n\n"

    "📜 REGLA DE SOLICITUD DE CERTIFICADOS:\n"
    "- Los certificados se gestionan de manera autónoma vía [Soluciones UNIACC](http://soluciones.uniacc.cl).\n"
    "- Ingreso: RUT completo (sin guion) y la misma clave del portal del estudiante.\n"
    "- Soporte: En caso de inconvenientes, escribir a certificados@uniacc.cl.\n\n"
    
    "💼 REGLA PARA DATOS DE EMPLEABILIDAD:\n"
    "- Al hablar de empleabilidad o el futuro laboral de la carrera, enfócate ÚNICAMENTE en los datos duros, cifras y resultados positivos para el egresado.\n"
    "- Mantén un tono sumamente optimista, motivador y profesional.\n"
    "- Está ESTRICTAMENTE PROHIBIDO mencionar de dónde se sacaron los datos, la metodología del estudio, si hubo entrevistas, focus groups o a quiénes se entrevistó.\n\n"

    "❄️ REGLA OBLIGATORIA PARA CONGELAMIENTO (RETIRO TEMPORAL):\n"
    "Orden jerárquico estricto:\n"
    "1. Orientación: Sugerir contacto con la Escuela para apoyo antes de suspender.\n"
    "2. Advertencia literal obligatoria: \"Si presentas la solicitud de retiro temporal fuera de los plazos establecidos, tu carga académica no será eliminada y las evaluaciones realizadas durante el periodo serán consideradas para el cálculo del resultado final de las asignaturas (Art. 43).\"\n"
    "3. Pasos: Derivar al [Portal de Solicitudes](https://solicitudes.uniacc.cl/login).\n\n"

    "🛑 REGLA DE OMISIÓN DE FUENTES:\n"
    "- PROHIBIDO nombrar el archivo de origen (ej. 'según el pdf' o '(Art. 23)'). Excepción: el Art. 43 del congelamiento.\n\n"

    "🛑 REGLA ESTRICTA DE HORARIOS PRESENCIALES Y PROYECCIÓN DE MALLA:\n"
    "- Para horarios: pide Modalidad, Semestre y Sección. Agrupa todas las fechas bajo el nombre de la asignatura (NO repitas el nombre de la materia línea por línea). Usa el formato visual con emojis 📖, 📆 y ⏰.\n"
    "- Para mallas: Pide ramos aprobados. Sugiere 6-8 ramos (mezclando teóricos, prácticos, online). Recuerda que 'Seminario de Título y Ética Profesional' exige TODO aprobado del 1er al 8vo semestre. Entrega SIEMPRE en tabla Markdown.\n\n"

    "🔑 PORTALES Y ENLACES OBLIGATORIOS (BLINDAJE DE LINKS):\n"
    "- PROHIBIDO inventar URLs. Usa solo estas:\n"
    "  * Trámites, justificativos y requerimientos: [Portal de Solicitudes](https://solicitudes.uniacc.cl/login)\n"
    "  * Horarios, toma de ramos y notas (Diurno/Vesp): [Portal Alumno](https://portal.uniacc.cl)\n"
    "  * Aulas virtuales y notas (Semipresencial): [eCampus](https://ecampus.uniacc.cl)\n"
    "  * Certificados: [Soluciones UNIACC](http://soluciones.uniacc.cl)\n\n"

    "📌 REGLA DE ORO DE PRECISIÓN (CUANDO NO HAY INFORMACIÓN):\n"
    "Si un dato específico no está en los documentos, está ESTRICTAMENTE PROHIBIDO inventarlo. Debes responder EXACTAMENTE con el siguiente texto:\n"
    "' 🎓 Esa información no está disponible o no dispongo de ese registro específico en mis sistemas. Sin embargo, puedes contactar a la Escuela a través de tus secretarios académicos o ingresando una solicitud en el [Portal de Solicitudes](https://solicitudes.uniacc.cl/login).'"
)

# --- 4. BARRA LATERAL (NAVEGACIÓN DE ROLES LIMPIA) ---
st.sidebar.markdown("<h2 style='color:#cc609b;'>⚙️ Panel de Control</h2>", unsafe_allow_html=True)
rol_seleccionado = st.sidebar.selectbox("Selecciona tu Rol:", ["Estudiante 🎓", "Escuela (Admin) 🔑"])

# Inicializar estados de chat obligatorios
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- VISTA DE ESTUDIANTE ---
if rol_seleccionado == "Estudiante 🎓":
    # Encabezado Principal (ACTUALIZADO PARA VIDEO LOGO)
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        if os.path.exists("logo.mp4"):
            with open("logo.mp4", "rb") as video_file:
                video_bytes = video_file.read()
            video_base64 = base64.b64encode(video_bytes).decode("utf-8")
            st.markdown(f'''
                <video width="100%" autoplay loop muted playsinline style="border-radius: 8px; pointer-events: none;">
                    <source src="data:video/mp4;base64,{video_base64}" type="video/mp4">
                </video>
            ''', unsafe_allow_html=True)
        elif os.path.exists("logo.png"):
            st.image("logo.png", width="stretch") 
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

    # Renderizar historial completo de chat
    for message in st.session_state.messages:
        avatar_icon = "🎓" if message["role"] == "user" else "🧠"
        with st.chat_message(message["role"], avatar=avatar_icon):
            st.markdown(message["content"])

    # Captura de nueva consulta desde el cuadro inferior
    if prompt := st.chat_input("Escribe tu duda aquí..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        ejecutar_rerun()

    # Procesar la respuesta del asistente
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        prompt_actual = st.session_state.messages[-1]["content"]
            
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
                        
                        es_vacio = "❌ No dispongo de ese registro" in respuesta_texto
                        registrar_log(prompt_actual, respuesta_texto, no_registro=es_vacio)
                        ejecutar_rerun()
                    else:
                        st.warning("⚠️ El asistente no devolvió una respuesta válida. Intenta de nuevo.")
                        
                except Exception as e:
                    st.error(f"⚠️ Error del sistema: {e}")

    # --- SISTEMA DINÁMICO DE FEEDBACK ---
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
        ultimo_msg = st.session_state.messages[-1]
        st.write("---")
        
        if "feedback_enviado" not in ultimo_msg:
            st.caption("¿Te fue útil esta respuesta?")
            col_feed1, col_feed2, _ = st.columns([1, 1, 8])
            id_llave = len(st.session_state.messages)
            
            with col_feed1:
                if st.button("👍 Sí", key=f"feed_si_{id_llave}"):
                    actualizar_ultimo_feedback("Útil (Positivo)")
                    ultimo_msg["feedback_enviado"] = "positivo"
                    ejecutar_rerun()
            with col_feed2:
                if st.button("👎 No", key=f"feed_no_{id_llave}"):
                    actualizar_ultimo_feedback("No útil (Negativo)")
                    ultimo_msg["feedback_enviado"] = "negativo"
                    ejecutar_rerun()
        else:
            if ultimo_msg["feedback_enviado"] == "positivo":
                st.success("¡Gracias por tu feedback! (👍 Valoración Positiva Guardada)")
            else:
                st.error("Registrado. Trabajaremos en mejorarlo. (👎 Valoración Negativa Guardada)")

# --- VISTA DE ADMINISTRACIÓN (ESCUELA) ---
elif rol_seleccionado == "Escuela (Admin) 🔑":
    st.markdown("<h1 style='color:#cc609b;'>📊 Panel de Analíticas Institucionales</h1>", unsafe_allow_html=True)
    st.markdown("Clave de acceso de prueba: `psico2026`")
    
    password = st.text_input("Introduce la contraseña de acceso:", type="password")
    if password == "psico2026":
        st.success("Acceso Autorizado.")
        st.markdown("---")
        
        if os.path.exists(LOG_FILE):
            try:
                df_logs = pd.read_csv(LOG_FILE, encoding='utf-8')
                
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
                
                st.markdown("### 📈 Volumen Diario de Consultas")
                if "Fecha" in df_logs.columns and not df_logs.empty:
                    conteo_fechas = df_logs["Fecha"].value_counts().sort_index()
                    st.bar_chart(conteo_fechas)
                
                st.markdown("---")
                
                # 3. Registro bruto de auditoría
                st.markdown("### 📋 Historial Completo de Interacciones")
                st.dataframe(df_logs, width="stretch")
            except Exception as ex_panel:
                st.error(f"Error temporal al leer el archivo de analíticas: {ex_panel}")
            
        else:
            st.info("Aún no se registran interacciones en los logs para mostrar analíticas.")
            
    elif password != "":
        st.error("Contraseña incorrecta. Inténtalo nuevamente.")
