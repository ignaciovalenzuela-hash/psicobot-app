import streamlit as st
import google.generativeai as genai
import fitz  # Para los PDFs
import pandas as pd  # Para el Excel
import os
import unicodedata

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Psicobot", page_icon="🧠", layout="centered")

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

st.markdown("<h1 style='text-align: center;'>Psicobot</h1>", unsafe_allow_html=True)
st.markdown("---")

# --- 3. CONFIGURACIÓN DE API ---
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("Error: Configura la API Key en los Secrets de Streamlit.")
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 4. DETECCIÓN DINÁMICA DE MODELOS ACTIVOS ---
@st.cache_resource(show_spinner=False)
def obtener_modelo_flash_activo():
    try:
        modelos_disponibles = list(genai.list_models())
        for m in modelos_disponibles:
            if 'generateContent' in m.supported_generation_methods and 'flash' in m.name.lower():
                return m.name
        for m in modelos_disponibles:
            if 'generateContent' in m.supported_generation_methods:
                return m.name
    except:
        pass
    return 'models/gemini-1.5-flash-latest'

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

# --- 6. INSTRUCCIONES DE FILTRADO, EMOJIS Y NEGRETAS ---
instrucciones_base = (
    "Eres Psicobot, el asistente oficial de la carrera de Psicología Semipresencial.\n\n"
    "REGLA 1: CLASIFICACIÓN DE LA CONSULTA DEL ESTUDIANTE\n"
    "Dependiendo de lo que el alumno pregunte, debes actuar bajo uno de estos dos escenarios estrictos:\n\n"
    "ESCENARIO A: CONSULTA GENERAL DE HORARIOS (Ej: '¿cuándo tengo clases?', 'horarios de semipresencial', 'mis materias')\n"
    "- Para este caso, necesitas OBLIGATORIAMENTE saber el SEMESTRE y la SECCIÓN del alumno.\n"
    "- Si el alumno no menciona de forma explícita AMBOS datos en su mensaje o en el historial, detén el proceso de inmediato.\n"
    "- Pídele amablemente que te indique su semestre (ej. 1er semestre) y su sección (ej. 336).\n"
    "- NOTA DE CRUCE DE DATOS: En el repositorio, la columna SEMESTRE contiene números puros (ej: '1' para primer semestre, '9' para noveno semestre).\n"
    "- Una vez obtenidos ambos datos, busca en el repositorio y muestra ÚNICAMENTE las materias que coincidan EXACTAMENTE con ese Semestre y esa Sección.\n\n"
    "ESCENARIO B: CONSULTA DE ASIGNATURA ESPECÍFICA (Ej: '¿cuándo tengo Epistemología sección 336?', 'horario de Introducción sección 334')\n"
    "- Si el alumno pregunta por una asignatura en particular y te proporciona la SECCIÓN, responde DIRECTAMENTE con las fechas de esa materia para esa sección.\n"
    "- En este escenario NO le pidas el semestre, ya que la combinación de Asignatura + Sección es suficiente para filtrar de forma exacta.\n\n"
    "REGLA 2: FORMATO VISUAL CON EMOJIS Y NEGRETAS (ESTRICTO Y OBLIGATORIO)\n"
    "Al entregar los resultados (para cualquier escenario), debes formatear el texto exactamente de la siguiente manera:\n"
    "1. Escribe un emoji relacionado con la materia al inicio (ej: 🧬, 📚, 🧠, 📑), luego el nombre de la Asignatura en negritas, seguido de dos puntos (:).\n"
    "2. Inmediatamente abajo, lista cada una de las fechas utilizando viñetas de punto (*).\n"
    "3. Cada viñeta debe usar exactamente este formato e iconos:\n"
    "   * 🗓️ **[Día] [DD-MM-AA]** | ⏰ de **[Hora Inicio]** a **[Hora Fin]** horas\n"
    "4. El día de la semana y la fecha completa van juntos en un solo bloque de negritas. Las horas de inicio y fin van en negritas de forma individual.\n"
    "5. Ordena las fechas cronológicamente de la más antigua a la más reciente.\n"
    "6. Separa cada bloque de asignatura con un solo espacio en blanco.\n\n"
    "EJEMPLO DE RESPUESTA VISUAL REQUERIDA:\n"
    "🧬 **Bases biológicas del comportamiento**:\n"
    "* 🗓️ **Domingo 07-06-26** | ⏰ de **08:30** a **13:30** horas\n"
    "* 🗓️ **Domingo 19-07-26** | ⏰ de **08:30** a **13:30** horas\n\n"
    "📚 **Epistemología**:\n"
    "* 🗓️ **Sábado 28-03-26** | ⏰ de **11:05** a **14:05** horas\n"
    "* 🗓️ **Sábado 09-05-26** | ⏰ de **11:40** a **14:05** horas\n\n"
    "No pongas introducciones largas ni textos adicionales al final. Ve directo al grano entregando los horarios con el diseño solicitado."
)

with st.sidebar:
    st.subheader("📁 Estado del Sistema")
    st.info(f"🤖 Modelo Activo: {nombre_modelo_oficial.split('/')[-1]}")
    st.success("🚀 Formato Visual Dinámico Activado")

# --- 7. VISUALIZACIÓN DEL CHAT ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Escribe tu duda aquí..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            historial_contexto = ""
            for msg in st.session_state.messages[:-1]:
                rol = "Estudiante" if msg["role"] == "user" else "Psicobot"
                historial_contexto += f"{rol}: {msg['content']}\n"
            
            model = genai.GenerativeModel(model_name=nombre_modelo_oficial)
            
            full_prompt = (
                f"{instrucciones_base}\n\n"
                f"REPOSITORIO DE DATOS DE LA CARRERA:\n{contexto_facultad}\n\n"
                f"HISTORIAL DE LA CONVERSACIÓN:\n{historial_contexto}\n"
                f"ESTUDIANTE: {prompt}"
            )
            
            response = model.generate_content(full_prompt, generation_config={"temperature": 0.0})
            
            if response and hasattr(response, 'text') and response.text:
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            else:
                st.warning("⚠️ El asistente no devolvió una respuesta válida. Intenta reformular.")
                
        except Exception as e:
            st.error(f"⚠️ Error detallado del sistema: {e}")
