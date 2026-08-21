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
from datetime import datetime

# ==========================================
# CONFIGURACIÓN Y MEMORIA HISTÓRICA
# ==========================================
st.set_page_config(page_title="Auditor TFG - Ley 2/2023", page_icon="🕵️‍♂️", layout="wide")

# Inicializar la "Memoria" del programa para guardar el histórico
if 'historial_datos' not in st.session_state:
    st.session_state.historial_datos = pd.DataFrame()

st.title("🕵️‍♂️ Auditor OSINT: Canales de Denuncia (Ley 2/2023)")
st.markdown("Herramienta de análisis metodológico con memoria histórica y control de IA para el Trabajo de Fin de Grado.")

# ==========================================
# BARRA LATERAL
# ==========================================
with st.sidebar:
    st.header("⚙️ Configuración")
    api_key_usuario = st.text_input("1. Introduce tu API Key de Gemini:", type="password")
    archivo_subido = st.file_uploader("2. Sube tu base de datos (Excel SABI)", type=["xlsx"])
    
    st.markdown("---")
    st.header("🎛️ Parámetros Metodológicos")
    # AÑADIDO: Selector de repeticiones de la IA
    rondas_ia = st.slider("Rondas de Consenso IA (Precisión vs Agilidad):", min_value=1, max_value=5, value=3, help="1 = Más rápido / 3+ = Máxima precisión científica")
    
    st.info("El archivo debe contener las columnas 'Company Name' y 'Web' o 'Web site'.")

# ==========================================
# MOTOR DEL PROGRAMA
# ==========================================
if st.button("🚀 Iniciar Auditoría", type="primary"):
    
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
        
        # Etiqueta de la ejecución para el histórico
        timestamp_ejecucion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
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
            
            # AÑADIDO: Separación de puntuaciones
            puntuacion_base = 0  # Sin IA (Máx 40)
            puntuacion_ia = 0    # Con IA (Máx 60)
                
        if pd.notna(url_base):
                # CAMBIO 1: Forzamos conexión segura HTTPS (vital para webs corporativas)
                if not str(url_base).startswith('http'):
                    url_base = 'https://' + str(url_base)
                    
                try:
                    # CAMBIO 2: Disfraz humano avanzado (evita bloqueos anti-bots)
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
                        'Connection': 'keep-alive'
                    } 
                    # CAMBIO 3: Aumentamos el timeout a 15 segundos por si la web es lenta
                    respuesta = requests.get(url_base, headers=headers, timeout=15)
                    
                    # Ignorar errores de certificado SSL temporales que a veces tienen las empresas
                    respuesta.raise_for_status()
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
                        puntuacion_base += 20 # Determinista (Sin IA)
                        
                        try:
                            time.sleep(1)
                            resp_canal = requests.get(canal_encontrado, headers=headers, timeout=10)
                            texto_canal = ""
                            
                            soup_canal_interior = BeautifulSoup(resp_canal.text, 'html.parser')
                            if soup_canal_interior.find('form') or 'mailto:' in resp_canal.text:
                                canal_operativo = "Sí"
                                puntuacion_base += 20 # Determinista (Sin IA)
        
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
                                # AÑADIDO: El bucle ahora depende del slider (rondas_ia)
                                for ronda in range(rondas_ia):
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
                                    
                                    # Lógica de mayoría adaptable según las rondas elegidas
                                    mayoria = (rondas_ia // 2) + 1
                                            
                                    if votos_anon >= mayoria:
                                        puntuacion_ia += 30
                                        anonimato_ok = "Sí"
                                        evidencia_anonimato = " | ".join(todas_citas_anon) if todas_citas_anon else "Evidencia detectada"
                                        
                                    if votos_conf >= mayoria:
                                        puntuacion_ia += 30
                                        confidencialidad_ok = "Sí"
                                        evidencia_confidencialidad = " | ".join(todas_citas_conf) if todas_citas_conf else "Evidencia detectada"
                                        
                        except Exception:
                            pass
                except Exception:
                    url_canal = "Error de conexión"
        
            puntuacion_total = puntuacion_base + puntuacion_ia
            
            with contenedor_resultados:
                st.write(f"🏢 **{empresa}** -> **ICOW Base (Sin IA):** {puntuacion_base}/40 | **ICOW Total:** {puntuacion_total}/100")
            
            fila_resultado = row.to_dict()
            fila_resultado.update({
                'ID_Ejecución': timestamp_ejecucion,
                'Rondas_IA': rondas_ia,
                'Auditoría: URL del Canal': url_canal,
                'Auditoría: Canal Operativo': canal_operativo,
                'Auditoría: ICOW Base (SIN IA)': puntuacion_base,
                'Auditoría: Anonimato': anonimato_ok,
                'Auditoría: Cita Anonimato': evidencia_anonimato,
                'Auditoría: Confidencialidad': confidencialidad_ok,
                'Auditoría: Cita Confidencialidad': evidencia_confidencialidad,
                'Auditoría: Puntuación ICOW TOTAL': puntuacion_total
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
            
        st.balloons()
        df_resultados = pd.DataFrame(datos_finales)
        
        # Guardar en la memoria global
        st.session_state.historial_datos = pd.concat([st.session_state.historial_datos, df_resultados], ignore_index=True)
        
        # ==========================================
        # DASHBOARD Y RESULTADOS
        # ==========================================
        st.markdown("---")
        
        tab1, tab2 = st.tabs(["📊 Análisis Actual", "📚 Memoria Histórica"])
        
        with tab1:
            st.header(f"Resultados de la muestra actual ({rondas_ia} Rondas IA)")
            if not df_resultados.empty:
                df_graficos = df_resultados.copy()
                # CORREZIONE: Rinominiamo TUTTE le colonne usate nei grafici per togliere i due punti (:)
                df_graficos.rename(columns={
                    'Auditoría: Puntuación ICOW TOTAL': 'ICOW Total', 
                    'Auditoría: ICOW Base (SIN IA)': 'ICOW Base',
                    'Auditoría: Canal Operativo': 'Canal Operativo'
                }, inplace=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("Comparativa: ICOW Base (Sin IA) vs ICOW Total")
                    # Muestra las dos barras comparadas para evidenciar el aporte de la IA
                    st.bar_chart(df_graficos.set_index("Company Name")[['ICOW Base', 'ICOW Total']])
                with col2:
                    st.subheader("Estado de Operatividad (Determinista)")
                    # Ora usa la colonna rinominata senza i due punti
                    st.bar_chart(df_graficos['Canal Operativo'].value_counts(), color="#ffaa00")

            st.subheader("📋 Matriz de Datos")
            st.dataframe(df_resultados, use_container_width=True)

            for index, row in df_resultados.iterrows():
                with st.expander(f"🏢 {row['Company Name']} - Base: {row['Auditoría: ICOW Base (SIN IA)']} | Total: {row['Auditoría: Puntuación ICOW TOTAL']}"):
                    st.write(f"**URL:** {row['Auditoría: URL del Canal']} | **Operativo:** {row['Auditoría: Canal Operativo']}")
                    st.write(f"**Anonimato:** {row['Auditoría: Anonimato']}")
                    st.info(f"{row['Auditoría: Cita Anonimato']}")
                    st.write(f"**Confidencialidad:** {row['Auditoría: Confidencialidad']}")
                    st.success(f"{row['Auditoría: Cita Confidencialidad']}")

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_resultados.to_excel(writer, index=False)
            st.download_button("📥 Descargar Excel (Muestra Actual)", data=output.getvalue(), file_name="Auditoria_Actual.xlsx")

        with tab2:
            st.header("Histórico de todas las pruebas")
            st.write("Aquí se acumulan todas las pruebas que hagas mientras no cierres esta pestaña web. Ideal para comparar el mismo Excel con 1 ronda de IA frente a 5 rondas.")
            st.dataframe(st.session_state.historial_datos, use_container_width=True)
            
            if not st.session_state.historial_datos.empty:
                output_hist = io.BytesIO()
                with pd.ExcelWriter(output_hist, engine='xlsxwriter') as writer:
                    st.session_state.historial_datos.to_excel(writer, index=False)
                st.download_button("📥 Descargar TODO el Histórico Consolidado", data=output_hist.getvalue(), file_name="Historico_Global_TFG.xlsx", type="primary")
