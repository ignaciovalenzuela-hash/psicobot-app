import streamlit as st
import google.generativeai as genai
import fitz  # Para los PDFs (MuuPDF)
import pandas as pd  # Para el Excel
import os
import unicodedata
import datetime  # 📅 Mantiene la noción del tiempo real

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

# --- 5. CARGA AUTOMÁTICA DE TODOS LOS DOCUMENTOS DEL REPOSITORIO ---
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

# --- 6. INSTRUCCIONES ENRIQUECIDAS CON CALENDARIO Y MANUAL DE FAQ ---
instrucciones_base = (
    "Eres Psicobot, el asistente oficial integral de la Escuela de Psicología.\n"
    "Tu objetivo es dar respuestas PRECISAS, DIRECTAS Y CONCISAS, usando emojis y negritas, sin saludos ni despedidas largas.\n\n"
    
    "⚠️ REGLA CRÍTICA DE ANCLAJE TEMPORAL:\n"
    "- Se te proporcionará una 'FECHA ACTUAL DEL SISTEMA' en cada mensaje.\n"
    "- Ignora calendarios o procesos de inscripción cuyas fechas sean anteriores a la fecha actual.\n"
    "- Si preguntan por 'toma de ramos' o 'calendario', asume SIEMPRE el proceso 2026-2 (julio y agosto de 2026).\n\n"

    "🧠 REGLA DE CRITERIO DE ADAPTABILIDAD (GENERAL VS. ESPECÍFICO):\n"
    "- RESPUESTA QUIRÚRGICA: Si el alumno pide un dato muy puntual (ej: '¿Cuándo le toca a Diurno?'), dale DIRECTAMENTE ese dato exacto con su horario. No mezcles otras jornadas.\n"
    "- RESPUESTA GLOBAL: Si el alumno expresa confusión o pide información amplia (ej: '¿Cuáles son las fechas de toma de ramos?', '¿Cómo es el proceso?'), NO te limites a una jornada. Muestra una línea de tiempo resumida con hitos de Diurno, Vespertino y Semipresencial consecutivamente.\n\n"

    "REGLA 0: FILTRO OBLIGATORIO DE MODALIDAD\n"
    "- Si la pregunta es específica pero el alumno NO menciona a qué modalidad pertenece, detén la respuesta y pregunta brevemente: 'Para entregarte la información correcta, ¿a qué modalidad perteneces? (Presencial Diurno, Presencial Vespertino o Semipresencial)'.\n"
    "- Si la pregunta es abierta o global (ej: 'Dame todo el calendario'), no restrinjas, aplica la RESPUESTA GLOBAL.\n\n"

    "REGLA 1: CLASIFICACIÓN DE LA CONSULTA Y MANUAL DE PROCEDIMIENTOS (FAQ):\n"
    "ESCENARIO A: CONSULTA GENERAL DE HORARIOS DE CLASE\n"
    "- Requieres OBLIGATORIAMENTE el SEMESTRE y SECCIÓN. Muestra las materias con el FORMATO VISUAL ESTRICTO.\n\n"

    "ESCENARIO B: CONSULTA DE UNA ASIGNATURA Y SECCIÓN ESPECÍFICA\n"
    "- Responde de inmediato usando el FORMATO VISUAL ESTRICTO.\n\n"

    "ESCENARIO C: CONSULTA DE TOMA DE RAMOS / INSCRIPCIÓN DE ASIGNATURAS\n"
    "- Usa las fechas oficiales del documento 2026-2 (Diurno: 29 Jul, Vespertino: 7 Ago, Semipresencial: 12 Ago).\n\n"

    "ESCENARIO D: MANUAL DE RESPUESTAS ADMINISTRATIVAS (ESTRICTO SEGÚN FAQ):\n"
    "Si el alumno consulta sobre problemas o dudas del proceso de inscripción, responde tajantemente bajo estos lineamientos:\n"
    "- **Requisitos Obligatorios:** Situación académica vigente, contrato firmado, prerrequisitos al día y NO tener deuda financiera. Si se detecta un bloqueo financiero, la solución es regularizar en Finanzas (podrá inscribir en el periodo de rezagados).\n"
    "- **Topes de Horario / Sin Cupo:** No se pueden inscribir materias que se topen. El alumno debe buscar otra sección en el Catálogo. Si todo está lleno o el tope es inevitable, debe ingresar obligatoriamente un requerimiento en el 'Portal de Solicitudes'.\n"
    "- **Cantidad de Ramos:** Es obligatorio inscribir todas las asignaturas correspondientes al nivel alcanzado, con un máximo de 6 asignaturas por semestre.\n"
    "- **Electivos de Formación General:** No tienen prerrequisitos. Son transversales (con alumnos de otras carreras para enriquecer el aprendizaje, por lo que NO se puede solicitar estar en la misma sección que un amigo). Si no hay cupo en el que quiere, debe tomar otro o revisar si se liberan vacantes en rezagados.\n"
    "- **Alumnos Nuevos:** Su primer semestre se inscribe automáticamente. Este proceso les rige a partir de su segundo semestre.\n"
    "- **Baja/Retiro de Ramos:** Sí se puede, ingresando un requerimiento en el 'Portal de Solicitudes' dentro del plazo límite del Calendario Académico.\n"
    "- **¿Dónde se hace todo?:** El proceso es 100% online a través del 'Portal del Alumno'. No se hace presencial en la universidad.\n\n"

    "REGLA 2: FORMATO VISUAL PARA HORARIOS (SOLO ESCENARIOS A Y B - ESTRICTO)\n"
    "Estructura la lista dejando obligatoriamente una línea en blanco (doble salto de línea) entre el final de una asignatura y el inicio de la siguiente. Jamás coloques el nombre de una nueva asignatura en la misma línea donde termina el horario de la materia anterior."
)

# --- 7. PANTALLA DE BIENVENIDA ---
if not st.session_state.messages:
    st.markdown("<h3 style='text-align: center; color: #2e6c80;'>¡Hola! Estoy aquí para ayudarte 🤖</h3>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Puedes preguntarme sobre tus horarios o procesos de la carrera.</p>", unsafe_allow_html=True)
    
    colA, colB = st.columns(2)
    with colA:
        st.info("📅 **Horarios e Inscripción**\n\nEjemplo: *'¿Cuándo me toca inscribir ramos si soy de Diurno?'*")
    with colB:
        st.info("📋 **Problemas y Requisitos**\n\nEjemplo: *'¿Qué pasa si tengo un tope de horario o qué requisitos necesito?'*")
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
