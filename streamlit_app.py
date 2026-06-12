import streamlit as st
import google.generativeai as genai
import fitz  # Para los PDFs
import pandas as pd  # Para el Excel
import os
import unicodedata
import datetime  # Para darle noción del tiempo real al bot

# --- 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS VISUALES (CSS) ---
st.set_page_config(page_title="Psicobot", page_icon="🧠", layout="centered")

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    div[data-testid="stNotification"] {
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        border-radius: 10px;
    }
    div[data-testid="stNotification"]:hover {
        transform: translateY(-4px);
        box-shadow: 0px 10px 25px rgba(0, 0, 0, 0.1);
    }

    .titulo-psicobot {
        background: linear-gradient(45deg, #1e3d59, #17b890);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        font-weight: 800;
        font-size: 3rem;
        margin-bottom: 0rem;
    }

    .online-indicator {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 8px;
        color: #555;
        font-size: 0.92rem;
        margin-top: -5px;
        margin-bottom: 15px;
        font-weight: 500;
    }
    .dot {
        height: 9px;
        width: 9px;
        background-color: #17b890;
        border-radius: 50%;
        display: inline-block;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0% { transform: scale(0.9); box-shadow: 0 0 0 0 rgba(23, 184, 144, 0.7); }
        70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(23, 184, 144, 0); }
        100% { transform: scale(0.9); box-shadow: 0 0 0 0 rgba(23, 184, 144, 0); }
    }
</style>
""", unsafe_allow_html=True)

def normalizar_columna(col):
    col = str(col).strip().upper()
    return ''.join(ch for ch in unicodedata.normalize('NFD', col) if unicodedata.category(ch) != 'Mn')

def limpiar_celda_texto(val):
    if pd.isna(val): return ""
    texto = str(val).strip()
    if texto.endswith('.0'): texto = texto[:-2]
    return texto

# --- 2. LOGO Y ENCABEZADO ---
col1, col2, col3 = st.columns([1, 1.2, 1])
with col2:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    else:
        st.caption("🚀 Psicobot en línea")

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
@st.cache_resource(show_spinner=False)
def obtener_modelo_flash_activo():
    try:
        modelos_disponibles = list(genai.list_models())
        for m in modelos_disponibles:
            if 'generateContent' in m.supported_generation_methods and 'flash' in m.name.lower():
                return m.name
    except:
        pass
    return 'models/gemini-2.5-flash'

nombre_modelo_oficial = obtener_modelo_flash_activo()

# --- 5. CARGA DE DATOS DESDE EL REPOSITORIO ---
@st.cache_resource(show_spinner=False)
def cargar_documentos():
    texto_total = ""
    archivos_procesados = []
    archivos_excluidos = {f"Calendario {i}mo semestre 2026-1.pdf" for i in range(1, 11)}
    
    for a in os.listdir():
        if a in archivos_excluidos: continue
            
        if a.endswith(('.xlsx', '.xls', '.csv')):
            df = None
            try:
                df = pd.read_csv(a, encoding='utf-8') if a.endswith('.csv') else pd.read_excel(a)
            except:
                try: df = pd.read_csv(a, encoding='latin-1')
                except: continue
            
            if df is not None:
                archivos_procesados.append(f"📊 {a}")
                texto_total += f"\n--- REPOSITORIO HORARIOS HORAS: {a} ---\n"
                df.columns = [normalizar_columna(c) for c in df.columns]
                
                for _, fila in df.iterrows():
                    asig = limpiar_celda_texto(fila.get('ASIGNATURAS', fila.get('ASIGNATURA', '')))
                    secc = limpiar_celda_texto(fila.get('SECCION', fila.get('SECCIÓN', '')))
                    sem = limpiar_celda_texto(fila.get('SEMESTRE', ''))
                    dia = limpiar_celda_texto(fila.get('DIA', fila.get('DÍA', '')))
                    f_raw = limpiar_celda_texto(fila.get('FECHA DE LA CLASE', fila.get('FECHA', '')))
                    f_limpia = f_raw.split(' ')[0] if ' ' in f_raw else f_raw
                    h_ini = limpiar_celda_texto(fila.get('HORA INICIO DE LA CLASE', fila.get('HORA_INICIO', '')))
                    h_fin = limpiar_celda_texto(fila.get('HORA FINALIZACION DE LA CLASE', fila.get('HORA_FIN', '')))
                    
                    texto_total += f"Materia: {asig} | Seccion: {secc} | Semestre: {sem} | Dia: {dia} | Fecha: {f_limpia} | Horario: {h_ini} a {h_fin}\n"
                texto_total += "--- FIN REPOSITORIO ---\n"
                
        elif a.endswith('.pdf'):
            try:
                with fitz.open(a) as doc:
                    for pagina in doc:
                        texto_total += pagina.get_text()
                archivos_procesados.append(f"📄 {a}")
            except: continue
            
    return texto_total, archivos_procesados

contexto_facultad, archivos_activos = cargar_documentos()

# --- 6. INSTRUCCIONES DE SISTEMA CON CRITERIO DE ADAPTABILIDAD (NUEVO) ---
instrucciones_base = (
    "Eres Psicobot, el asistente oficial integral de la Escuela de Psicología.\n"
    "Tu objetivo es dar respuestas PRECISAS, DIRECTAS Y CONCISAS, usando emojis y negritas, sin saludos ni despedidas largas.\n\n"
    
    "⚠️ REGLA CRÍTICA DE ANCLAJE TEMPORAL:\n"
    "- Se te proporcionará una 'FECHA ACTUAL DEL SISTEMA' en cada mensaje.\n"
    "- Úsala como tu brújula temporal. Debes comparar lógicamente la fecha de hoy con las fechas de los documentos.\n"
    "- Ignora por completo o trata como 'pasados' los eventos, calendarios o procesos de inscripción cuyas fechas sean anteriores a la fecha actual.\n"
    "- Si el alumno pregunta por 'toma de ramos' o 'calendario', asume SIEMPRE que se refiere al proceso futuro más cercano o al semestre que está por iniciar.\n\n"

    "🧠 REGLA DE CRITERIO DE ADAPTABILIDAD (GENERAL VS. ESPECÍFICO):\n"
    "Evalúa detenidamente la estructura y la intención de la pregunta del alumno para decidir qué tipo de respuesta le sirve más:\n"
    "1. RESPUESTA QUIRÚRGICA (Específica): Si el alumno pregunta por un dato muy puntual (ej: '¿Cuándo le toca a Diurno?', '¿A qué hora abre Semipresencial cohorte 2025?'), dale DIRECTAMENTE ese dato exacto con su horario. No le muestres las fechas de las otras modalidades porque lo vas a confundir.\n"
    "2. RESPUESTA GLOBAL (Panorama Completo): Si el alumno pregunta de forma amplia o expresa confusión general (ej: '¿Cuáles son las fechas de toma de ramos de este semestre?', '¿Me das el calendario de inscripción?', '¿Cómo viene el proceso?'), NO te limites a una sola modalidad. Entrégale una línea de tiempo resumida y ultra-ordenada que muestre los hitos clave de todas las jornadas (Diurno, Vespertino y Semipresencial) en orden cronológico, para que tenga el mapa completo del proceso en un solo vistazo.\n\n"

    "REGLA 0: FILTRO OBLIGATORIO DE MODALIDAD (Aplica solo si la pregunta requiere identificar al alumno)\n"
    "- Si la pregunta es específica pero el alumno NO ha mencionado a qué modalidad pertenece, detén la respuesta de inmediato y pídelo brevemente: 'Para entregarte la información correcta, ¿a qué modalidad perteneces? (Presencial Diurno, Presencial Vespertino o Semipresencial)'.\n"
    "- Nota: Si la pregunta es abierta/general (ej: '¿Me das el calendario completo de toma de ramos?'), no necesitas filtrar; aplica la RESPUESTA GLOBAL directamente.\n\n"

    "REGLA 1: CLASIFICACIÓN DE LA CONSULTA\n"
    "ESCENARIO A: CONSULTA GENERAL DE HORARIOS DE CLASE\n"
    "- Requieres OBLIGATORIAMENTE el SEMESTRE y SECCIÓN. Pídelos brevemente si faltan.\n"
    "- Muestra exclusivamente las materias correspondientes usando el FORMATO VISUAL ESTRICTO.\n\n"

    "ESCENARIO B: CONSULTA DE UNA ASIGNATURA Y SECCIÓN ESPECÍFICA\n"
    "- Responde de inmediato sin pedir semestre usando el FORMATO VISUAL ESTRICTO.\n\n"

    "ESCENARIO C: CONSULTA DE TOMA DE RAMOS / INSCRIPCIÓN DE ASIGNATURAS\n"
    "- Usa el Criterio de Adaptabilidad para decidir si entregas el dato de una modalidad o el cronograma completo vigente (según archivo 2026-2).\n"
    "- Para respuestas específicas de Semipresencial, recuerda verificar la cohorte (2025-2026 vs 2024 y anteriores).\n"
    "- Incluye siempre los bloques de modificaciones y rezagados asociados a los datos que muestres.\n\n"

    "ESCENARIO D: CONSULTA GENERAL O ADMINISTRATIVA\n"
    "- Responde de forma directa basándote en los documentos aplicables.\n\n"

    "REGLA 2: FORMATO VISUAL PARA HORARIOS (SOLO ESCENARIOS A Y B - ESTRICTO)\n"
    "Estructura la lista dejando obligatoriamente una línea en blanco (doble salto de línea) entre el final de una asignatura y el inicio de la siguiente. Sigue este ejemplo exacto de espaciado:\n\n"
    "🧠 **ELEMENTOS DE NEUROCIENCIA**:\n"
    "* 🗓️ **DOMINGO 26-04-26** | ⏰ de **14:30** a **19:30** horas\n\n"
    "📊 **METODOLOGÍA CUANTITATIVA DE INVESTIGACIÓN**:\n"
    "* 🗓️ **SABADO 25-04-26** | ⏰ de **14:30** a **16:55** horas\n"
    "* 🗓️ **SABADO 30-05-26** | ⏰ de **14:30** a **17:40** horas\n\n"
    "REGLA CRÍTICA DE ESPACIADO: Jamás coloques el nombre o el emoji de una nueva asignatura en la misma línea donde termina el horario de la materia anterior."
)

# --- 7. PANTALLA DE BIENVENIDA ---
if not st.session_state.messages:
    st.markdown("<h3 style='text-align: center; color: #2e6c80;'>¡Hola! Estoy aquí para ayudarte 🤖</h3>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Puedes preguntarme sobre tus horarios o procesos de la carrera.</p>", unsafe_allow_html=True)
    
    colA, colB = st.columns(2)
    with colA:
        st.info("📅 **Horarios de Clases**\n\nEjemplo: *'Soy de Semipresencial, 1er semestre, sección 336. ¿Cuándo tengo clases?'*")
    with colB:
        st.info("📋 **Dudas Administrativas**\n\nEjemplo: *'¿Cuáles son todas las fechas de inscripción de asignaturas?'*")
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
        with st.spinner("Preparando respuesta..."):
            try:
                historial_contexto = ""
                for msg in st.session_state.messages[:-1]:
                    rol = "Estudiante" if msg["role"] == "user" else "Psicobot"
                    historial_contexto += f"{rol}: {msg['content']}\n"
                
                # Obtención de la fecha actual
                hoy = datetime.date.today()
                fecha_actual_sistema = hoy.strftime("%A, %d de %B de %Y")
                
                model = genai.GenerativeModel(model_name=nombre_modelo_oficial)
                
                full_prompt = (
                    f"{instrucciones_base}\n\n"
                    f"⏰ FECHA ACTUAL DEL SISTEMA (HOY ES): {fecha_actual_sistema}\n\n"
                    f"REPOSITORIO DE DATOS DE LA CARRERA:\n{contexto_facultad}\n\n"
                    f"HISTORIAL DE LA CONVERSACIÓN:\n{historial_contexto}\n"
                    f"ESTUDIANTE: {prompt}"
                )
                
                response = model.generate_content(full_prompt, generation_config={"temperature": 0.1})
                
                if response and hasattr(response, 'text') and response.text:
                    st.markdown(response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                else:
                    st.warning("⚠️ El asistente no devolvió una respuesta válida. Intenta reformular.")
                    
            except Exception as e:
                st.error(f"⚠️ Error detallado del sistema: {e}")
