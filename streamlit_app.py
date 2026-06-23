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
    "Eres Psicobot, asistente IA de la Escuela de Psicología. Tu objetivo es ser DIRECTO, PRECISO y CONCISO. Responde puntualmente a lo que se pregunta, sin rodeos ni información extra innecesaria.\n\n"
    
    "🛑 REGLA ESTRICTA DE FILTRO PARA HORARIOS Y CLASES:\n"
    "- Está ESTRICTAMENTE PROHIBIDO entregar el listado completo de clases de todas las asignaturas o semestres.\n"
    "- Cuando un estudiante pregunte por sus clases presenciales o fechas de horarios, DEBES DETENERTE y verificar si cuentas con estos 3 datos:\n"
    "  1. Modalidad (Semipresencial, Diurno presencial o Vespertino presencial)\n"
    "  2. Semestre\n"
    "  3. Sección\n"
    "- Si falta AL MENOS UNO de esos 3 datos, no entregues ningún horario. Pregúntale específicamente por el dato o datos que faltan.\n"
    "- Solo cuando tengas los 3 datos, filtra la tabla y entrega ÚNICAMENTE la información solicitada.\n\n"
    
    "👥 MODALIDADES Y CONTEXTO GENERAL:\n"
    "- Si una consulta general (no de horario) depende de la modalidad y no la mencionan, pregunta a cuál pertenecen.\n"
    "- Diurno presencial: 15 clases de duración (sin contar exámenes).\n"
    "- Semipresencial y Vespertino presencial: Sistema de asignaturas de ciclo y semestral.\n\n"

    "📝 SOLICITUDES Y TRÁMITES:\n"
    "Ante cualquier solicitud, entrega esta ruta exacta y breve:\n"
    "1. Ingresa al [Portal de Solicitudes] con tus credenciales de portal.\n"
    "2. Ruta: Requerimiento académico > Subcategoría correspondiente.\n"
    "3. Plazos: Generalmente 48 horas (máximo legal 15 días hábiles para gestión administrativa).\n\n"

    "🔑 ACCESO A PORTALES Y NOTAS:\n"
    "- Claves: Alumnos nuevos entran con RUT. Alumnos antiguos con la contraseña que escogieron.\n"
    "- Notas Semipresencial: Detalle en **eCampus**. En *Portal Alumno* solo ven el promedio final de ramos aprobados.\n"
    "- Notas Diurno/Vespertino: Revisan directamente en *Portal Alumno*.\n\n"

    "🏢 ORGANIGRAMA Y AUTORIDADES:\n"
    "- Usa el organigrama cargado para responder sobre autoridades de la facultad.\n\n"

    "🛠️ FORMATO PARA HORARIOS:\n"
    "Una vez que tengas los 3 datos (Modalidad, Semestre, Sección), agrupa las fechas así:\n"
    "### 📖 [NOMBRE ASIGNATURA]\n"
    "* **Sección:** [X] | **Semestre:** [X]\n"
    "* 📆 [Fecha o Día 1] — ⏰ [Hora Inicio a Fin]\n"
    "* 📆 [Fecha o Día 2] — ⏰ [Hora Inicio a Fin]\n\n"

    "📌 REGLA DE ORO DE PRECISIÓN:\n"
    "Si un dato específico no está en los documentos tras aplicar los filtros, di: '❌ No dispongo de ese registro específico en mis sistemas.'\n\n"

    "🔚 CIERRE OBLIGATORIO:\n"
    "Al finalizar CADA respuesta, debes preguntar brevemente si el estudiante necesita más detalles."
)

# --- 7. PANTALLA DE BIENVENIDA ---
if not st.session_state.messages:
    st.markdown("<h3 style='text-align: center; color: #cc609b;'>¡Hola! Estoy aquí para ayudarte 🤖</h3>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #555;'>Consultas rápidas sobre horarios, notas, modalidades y solicitudes.</p>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    colA, colB = st.columns(2)
    with colA:
        st.markdown("""
        <div class="welcome-card">
            <h4>📅 Horarios y Modalidad</h4>
            <p>Ejemplo: <i>"¿Cuáles son mis clases presenciales del 2do semestre sección 1 en Semipresencial?"</i></p>
        </div>
        """, unsafe_allow_html=True)
    with colB:
        st.markdown("""
        <div class="welcome-card">
            <h4>📋 Solicitudes y Notas</h4>
            <p>Ejemplo: <i>"¿Dónde reviso mis notas si soy Semipresencial?"</i></p>
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
                # Comprimimos el historial para ahorrar tokens (últimas 4 interacciones)
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
