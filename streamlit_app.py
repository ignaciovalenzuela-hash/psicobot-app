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
    st.error("Error: Configura la API Key en los Secrets.")
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 4. CARGA EXTREMA DE DATOS ---
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
                    # Buscamos columnas alternativas según cómo nombres tu Excel
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

# --- 5. CONFIGURACIÓN DE CONTEXT CACHING (AHORRO CRÉDITOS) ---
# Instrucciones del sistema que formatean la salida exactamente como lo pides
instrucciones_base = (
    "Eres Psicobot, el asistente oficial de Psicología.\n\n"
    "REGLA 1: VALIDACIÓN ANTES DE RESPONDER\n"
    "Si el alumno no indica explícitamente su MODALIDAD y su SECCIÓN, detenlo inmediatamente "
    "y pídele amablemente esos datos antes de procesar cualquier horario.\n\n"
    "REGLA 2: FORMATO DE SALIDA ESTRICTO POR ASIGNATURA\n"
    "Cuando respondas los horarios de clases, debes agruparlos estrictamente por Asignatura utilizando "
    "exactamente este diseño de texto (sin viñetas, sin guiones, respetando saltos de línea):\n\n"
    "[Nombre de la Asignatura en formato normal]:\n\n"
    "FECHAS\n"
    "[día de la semana en minúscula] [DD-MM-AA] DE [Hora Inicio] A [Hora Fin] HORAS\n\n"
    "EJEMPLO DE RESPUESTA REQUERIDA:\n"
    "Introducción a la psicología:\n\n"
    "FECHAS\n"
    "domingo 29-03-26 DE 8:30 A 13:30 HORAS\n"
    "domingo 10-05-26 DE 8:30 A 13:30 HORAS\n\n"
    "Si hay más asignaturas agendadas para esa sección, pon un bloque completo abajo del otro separado por un espacio vacío."
)

@st.cache_resource(show_spinner=False)
def crear_context_cache(contexto, instrucciones):
    # Combinamos todo el conocimiento base
    bloque_conocimiento = f"{instrucciones}\n\nCONOCIMIENTO DE LA CARRERA:\n{contexto}"
    
    # Verificamos si el tamaño cumple con el mínimo requerido por Google (~32k tokens)
    if len(bloque_conocimiento) < 130000:
        return None  # Muy pequeño para caché de servidor, se usará el modo estándar económico
    
    try:
        # Registramos el caché en los servidores de Google Gemini por un TTL de 3 horas
        mi_cache = caching.CachedContent.create(
            model='models/gemini-1.5-flash-001',
            display_name='psicobot_data_cache',
            contents=bloque_conocimiento,
            ttl=datetime.timedelta(hours=3)
        )
        return mi_cache
    except:
        return None

# Activamos el optimizador de créditos de Google
cache_activo = crear_context_cache(contexto_facultad, instrucciones_base)

with st.sidebar:
    st.subheader("📁 Estado del Sistema")
    if cache_activo:
        st.success("⚡ Caché de Contexto Activo (Ahorro de créditos activado)")
    else:
        st.info("📉 Modo estándar (Consumo regular bajo)")

# --- 6. CHAT ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Escribe tu duda aquí..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            # Reutilizamos el modelo asociado al caché guardado si está disponible
            if cache_activo:
                model = genai.GenerativeModel(name='models/gemini-1.5-flash-001', cached_content=cache_activo)
            else:
                model = genai.GenerativeModel(model_name='gemini-1.5-flash', system_instruction=instrucciones_base)
            
            # Construcción de la memoria de la conversación actual
            historial_contexto = ""
            for msg in st.session_state.messages[:-1]:
                rol = "Estudiante" if msg["role"] == "user" else "Psicobot"
                historial_contexto += f"{rol}: {msg['content']}\n"
            
            # Formamos el prompt final
            if cache_activo:
                # Si hay caché, no enviamos los archivos pesados, Google ya los tiene memorizados.
                full_prompt = f"HISTORIAL:\n{historial_contexto}\nESTUDIANTE: {prompt}"
            else:
                # Si los archivos son pequeños, usamos el flujo regular
                full_prompt = f"REPOSITORIO:\n{contexto_facultad[:100000]}\n\nHISTORIAL:\n{historial_contexto}\nESTUDIANTE: {prompt}"
            
            response = model.generate_content(full_prompt, generation_config={"temperature": 0.0})
            
            if response.text:
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                
        except Exception as e:
            st.error("Ocurrió un inconveniente al conectar con el servidor. Por favor reenvía tu pregunta.")
