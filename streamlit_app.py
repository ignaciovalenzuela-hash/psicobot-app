import streamlit as st
import google.generativeai as genai
import fitz  # Para los PDFs
import pandas as pd  # Para leer el Excel/CSV
import os

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Psicobot", page_icon="🧠", layout="centered")

# --- 2. LOGO Y ENCABEZADO ---
col1, col2, col3 = st.columns([1, 1.2, 1])
with col2:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    else:
        st.caption("🚀 Psicobot en línea")

st.markdown("<h1 style='text-align: center;'>Psicobot</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: gray;'>Tu asistente oficial de Psicología</p>", unsafe_allow_html=True)
st.markdown("---")

# --- 3. CONFIGURACIÓN DE API ---
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("Error: Configura la API Key en los Secrets.")
    st.stop()

# --- 4. MEMORIA DEL CHAT ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 5. CARGA INTELIGENTE DE PDF Y EXCEL (CSV) ---
@st.cache_resource(show_spinner=False)
def cargar_documentos():
    texto_total = ""
    
    # Excluimos los calendarios antiguos que me pediste sacar antes
    archivos_excluidos = {
        "Calendario 10mo semestre 2026-1.pdf", "Calendario 1er semestre 2026-1.pdf",
        "Calendario 2do semestre 2026-1.pdf", "Calendario 3er semestre 2026-1.pdf",
        "Calendario 4to semestre 2026-1.pdf", "Calendario 5to semestre 2026-1.pdf",
        "Calendario 6to semestre 2026-1.pdf", "Calendario 7mo semestre 2026-1.pdf",
        "Calendario 8vo semestre 2026-1.pdf", "Calendario 9no semestre 2026-1.pdf"
    }
    
    archivos = os.listdir()
    
    for a in archivos:
        if a in archivos_excluidos:
            continue
            
        # --- PROCESAR PDFs ---
        if a.endswith('.pdf'):
            try:
                with fitz.open(a) as doc:
                    for pagina in doc:
                        texto_total += f"\n\n--- INICIO DOCUMENTO: {a} ---\n"
                        texto_total += pagina.get_text()
                        texto_total += f"\n--- FIN DOCUMENTO: {a} ---\n"
            except: continue
            
        # --- PROCESAR EXCEL / CSV (NUEVO) ---
        elif a.endswith('.csv'):
            try:
                # Cargamos el archivo usando pandas
                df = pd.read_csv(a)
                texto_total += f"\n\n--- INICIO BASE DE DATOS HORARIOS PRESENCIALES: {a} ---\n"
                
                # Convertimos cada fila del Excel en una frase clara para la IA
                for index, fila in df.iterrows():
                    texto_total += (
                        f"Asignatura: {fila.get('ASIGNATURAS', '')} ({fila.get('CODIGO DE ASIGNATURAS', '')}) | "
                        f"Sección: {fila.get('SECCIÓN', '')} | "
                        f"Docente: {fila.get('NOMBRES DOCENTE', '')} {fila.get('APELLIDO PATERNO DOCENTE', '')} | "
                        f"Día: {fila.get('DÍA', '')} | "
                        f"Fecha: {fila.get('FECHAS DE LA CLASE', fila.get('FECHA DE LA CLASE', ''))} | "
                        f"Horario: {fila.get('HORA INICIO DE LA CLASE', '')} a {fila.get('HORA FINALIZACIÓN DE LA CLASE', '')} | "
                        f"Sala: {fila.get('CODIGO DE SALA DE CLASES', '')} | "
                        f"Semestre: {fila.get('SEMESTRE', '')} Semestre.\n"
                    )
                texto_total += f"--- FIN BASE DE DATOS HORARIOS ---\n"
            except: continue
            
    return texto_total

contexto_facultad = cargar_documentos()

# --- 6. VISUALIZACIÓN DEL HISTORIAL ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 7. LÓGICA DE PREGUNTAS Y RESPUESTAS ---
if prompt := st.chat_input("Pregúntame por tus fechas presenciales, salas o docentes..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            modelos_disponibles = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            nombre_modelo = next((m for m in modelos_disponibles if "flash" in m), modelos_disponibles[0])
            
            model = genai.GenerativeModel(
                model_name=nombre_modelo,
                generation_config={
                    "temperature": 0.1, 
                    "max_output_tokens": 2048,
                }
            )
            
            instrucciones = (
                "Eres Psicobot. Tu tono es el de un coordinador académico muy buena onda, empático y súper claro.\n\n"
                "REGLAS PARA EL EXCEL DE HORARIOS:\n"
                "1. Cuando un alumno te pregunte por una asignatura (ej. 'Bases Biológicas' o 'Epistemología'), busca TODAS las filas asociadas a esa asignatura en el contexto.\n"
                "2. Agrupa las fechas. Si una materia tiene 2 o 3 fechas presenciales en el semestre, muéstraselas todas en una lista ordenada cronológicamente.\n"
                "3. Entrega el detalle completo por cada fecha: Día, Fecha exacta, Horario (inicio y fin), Sala asignada y el profesor a cargo.\n"
                "4. Sé muy claro y ordenado. Usa emojis (📅, 🕒, 📍, 👨‍🏫) para que el alumno entienda la información de un solo vistazo.\n"
                "5. Si el estudiante no especifica su sección o semestre y ves que la materia se repite, pregúntale amablemente: '¿De qué semestre o sección eres?' para darle el dato exacto."
            )

            full_prompt = f"{instrucciones}\n\nCONTEXTO DE LA FACULTAD (Aquí están los horarios y documentos):\n{contexto_facultad[:110000]}\n\nPREGUNTA DEL ESTUDIANTE: {prompt}"
            
            response = model.generate_content(full_prompt)
            
            if response.text:
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            
        except Exception as e:
            st.error("Se interrumpió la respuesta o hubo un error de conexión. Por favor, intenta preguntar de nuevo.")
