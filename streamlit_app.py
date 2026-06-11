import streamlit as st
import google.generativeai as genai
from google.generativeai import caching
import fitz  # Para los PDFs
import pandas as pd  # Para el Excel
import os
import unicodedata
import datetime

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

# --- 5. CARGA EXTREMA DE DATOS ---
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

# --- 6. INSTRUCCIONES DEFINITIVAS DE FILTRADO ---
instrucciones_base = (
    "Eres Psicobot, el asistente oficial de la carrera de Psicología Semipresencial.\n\n"
    "REGLA 1: CLASIFICACIÓN DE LA CONSULTA DEL ESTUDIANTE\n"
    "Dependiendo de lo que el alumno pregunte, debes actuar bajo uno de estos dos escenarios estrictos:\n\n"
    "ESCENARIO A: CONSULTA GENERAL DE HORARIOS (Ej: '¿cuándo tengo clases?', 'horarios de semipresencial', 'mis materias')\n"
    "- Para este caso, necesitas OBLIGATORIAMENTE saber el SEMESTRE y la SECCIÓN del alumno.\n"
    "- Si el alumno no menciona de forma explícita AMBOS datos en su mensaje o en el historial, detén el proceso de inmediato.\n"
    "- Pídele amablemente que te indique su semestre (ej. 1er semestre) y su sección (ej. 336).\n"
    "- Una vez obtenidos ambos datos, busca en el repositorio y muestra ÚNICAMENTE las materias que coincidan EXACTAMENTE con ese Semestre y esa Sección.\n\n"
    "ESCENARIO B: CONSULTA DE ASIGNATURA ESPECÍFICA (Ej: '¿cuándo tengo Epistemología sección 336?', 'horario de Introducción sección 334')\n"
    "- Si el alumno pregunta por una asignatura en particular y te proporciona la SECCIÓN, responde DIRECTAMENTE con las fechas de esa materia para esa sección.\n"
    "- En este escenario NO le pidas el semestre, ya que la combinación de Asignatura + Sección es suficiente para identificar las filas correctas en el repositorio.\n\n"
    "REGLA 2: FORMATO DE SALIDA ESTRICTO POR ASIGNATURA\n"
    "Para cualquiera de los dos escenarios anteriores, al entregar los horarios debes agruparlos por Asignatura usando exactamente este diseño de texto (sin viñetas, sin guiones, respetando los saltos de línea):\n\n"
    "[Nombre de la Asignatura en formato normal]:\n\n"
    "FECHAS\n"
    "[día de la semana en minúscula] [DD-MM-AA] DE [Hora Inicio] A [Hora Fin] HORAS\n\n"
    "EJEMPLO DE RESPUESTA REQUERIDA:\n"
    "Introducción a la psicología:\n\n"
    "FECHAS\n"
    "domingo 29-03-26 DE 8:30 A 13:30 HORAS\n"
    "domingo 10-05-26 DE 8:30 A 13:30 HORAS\n\n"
    "Si hay múltiples asignaturas que cumplan con el filtro del estudiante, coloca un bloque completo abajo del otro, separados exactamente por un espacio en blanco."
)

# --- 6.1 CONFIGURACIÓN DE CONTEXT CACHING ---
@st.cache_resource(show_spinner=False)
def crear_context_cache(contexto, instrucciones, modelo_destino):
    bloque_conocimiento = f"{instrucciones}\n\nCONOCIMIENTO DE LA CARRERA:\n{contexto}"
    if len(bloque_conocimiento) < 130000:
        return None
    try:
        mi_cache = caching.CachedContent.create(
            model=modelo_destino,
            display_name='psicobot_data_cache',
            contents=bloque_conocimiento,
            ttl=datetime.timedelta(hours=3)
        )
        return mi_cache
    except:
        return None

cache_activo = crear_context_cache(contexto_facultad, instrucciones_base, nombre_modelo_oficial)

with st.sidebar:
    st.subheader("📁 Estado del Sistema")
    st.info(f"🤖 Modelo En Línea: {nombre_modelo_oficial.split('/')[-1]}")
    if cache_activo:
        st.success("⚡ Caché Activo (Ahorro de créditos)")
    else:
        st.info("📉 Modo estándar (Optimizado de bajo consumo)")

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
            
            if cache_activo:
                model = genai.GenerativeModel(model_name=nombre_modelo_oficial, cached_content=cache_activo)
                full_prompt = f"HISTORIAL:\n{historial_contexto}\nESTUDIANTE: {prompt}"
            else:
                model = genai.GenerativeModel(model_name=nombre_modelo_oficial)
                full_prompt = (
                    f"{instrucciones_base}\n\n"
                    f"REPOSITORIO:\n{contexto_facultad[:100000]}\n\n"
                    f"HISTORIAL COVERSACIÓN:\n{historial_contexto}\n"
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
