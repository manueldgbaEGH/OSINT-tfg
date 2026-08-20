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

# ==========================================
# INTERFAZ DE USUARIO (EL ESCAPARATE)
# ==========================================
st.set_page_config(page_title="Auditor TFG - Ley 2/2023", page_icon="🕵️‍♂️", layout="wide")

st.title("🕵️‍♂️ Auditor OSINT: Canales de Denuncia (Ley 2/2023)")
st.markdown("Esta herramienta analiza páginas web corporativas para evaluar el **Índice de Cumplimiento Observable en Web (ICOW)** de los Sistemas Internos de Información mediante IA.")

# Barra lateral para configuraciones
with st.sidebar:
    st.header("⚙️ Configuración")
    api_key_usuario = st.text_input("1. Introduce tu API Key de Gemini:", type="password", help="Tu clave segura de Google AI Studio")
    archivo_subido = st.file_uploader("2. Sube tu base de datos (Excel SABI)", type=["xlsx"])
    st.info("El archivo debe contener las columnas 'Company Name' y 'Web' o 'Web site'.")

# ==========================================
# MOTOR DEL PROGRAMA (AL PULSAR EL BOTÓN)
# ==========================================
if st.button("🚀 Iniciar Auditoría Automatizada", type="primary"):
    
    if not api_key_usuario or not archivo_subido:
        st.error("⚠️ Por favor, introduce tu API Key y sube un archivo Excel para comenzar.")
    else:
        # Configurar la IA con la clave del usuario
        cliente_ia = genai.Client(api_key=api_key_usuario)
        
        # Leer el Excel
        df = pd.read_excel(archivo_subido)
        datos_finales = []
        
        palabras_fuertes = ['denuncia', 'whistleblowing', 'etico', 'ética', 'compliance']
        secciones_sospechosas = ['contacto', 'legal', 'sostenibilidad', 'corporativo', 'empresa', 'rsc']
        
        # Barra de progreso visual
        barra_progreso = st.progress(0)
        total_empresas = len(df)
        
        st.subheader("📊 Resultados del Análisis en Tiempo Real")
        contenedor_resultados = st.container() # Para ir imprimiendo debajo
        
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
                    
                    # PASO 1: Buscar en portada
                    for enlace in enlaces:
                        href = enlace['href'].lower()
                        texto = enlace.get_text().lower()
                        if any(p in href for p in palabras_fuertes) or any(p in texto for p in palabras_fuertes):
                            canal_encontrado = urllib.parse.urljoin(url_base, enlace['href'])
                            break 
                        if any(sec in href for sec in secciones_sospechosas):
                            enlaces_secundarios.append(urllib.parse.urljoin(url_base, enlace['href']))
                    
                    # PASO 2: Rastreo Profundo
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
                            
                    # PASO 3: EXTRACCIÓN Y ANÁLISIS IA
                    if canal_encontrado:
                        url_canal = canal_encontrado
                        puntuacion_total += 20 
                        
                        try:
                            time.sleep(1)
                            resp_canal = requests.get(canal_encontrado, headers=headers, timeout=10)
                            texto_canal = ""
                            
                            # Análisis de Operatividad
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
                                Eres un auditor de compliance legal. Lee el texto y responde ÚNICAMENTE con un objeto JSON válido.
                                No uses viñetas ni texto fuera del JSON. Las claves deben ser exactamente estas:
                                {{
                                    "anonimato": "SÍ" o "NO",
                                    "evidencia_anonimato": "Frase literal extraída del texto",
                                    "confidencialidad": "SÍ" o "NO",
                                    "evidencia_confidencialidad": "Frase literal extraída del texto"
                                }}
                                
                                Texto:
                                {texto_acotado}
                                """
                                exito_ia = False
                                for intento in range(3):
                                    try:
                                        respuesta_ia = cliente_ia.models.generate_content(
                                            model='gemini-3.6-flash',
                                            contents=prompt
                                        )
                                        json_texto = respuesta_ia.text.replace('```json', '').replace('```', '').strip()
                                        datos_ia = json.loads(json_texto)
                                        exito_ia = True
                                        break 
                                    except Exception:
                                        time.sleep(5)
                                
                                if exito_ia:
                                    if datos_ia.get("anonimato", "NO").upper() == "SÍ":
                                        puntuacion_total += 30
                                        anonimato_ok = "Sí"
                                        evidencia_anonimato = datos_ia.get("evidencia_anonimato", "")
                                        
                                    if datos_ia.get("confidencialidad", "NO").upper() == "SÍ":
                                        puntuacion_total += 30
                                        confidencialidad_ok = "Sí"
                                        evidencia_confidencialidad = datos_ia.get("evidencia_confidencialidad", "")
                                time.sleep(3) 
                        except Exception:
                            pass
                except Exception:
                    url_canal = "Error de conexión"
        
            # Imprimir resultado visual por empresa
            with contenedor_resultados:
                if puntuacion_total >= 80:
                    st.success(f"🟢 **{empresa}** - ICOW: {puntuacion_total}/100")
                elif puntuacion_total >= 40:
                    st.warning(f"🟡 **{empresa}** - ICOW: {puntuacion_total}/100")
                else:
                    st.error(f"🔴 **{empresa}** - ICOW: {puntuacion_total}/100")
            
            # Guardar fila
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
            
            # Actualizar barra de progreso
            progreso_actual = (index + 1) / total_empresas
            barra_progreso.progress(progreso_actual)
            
        # Al terminar, crear Excel descargable
        st.balloons()
        df_resultados = pd.DataFrame(datos_finales)
        
        # Convertir Excel a memoria para botón de descarga
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_resultados.to_excel(writer, index=False)
        datos_excel = output.getvalue()
        
        st.markdown("---")
        st.subheader("💾 Auditoría Finalizada")
        st.download_button(
            label="📥 Descargar Base de Datos con Resultados",
            data=datos_excel,
            file_name="Resultados_Auditoria_TFG.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )