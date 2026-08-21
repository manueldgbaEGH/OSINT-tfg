import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import urllib.parse
import time
import io
import PyPDF2
import json
from google import genai
from google.genai import types

# ==========================================
# INTERFAZ DE USUARIO
# ==========================================
st.set_page_config(page_title="Auditor TFG - Ley 2/2023", page_icon="🕵️‍♂️", layout="wide")

st.title("🕵️‍♂️ Auditor OSINT: Canales de Denuncia (Ley 2/2023)")
st.markdown("Esta herramienta analiza páginas web corporativas para evaluar el **Índice de Cumplimiento Observable en Web (ICOW)** de los Sistemas Internos de Información mediante IA.")

with st.sidebar:
    st.header("⚙️ Configuración")
    api_key_usuario = st.text_input("1. Introduce tu API Key de Gemini:", type="password")
    archivo_subido = st.file_uploader("2. Sube tu base de datos (Excel SABI)", type=["xlsx"])
    st.info("El archivo debe contener las columnas 'Company Name' y 'Web' o 'Web site'.")

# ==========================================
# MOTOR DEL PROGRAMA
# ==========================================
if st.button("🚀 Iniciar Auditoría Automatizada", type="primary"):
    
    if not api_key_usuario or not archivo_subido:
        st.error("⚠️ Por favor, introduce tu API Key y sube un archivo Excel para comenzar.")
    else:
        cliente_ia = genai.Client(api_key=api_key_usuario)
        df = pd.read_excel(archivo_subido)
        datos_finales = []
        
        palabras_fuertes = ['denuncia', 'whistleblowing', 'etico', 'ética', 'compliance']
        secciones_sospechosas = ['contacto', 'legal', 'sostenibilidad', 'corporativo', 'empresa', 'rsc']
        
        tiempo_inicio = time.time()
        barra_progreso = st.progress(0, text="Iniciando auditoría...")
        total_empresas = len(df)
        
        st.subheader("⏳ Procesamiento en Tiempo Real")
        contenedor_resultados = st.container()
        
        for index, row in df.iterrows():
            empresa = row['Company Name'] 
            url_base = row['Web site'] if 'Web site' in df.columns else row.get('Web')
            
            url_canal = "No encontrado"
            canal_operativo = "No" 
            anonimato_ok = "No"
            confidencialidad_ok = "No"
            evidencia_anonimato = "N/A"
            evidencia_confidencialidad = "N/A"
            puntuacion_total = 0
                
            if pd.notna(url_base):
                if not str(url_base).startswith('http'):
                    url_base = 'http://' + str(url_base)
                    
                try:
                    headers = {'User-Agent': 'Mozilla/5.0'} 
                    respuesta = requests.get(url_base, headers=headers, timeout=10)
                    soup = BeautifulSoup(respuesta.text, 'html.parser')
                    
                    enlaces = soup.find_all('a', href=True)
                    canal_encontrado = None
                    enlaces_secundarios = []
                    
                    for enlace in enlaces:
                        href = enlace['href'].lower()
                        texto = enlace.get_text().lower()
                        if any(p in href for p in palabras_fuertes) or any(p in texto for p in palabras_fuertes):
                            canal_encontrado = urllib.parse.urljoin(url_base, enlace['href'])
                            break 
                        if any(sec in href for sec in secciones_sospechosas):
                            enlaces_secundarios.append(urllib.parse.urljoin(url_base, enlace['href']))
                    
                    if not canal_encontrado and enlaces_secundarios:
                        for url_secundaria in list(set(enlaces_secundarios))[:3]:
                            try:
                                time.sleep(1) 
                                resp_sec = requests.get(url_secundaria, headers=headers, timeout=5)
                                soup_sec = BeautifulSoup(resp_sec.text, 'html.parser')
                                enlaces_sec = soup_sec.find_all('a', href=True)
                                for e in enlaces_sec:
                                    href_sec = e['href'].lower()
                                    texto_sec = e.get_text().lower()
                                    if any(p in href_sec for p in palabras_fuertes) or any(p in texto_sec for p in palabras_fuertes):
                                        canal_encontrado = urllib.parse.urljoin(url_secundaria, e['href'])
                                        break
                                if canal_encontrado:
                                    break 
                            except:
                                pass 
                            
                    if canal_encontrado:
                        url_canal = canal_encontrado
                        puntuacion_total += 20 
                        
                        try:
                            time.sleep(1)
                            resp_canal = requests.get(canal_encontrado, headers=headers, timeout=10)
                            texto_canal = ""
                            
                            soup_canal_interior = BeautifulSoup(resp_canal.text, 'html.parser')
                            if soup_canal_interior.find('form') or 'mailto:' in resp_canal.text:
                                canal_operativo = "Sí"
                                puntuacion_total += 20 
        
                            if canal_encontrado.lower().endswith('.pdf') or 'application/pdf' in resp_canal.headers.get('Content-Type', ''):
                                pdf_archivo = io.BytesIO(resp_canal.content)
                                lector = PyPDF2.PdfReader(pdf_archivo)
                                for pagina in lector.pages:
                                    texto_extraido = pagina.extract_text()
                                    if texto_extraido:
                                        texto_canal += texto_extraido
                            else:
                                texto_canal = soup_canal_interior.get_text()
                            
                            if texto_canal:
                                texto_acotado = texto_canal[:15000] 
                                prompt = f"""
                                Eres un auditor estrictamente analítico. Lee el texto y responde ÚNICAMENTE con un objeto JSON válido.
                                Extrae todas las frases que hablen de anonimato y confidencialidad indicando el apartado del que salen.
                                Formato obligatorio:
                                {{
                                    "anonimato": "SÍ" o "NO",
                                    "citas_anonimato": [{{"seccion": "nombre apartado", "cita": "Frase literal exacta"}}],
                                    "confidencialidad": "SÍ" o "NO",
                                    "citas_confidencialidad": [{{"seccion": "nombre apartado", "cita": "Frase literal exacta"}}]
                                }}
                                Texto: {texto_acotado}
                                """
                                
                                resultados_rondas = []
                                for ronda in range(3):
                                    try:
                                        respuesta_ia = cliente_ia.models.generate_content(
                                            model='gemini-3.6-flash',
                                            contents=prompt,
                                            config=types.GenerateContentConfig(
                                                temperature=0.0,
                                                response_mime_type="application/json"
                                            )
                                        )
                                        json_texto = respuesta_ia.text.replace('```json', '').replace('```', '').strip()
                                        resultados_rondas.append(json.loads(json_texto))
                                        time.sleep(1)
                                    except Exception:
                                        time.sleep(2)
                                
                                if resultados_rondas:
                                    votos_anon = sum(1 for r in resultados_rondas if r.get("anonimato", "NO").upper() == "SÍ")
                                    votos_conf = sum(1 for r in resultados_rondas if r.get("confidencialidad", "NO").upper() == "SÍ")
                                    
                                    todas_citas_anon = []
                                    todas_citas_conf = []
                                    
                                    for r in resultados_rondas:
                                        for cita in r.get("citas_anonimato", []):
                                            texto_cita = f"[{cita.get('seccion', 'N/A')}] {cita.get('cita', '')}"
                                            if texto_cita not in todas_citas_anon and len(cita.get('cita', '')) > 5:
                                                todas_citas_anon.append(texto_cita)
                                        for cita in r.get("citas_confidencialidad", []):
                                            texto_cita = f"[{cita.get('seccion', 'N/A')}] {cita.get('cita', '')}"
                                            if texto_cita not in todas_citas_conf and len(cita.get('cita', '')) > 5:
                                                todas_citas_conf.append(texto_cita)
                                                
                                    if votos_anon >= 2:
                                        puntuacion_total += 30
                                        anonimato_ok = "Sí"
                                        evidencia_anonimato = " | ".join(todas_citas_anon) if todas_citas_anon else "Evidencia detectada"
                                        
                                    if votos_conf >= 2:
                                        puntuacion_total += 30
                                        confidencialidad_ok = "Sí"
                                        evidencia_confidencialidad = " | ".join(todas_citas_conf) if todas_citas_conf else "Evidencia detectada"
                                        
                        except Exception:
                            pass
                except Exception:
                    url_canal = "Error de conexión"
        
            with contenedor_resultados:
                if puntuacion_total >= 80:
                    st.success(f"🟢 **{empresa}** - ICOW: {puntuacion_total}/100")
                elif puntuacion_total >= 40:
                    st.warning(f"🟡 **{empresa}** - ICOW: {puntuacion_total}/100")
                else:
                    st.error(f"🔴 **{empresa}** - ICOW: {puntuacion_total}/100")
            
            fila_resultado = row.to_dict()
            fila_resultado.update({
                'Auditoría: URL del Canal': url_canal,
                'Auditoría: Canal Operativo': canal_operativo,
                'Auditoría: Anonimato': anonimato_ok,
                'Auditoría: Cita Anonimato': evidencia_anonimato,
                'Auditoría: Confidencialidad': confidencialidad_ok,
                'Auditoría: Cita Confidencialidad': evidencia_confidencialidad,
                'Auditoría: Puntuación ICOW': puntuacion_total
            })
            datos_finales.append(fila_resultado)
            
            progreso_actual = (index + 1) / total_empresas
            tiempo_transcurrido = time.time() - tiempo_inicio
            tiempo_por_empresa = tiempo_transcurrido / (index + 1)
            tiempo_restante_segundos = tiempo_por_empresa * (total_empresas - (index + 1))
            
            minutos = int(tiempo_restante_segundos // 60)
            segundos = int(tiempo_restante_segundos % 60)
            porcentaje = int(progreso_actual * 100)
            
            texto_barra = f"Procesando: {porcentaje}% completado | Tiempo estimado restante: {minutos} min {segundos} seg"
            barra_progreso.progress(progreso_actual, text=texto_barra)
            
        # ==========================================
        # DASHBOARD FINAL (TABLAS Y RAZONAMIENTOS)
        # ==========================================
        st.balloons()
        df_resultados = pd.DataFrame(datos_finales)
        
        st.markdown("---")
        st.header("📈 Dashboard de Resultados Globales")
        
        # 1. Gráficos
        if not df_resultados.empty:
            df_graficos = df_resultados.copy()
            df_graficos.rename(columns={'Auditoría: Puntuación ICOW': 'Puntuacion ICOW', 'Auditoría: Canal Operativo': 'Canal Operativo'}, inplace=True)
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Comparativa de Puntuación ICOW")
                st.bar_chart(df_graficos.set_index("Company Name")["Puntuacion ICOW"])
            with col2:
                st.subheader("Estado de Operatividad del Canal")
                operatividad_counts = df_graficos['Canal Operativo'].value_counts()
                st.bar_chart(operatividad_counts, color="#ffaa00")

        # 2. Tabla completa
        st.markdown("---")
        st.subheader("📋 Matriz de Datos Completa")
        st.dataframe(df_resultados, use_container_width=True)

        # 3. Fichas de razonamiento interactivo por empresa
        st.markdown("---")
        st.subheader("🔍 Análisis Detallado y Justificación Jurídica")
        st.write("Haz clic en cualquier empresa para revisar las evidencias extraídas por la Inteligencia Artificial:")
        
        for index, row in df_resultados.iterrows():
            with st.expander(f"🏢 {row['Company Name']} - Puntuación ICOW: {row['Auditoría: Puntuación ICOW']}/100"):
                st.markdown(f"**URL Detectada:** {row['Auditoría: URL del Canal']}")
                st.markdown(f"**Mecanismo de Envío (Formulario/Email):** {row['Auditoría: Canal Operativo']}")
                st.markdown("---")
                st.markdown(f"**🕵️‍♂️ Evaluación de Anonimato:** {row['Auditoría: Anonimato']}")
                st.info(f"**Evidencia literal:** {row['Auditoría: Cita Anonimato']}")
                st.markdown(f"**🔐 Evaluación de Confidencialidad:** {row['Auditoría: Confidencialidad']}")
                st.success(f"**Evidencia literal:** {row['Auditoría: Cita Confidencialidad']}")

        # 4. Descarga
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_resultados.to_excel(writer, index=False)
        datos_excel = output.getvalue()
        
        st.markdown("---")
        st.subheader("💾 Exportación de Resultados")
        st.download_button(
            label="📥 Descargar Base de Datos Científica (.xlsx)",
            data=datos_excel,
            file_name="Resultados_Auditoria_TFG.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
