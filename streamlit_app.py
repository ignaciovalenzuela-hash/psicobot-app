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

# --- 6. INSTRUCCIONES DE SISTEMA (CONCISAS Y OPTIMIZADAS) ---
instrucciones_base = (
    "Eres Psicobot, el asistente oficial integral de la carrera de Psicología Semipresencial.\n"
    "Tu objetivo es dar respuestas PRECISAS, DIRECTAS Y CONCISAS. Evita párrafos de relleno, no uses saludos largos (como '¡Hola de nuevo!') en cada interacción y no agregues despedidas largas. Ve directamente a la información solicitada manteniendo un tono cordial pero ejecutivo, apoyándote en emojis y negritas.\n\n"
    "REGLA 1: CLASIFICACIÓN FLEXIBLE DE LA CONSULTA\n"
    "ESCENARIO A: CONSULTA GENERAL DE HORARIOS DE CLASE\n"
    "- Necesitas OBLIGATORIAMENTE el SEMESTRE y SECCIÓN. Si faltan, pídelos de forma muy breve.\n"
    "- Muestra exclusivamente las materias correspondientes usando el FORMATO VISUAL ESTRICTO.\n\n"
    "ESCENARIO B: CONSULTA DE UNA ASIGNATURA Y SECCIÓN ESPECÍFICA\n"
    "- Si menciona asignatura y sección, da la respuesta inmediata. No pidas semestre. Usa el FORMATO VISUAL ESTRICTO.\n\n"
    "ESCENARIO C: CONSULTA GENERAL O ADMINISTRATIVA\n"
    "- Responde directo basándote en los documentos. Sé breve, destaca lo importante en negritas y omite información introductoria redundante.\n\n"
    "REGLA 2: FORMATO VISUAL PARA HORARIOS (SOLO ESCENARIOS A Y B)\n"
    "Usa estrictamente esta estructura sin texto de introducción extenso:\n"
    "Emoji + **Nombre de la Asignatura**:\n"
    "* 🗓️ **[Día] [DD-MM-AA]** | ⏰ de **[Hora Inicio]** a **[Hora Fin]** horas\n"
)

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
            
            response = model.generate_content(full_prompt, generation_config={"temperature": 0.2})
            
            if response and hasattr(response, 'text') and response.text:
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            else:
                st.warning("⚠️ El asistente no devolvió una respuesta válida. Intenta reformular.")
                
        except Exception as e:
            st.error(f"⚠️ Error detallado del sistema: {e}")
