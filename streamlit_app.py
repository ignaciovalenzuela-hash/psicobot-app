# Respuesta del asistente
    with st.chat_message("assistant"):
        try:
            # CAMBIO CLAVE: Usamos el nombre del modelo con el prefijo 'models/'
            # Esto soluciona el error 404 en las nuevas versiones de la API
            model = genai.GenerativeModel('models/gemini-1.5-flash')
            
            instrucciones = (
                "Eres Psicobot. Respuestas amables, breves y precisas.\n"
                "1. Diferencia CLASES ONLINE de CLASES PRESENCIALES.\n"
                "2. Cita Artículos si hablas de reglamentos.\n"
                "3. Si preguntan por un semestre, busca el archivo exacto de ese semestre.\n"
                "4. No inventes fechas que no estén en el contexto."
            )

            # Unimos todo
            full_prompt = f"{instrucciones}\n\nCONTEXTO:\n{contexto_facultad[:100000]}\n\nPREGUNTA: {prompt}"
            
            # Generamos contenido con una configuración de seguridad básica
            response = model.generate_content(full_prompt)
            
            if response.text:
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            
        except Exception as e:
            if "404" in str(e):
                st.error("🔄 Error de ruta. Intentando conexión alternativa...")
                # Reintento con nombre alternativo si el primero falla
                try:
                    model_alt = genai.GenerativeModel('gemini-1.5-flash')
                    response = model_alt.generate_content(full_prompt)
                    st.markdown(response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                except:
                    st.error("No se pudo conectar con el modelo. Verifica que la API Key esté activa en Google AI Studio.")
            elif "429" in str(e):
                st.error("⏳ Agotamos las pruebas en esta cuenta.")
            else:
                st.error(f"Error: {str(e)[:100]}")
