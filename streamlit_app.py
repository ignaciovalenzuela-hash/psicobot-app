import streamlit as st
import google.generativeai as genai
import fitz  
import pandas as pd  
import os
import unicodedata
import datetime  

# --- NUEVAS LIBRERÍAS PARA RAG (CEREBRO VECTORIAL) ---
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# --- 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS VISUALES ---
st.set_page_config(
    page_title="Psicobot Pro | Fase 2", 
    page_icon="🧠", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# [El CSS se mantiene igual para mantener la identidad visual]
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .titulo-psicobot { background: linear-gradient(45deg, #cc609b, #ff89c9); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-align: center; font-weight: 800; font-size: 3.2rem; margin-bottom: 0rem; }
    .online-indicator { display: flex; justify-content: center; align-items: center; gap: 8px; color: #555; font-size: 0.95rem; margin-top: -5px; margin-bottom: 25px; font-weight: 500; }
    .dot { height: 10px; width: 10px; background-color: #ff89c9; border-radius: 50%; display: inline-block; animation: pulse 2s infinite; }
    @keyframes pulse { 0% { transform: scale(0.9); box-shadow: 0 0 0 0 rgba(255, 137, 201, 0.7); } 70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(255, 137, 201, 0); } 100% { transform: scale(0.9); box-shadow: 0 0 0 0 rgba(255, 137, 201, 0); } }
    .welcome-card { background-color: #ffffff; border-left: 5px solid #cc609b; padding: 18px; border-radius: 8px; box-shadow: 0px 4px 15px rgba(0, 0, 0, 0.05); margin-bottom: 15px; transition: transform 0.3s ease; }
    .welcome-card:hover { transform: translateY(-3px); box-shadow: 0px 8px 20px rgba(204, 96, 155, 0.15); border-left: 5px solid #ff89c9; }
    .welcome-card h4 { color: #cc609b; margin-top: 0; margin-bottom: 8px; font-weight: 700; }
    .welcome-card p { color: #444444; font-size: 0.92rem; margin: 0; }
</style>
""", unsafe_allow_html=True)

# --- VERIFICACIÓN DE API KEY TEMPRANA (REQUERIDA PARA VECTORIZAR) ---
if "GOOGLE_API_KEY" in st.secrets:
    os.environ["GOOGLE_API_KEY"] = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("Error: Configura la API Key en los Secrets de Streamlit.")
    st.stop()

def ejecutar_rerun():
    if hasattr(st, "rerun"): st.rerun()
    else: st.experimental_rerun()

# --- SISTEMA DE LOGS Y ANALÍTICAS GENERALES ---
LOG_FILE = "psicobot_logs.csv"

def registrar_log(pregunta, respuesta, no_registro=False):
    try:
        fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d")
        hora_actual = datetime.datetime.now().strftime("%H:%M:%S")
        nuevo_registro = pd.DataFrame([{ "Fecha": fecha_actual, "Hora": hora_actual, "Pregunta": pregunta, "Respuesta": respuesta, "Vacio_Informacion": "SÍ" if no_registro else "NO", "Feedback": "No evaluado" }])
        if not os.path.exists(LOG_FILE): nuevo_registro.to_csv(LOG_FILE, index=False, encoding='utf-8')
        else: nuevo_registro.to_csv(LOG_FILE, mode='a', header=False, index=False, encoding='utf-8')
    except: pass

def actualizar_ultimo_feedback(tipo_feedback):
    try:
        if os.path.exists(LOG_FILE):
            df = pd.read_csv(LOG_FILE, encoding='utf-8')
            if not df.empty:
                df.at[df.index[-1], 'Feedback'] = tipo_feedback
                df.to_csv(LOG_FILE, index=False, encoding='utf-8')
    except: pass

# --- FUNCIONES DE LIMPIEZA ---
def normalizar_columna(col):
    col = str(col).strip().upper()
    return ''.join(ch for ch in unicodedata.normalize('NFD', col) if unicodedata.category(ch) != 'Mn')

def convertir_df_a_markdown(df):
    columnas = df.columns.tolist()
    md = "|" + "|".join(columnas) + "|\n" + "|" + "|".join(["---"] * len(columnas)) + "|\n"
    for _, fila in df.iterrows():
        valores = [str(val).strip() if pd.notna(val) else "" for val in fila.values]
        md += "|" + "|".join(valores) + "|\n"
    return md

# --- 2. MOTOR RAG: EXTRACCIÓN, CHUNKING Y VECTORIZACIÓN ---
@st.cache_resource(show_spinner=True)
def construir_cerebro_vectorial():
    texto_crudo = ""
    archivos_procesados = []
    
    # 1. Leer documentos
    for a in os.listdir():
        if a.endswith(('.xlsx', '.xls', '.csv')):
            df = None
            try: df = pd.read_csv(a, encoding='utf-8') if a.endswith('.csv') else pd.read_excel(a)
            except: 
                try: df = pd.read_csv(a, encoding='latin-1')
                except: continue
            
            if df is not None:
                archivos_procesados.append(f"📊 {a}")
                df.columns = [normalizar_columna(c) for c in df.columns]
                texto_crudo += f"\n[TABLA: {a}]\n" + convertir_df_a_markdown(df) + "\n"
                
        elif a.endswith('.pdf'):
            try:
                with fitz.open(a) as doc:
                    for pagina in doc:
                        texto_crudo += pagina.get_text() + "\n"
                archivos_procesados.append(f"📄 {a}")
            except: continue
            
    if not texto_crudo.strip():
        return None, archivos_procesados

    # 2. Dividir texto en pedazos manejables (Chunking)
    # 1200 caracteres por chunk con 200 de solapamiento para no cortar ideas por la mitad
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=200)
    chunks = text_splitter.split_text(texto_crudo)

   # 3. Crear Embeddings y almacenar en FAISS (Base de datos vectorial en RAM)
    # Usamos el modelo más reciente y le pasamos la API key de forma explícita
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004",
        google_api_key=st.secrets["GOOGLE_API_KEY"]
    )
    
    # Para evitar saturar la API gratuita de Google de golpe, validamos que haya chunks
    if not chunks:
        return None, archivos_procesados
        
    vectorstore = FAISS.from_texts(chunks, embeddings)
    
    # Para evitar saturar la API gratuita de Google de golpe, validamos que haya chunks
    if not chunks:
        return None, archivos_procesados
        
    vectorstore = FAISS.from_texts(chunks, embeddings)
    
    return vectorstore, archivos_procesados

# Inicializar motor
vectorstore, archivos_activos = construir_cerebro_vectorial()

# --- 3. INSTRUCCIONES BASE (Mantenemos las reglas estrictas) ---
instrucciones_base = (
    "Eres Psicobot, asistente IA de la Escuela de Psicología de UNIACC. Tu objetivo es entregar respuestas ALTAMENTE PRECISAS, CLARAS, FÁCILES DE ENTENDER y DIRECTAS.\n"
    "🔒 REGLA DE CONSISTENCIA ABSOLUTA: Mantén el estándar de calidad y tono directo. Nunca divagues ni entregues información desordenada.\n"
    "🛑 REGLA DE BREVEDAD: Ve directo al grano. Si una respuesta puede darse en un párrafo corto o viñetas breves, hazlo así.\n"
    "⚠️ REGLA DE CIERRE: ESTRICTAMENTE PROHIBIDO terminar con preguntas de cortesía o de seguimiento. Termina inmediatamente al entregar la información.\n"
    "👥 MODALIDADES: Reconoce ÚNICAMENTE Presencial Diurno, Presencial Vespertino y Semipresencial. ('Online' no es modalidad, solo ramos específicos).\n"
    "🛑 REGLA DE ASISTENCIA SEMIPRESENCIAL: Ramos de 10 semanas exigen 50% de asistencia. Ramos de 20 semanas exigen 75%.\n"
    "📅 TOMA DE RAMOS: En Semipresencial existen dos fechas distintas dependiendo del cohorte. En Diurno/Vespertino es una fecha única.\n"
    "❄️ CONGELAMIENTO: 1. Orientación (hablar con Escuela), 2. Advertencia literal: 'Si presentas la solicitud de retiro temporal fuera de los plazos establecidos, tu carga académica no será eliminada y las evaluaciones realizadas durante el periodo serán consideradas para el cálculo del resultado final de las asignaturas (Art. 43).' 3. Procedimiento.\n"
    "🛑 OMISIÓN DE FUENTES: PROHIBIDO agregar de dónde sacaste la información espontáneamente (excepto el Art. 43 obligatorio). Únicamente dalo si el estudiante pregunta.\n"
    "🛑 FILTRO DE HORARIOS: PROHIBIDO entregar todo el listado. Si falta Modalidad, Semestre o Sección, pregúntalo. \n"
    "🛠️ FORMATO PARA HORARIOS:\n"
    "### 📖 [NOMBRE ASIGNATURA]\n* **Sección:** [X] | **Semestre:** [X]\n* 📆 [Día] [Fecha] — ⏰ [Hora]\n"
    "📅 PROYECCIÓN DE MALLA: Sugiere 6-8 ramos, respeta prerrequisitos (Seminario exige 1ero a 8vo aprobado). Entrega siempre en tabla Markdown.\n"
    "⚖️ SÍNTESIS DE REGLAMENTOS: Usa máximo 3 o 4 viñetas (qué es, qué regula, sanción).\n"
    "🔑 ENLACES OBLIGATORIOS:\n- Portal de Solicitudes: [Portal de Solicitudes](https://solicitudes.uniacc.cl/login)\n- Notas finales/Horarios: [Portal Alumno](https://portal.uniacc.cl)\n- Aulas/Ramos Online Semipresencial: [eCampus](https://ecampus.uniacc.cl)\n"
    "📌 REGLA DE PRECISIÓN: Si la información no está en el 'CONTEXTO RECUPERADO', di: '❌ No dispongo de ese registro específico en mis sistemas.'"
)

# --- 4. BARRA LATERAL ---
st.sidebar.markdown("<h2 style='color:#cc609b;'>⚙️ Panel de Control</h2>", unsafe_allow_html=True)
rol_seleccionado = st.sidebar.selectbox("Selecciona tu Rol:", ["Estudiante 🎓", "Escuela (Admin) 🔑"])

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- VISTA DE ESTUDIANTE ---
if rol_seleccionado == "Estudiante 🎓":
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
        else: st.caption("🧠 Psicobot en línea")

    st.markdown("<h1 class='titulo-psicobot'>Psicobot</h1>", unsafe_allow_html=True)
    st.markdown("<div class='online-indicator'><span class='dot'></span> Conectado al Cerebro Vectorial</div>", unsafe_allow_html=True)
    st.markdown("---")

    if not st.session_state.messages:
        st.markdown("<h3 style='text-align: center; color: #cc609b;'>¡Hola! Estoy aquí para ayudarte 🤖</h3>", unsafe_allow_html=True)
        colA, colB = st.columns(2)
        with colA:
            st.markdown("""<div class="welcome-card"><h4>📅 Proyección de Malla</h4><p><i>"Necesito una proyección de mi malla, ¿qué ramos puedo tomar?"</i></p></div>""", unsafe_allow_html=True)
        with colB:
            st.markdown("""<div class="welcome-card"><h4>📋 Horarios y Asistencia</h4><p><i>"¿Cuáles son mis clases del 2do semestre sección 335?"</i></p></div>""", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

    for message in st.session_state.messages:
        avatar_icon = "🎓" if message["role"] == "user" else "🧠"
        with st.chat_message(message["role"], avatar=avatar_icon):
            st.markdown(message["content"])

    if prompt := st.chat_input("Escribe tu duda aquí..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        ejecutar_rerun()

    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        prompt_actual = st.session_state.messages[-1]["content"]
            
        with st.chat_message("assistant", avatar="🧠"):
            with st.spinner("Buscando en la base de datos..."):
                try:
                    # 🔍 1. BÚSQUEDA SEMÁNTICA (RAG): Recuperamos solo los fragmentos relevantes
                    contexto_recuperado = ""
                    if vectorstore is not None:
                        # Extrae los 5 fragmentos más similares a la pregunta del usuario
                        documentos_similares = vectorstore.similarity_search(prompt_actual, k=5)
                        contexto_recuperado = "\n\n...\n\n".join([doc.page_content for doc in documentos_similares])
                    else:
                        contexto_recuperado = "No hay documentos cargados en el sistema."

                    # 2. Preparar el historial reciente
                    historial_contexto = ""
                    for msg in st.session_state.messages[-5:-1]:
                        rol_ctx = "Estudiante" if msg["role"] == "user" else "Psicobot"
                        historial_contexto += f"{rol_ctx}: {msg['content']}\n"
                    
                    fecha_actual_sistema = datetime.date.today().strftime("%A, %d de %B de %Y")
                    
                    # 3. Construir el Prompt Final (Solo con la info necesaria)
                    full_prompt = (
                        f"{instrucciones_base}\n\n"
                        f"⏰ FECHA: {fecha_actual_sistema}\n\n"
                        f"CONTEXTO RECUPERADO DE LA BASE DE DATOS:\n{contexto_recuperado}\n\n"
                        f"HISTORIAL DE LA CONVERSACIÓN:\n{historial_contexto}\n"
                        f"ESTUDIANTE: {prompt_actual}"
                    )
                    
                    # 4. Generación con Gemini
                    model = genai.GenerativeModel('models/gemini-2.5-flash')
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

    # Sistema de Feedback
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
        
        # Muestra los documentos que el motor vectorial logró indexar
        with st.expander("📂 Estado del Cerebro Vectorial (Archivos Indexados)"):
            if archivos_activos:
                for arc in archivos_activos:
                    st.write(arc)
            else:
                st.warning("No se encontraron documentos en el directorio para indexar.")
        
        if os.path.exists(LOG_FILE):
            try:
                df_logs = pd.read_csv(LOG_FILE, encoding='utf-8')
                total_consultas = len(df_logs)
                vacios_info = len(df_logs[df_logs["Vacio_Informacion"] == "SÍ"])
                feedback_positivo = len(df_logs[df_logs["Feedback"] == "Útil (Positivo)"])
                
                kpi1, kpi2, kpi3 = st.columns(3)
                with kpi1: st.metric(label="Total Consultas Alumnos", value=total_consultas)
                with kpi2: st.metric(label="⚠️ Alertas de Vacíos", value=vacios_info)
                with kpi3: st.metric(label="Valoraciones Positivas (👍)", value=feedback_positivo)
                
                st.markdown("---")
                st.markdown("### 📈 Volumen Diario de Consultas")
                if "Fecha" in df_logs.columns and not df_logs.empty:
                    conteo_fechas = df_logs["Fecha"].value_counts().sort_index()
                    st.bar_chart(conteo_fechas)
                
                st.markdown("---")
                st.markdown("### 📋 Historial Completo de Interacciones")
                st.dataframe(df_logs, use_container_width=True)
            except Exception as ex_panel:
                st.error(f"Error temporal al leer el archivo de analíticas: {ex_panel}")
        else:
            st.info("Aún no se registran interacciones.")
