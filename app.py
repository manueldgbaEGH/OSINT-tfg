import streamlit as st
import requests
from bs4 import BeautifulSoup
import urllib.parse
import time
import io
import PyPDF2
import json
from google import genai
from google.genai import types

# AÑADIDO: Librería para buscar en internet
try:
    from duckduckgo_search import DDGS
    BUSCADOR_DISPONIBLE = True
except ImportError:
    BUSCADOR_DISPONIBLE = False

# ==========================================
# INTERFAZ DEL PANEL DE MANDO FORENSE
# ==========================================
st.set_page_config(page_title="Panel OSINT Forense", page_icon="⚖️", layout="wide")

st.title("⚖️ Panel OSINT Forense: Prevención del Delito Corporativo")
st.markdown("Herramienta de investigación individual para revisores públicos. Analiza el cumplimiento normativo (Ley 2/2023) y rastrea la huella digital en busca de antecedentes, sanciones o alertas de riesgo.")

with st.sidebar:
    st.header("⚙️ Configuración")
    api_key_usuario = st.text_input("Introduce tu API Key de Gemini:", type="password")
    st.info("Herramienta configurada para análisis forense individual en profundidad.")

st.markdown("---")
st.subheader("🎯 Objetivo de la Investigación")

col1, col2 = st.columns(2)
with col1:
    empresa = st.text_input("Nombre de la Empresa (Ej. Iberdrola, Mercadona):")
with col2:
    url_base = st.text_input("Página Web (Ej. https://www.empresa.com):")

# ==========================================
# MOTOR FORENSE (DOBLE VÍA)
# ==========================================
if st.button("🔍 Iniciar Auditoría Forense Profunda", type="primary"):
    
    if not api_key_usuario or not empresa or not url_base:
        st.error("⚠️ Falta la API Key, el nombre de la empresa o la URL.")
    elif not BUSCADOR_DISPONIBLE:
        st.error("⚠️ Falta instalar 'duckduckgo-search' en el archivo requirements.txt")
    else:
        cliente_ia = genai.Client(api_key=api_key_usuario)
        
        # Limpieza de URL
        if not str(url_base).startswith('http'):
            url_base = 'https://' + str(url_base)
            
        barra_progreso = st.progress(0, text="Iniciando motores de inteligencia...")
        
        # =================================================================
        # MOTOR 1: BÚSQUEDA DE ANTECEDENTES Y SANCIONES (WEB GENERAL)
        # =================================================================
        barra_progreso.progress(20, text="Fase 1: Rastreando huella digital y antecedentes en internet...")
        
        alertas_ia = {}
        try:
            # Creamos un "Google Dork" para buscar fraudes
            query_riesgo = f'"{empresa}" AND (sanción OR multa OR fraude OR CNMC OR "Inspección de Trabajo" OR condena)'
            
            with DDGS() as ddgs:
                resultados_raw = list(ddgs.text(query_riesgo, region='es-es', max_results=10))
            
            if resultados_raw:
                # Le pasamos los resultados a la IA para que haga de filtro forense
                prompt_riesgo = f"""
                Eres un analista de inteligencia criminal. Revisa estos resultados de búsqueda sobre la empresa "{empresa}".
                Busca ÚNICAMENTE información sobre multas, sanciones, fraudes, investigaciones o problemas legales.
                Ignora noticias de auto-promoción o marketing.
                Responde EXCLUSIVAMENTE con un JSON válido con esta estructura:
                {{
                    "alerta_detectada": "SÍ" o "NO",
                    "hallazgos": [
                        {{
                            "riesgo": "Resumen de la sanción o noticia (máx 2 líneas)",
                            "fuente_url": "URL exacta de la noticia que te paso en los datos"
                        }}
                    ]
                }}
                Datos crudos de búsqueda: {json.dumps(resultados_raw)}
                """
                
                resp_riesgo = cliente_ia.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=prompt_riesgo,
                    config=types.GenerateContentConfig(temperature=0.0, response_mime_type="application/json")
                )
                json_riesgo = resp_riesgo.text.replace('```json', '').replace('```', '').strip()
                alertas_ia = json.loads(json_riesgo)
            else:
                alertas_ia = {"alerta_detectada": "NO", "hallazgos": []}
                
        except Exception as e:
            alertas_ia = {"alerta_detectada": "ERROR", "hallazgos": [{"riesgo": f"Error al buscar: {e}", "fuente_url": ""}]}

        # =================================================================
        # MOTOR 2: RASTREO PROFUNDO COMPLIANCE (LEY 2/2023)
        # =================================================================
        barra_progreso.progress(50, text="Fase 2: Extracción profunda del canal de denuncias...")
        
        puntuacion_icow = 0
        canal_operativo = "No detectado"
        anonimato_ok = "No"
        confidencialidad_ok = "No"
        citas_compliance = {}
        url_canal = "No encontrado"
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            }
            respuesta = requests.get(url_base, headers=headers, timeout=15)
            soup = BeautifulSoup(respuesta.text, 'html.parser')
            enlaces = soup.find_all('a', href=True)
            
            palabras_fuertes = ['denuncia', 'whistleblowing', 'etico', 'ética', 'compliance']
            enlaces_sospechosos = []
            
            # Recolectar enlaces interesantes
            for enlace in enlaces:
                href = enlace['href'].lower()
                texto = enlace.get_text().lower()
                url_absoluta = urllib.parse.urljoin(url_base, enlace['href'])
                
                if any(p in href or p in texto for p in palabras_fuertes):
                    if url_absoluta not in enlaces_sospechosos:
                        enlaces_sospechosos.append(url_absoluta)
            
            # Si no encuentra en portada, buscamos en legal o contacto
            if not enlaces_sospechosos:
                for sec in ['legal', 'contacto', 'corporativo']:
                    for enlace in enlaces:
                        if sec in enlace['href'].lower():
                            enlaces_sospechosos.append(urllib.parse.urljoin(url_base, enlace['href']))
            
            # Analizar el mejor enlace encontrado
            texto_canal = ""
            if enlaces_sospechosos:
                url_canal = enlaces_sospechosos[0] # Tomamos el más relevante
                puntuacion_icow += 20
                
                resp_canal = requests.get(url_canal, headers=headers, timeout=15)
                soup_canal = BeautifulSoup(resp_canal.text, 'html.parser')
                
                # Operatividad
                if soup_canal.find('form') or 'mailto:' in resp_canal.text:
                    canal_operativo = "Sí (Formulario o Email detectado)"
                    puntuacion_icow += 20
                    
                # Extracción PDF o HTML
                if url_canal.lower().endswith('.pdf') or 'application/pdf' in resp_canal.headers.get('Content-Type', ''):
                    pdf_archivo = io.BytesIO(resp_canal.content)
                    lector = PyPDF2.PdfReader(pdf_archivo)
                    for pagina in lector.pages[:10]: # Leemos hasta 10 páginas
                        t = pagina.extract_text()
                        if t: texto_canal += t
                else:
                    texto_canal = soup_canal.get_text()
                    
            barra_progreso.progress(80, text="Fase 3: Evaluación de la Inteligencia Artificial (Criminológica)...")
            
            # IA Analiza el Canal
            if texto_canal:
                prompt_canal = f"""
                Eres un auditor legal de compliance.
                Texto extraído: {texto_canal[:15000]}
                Devuelve ÚNICAMENTE un JSON:
                {{
                    "anonimato": "SÍ" o "NO",
                    "cita_anonimato": "Frase literal",
                    "confidencialidad": "SÍ" o "NO",
                    "cita_confidencialidad": "Frase literal"
                }}
                """
                resp_canal_ia = cliente_ia.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=prompt_canal,
                    config=types.GenerateContentConfig(temperature=0.0, response_mime_type="application/json")
                )
                citas_compliance = json.loads(resp_canal_ia.text.replace('```json', '').replace('```', '').strip())
                
                if citas_compliance.get("anonimato") == "SÍ":
                    puntuacion_icow += 30
                    anonimato_ok = "Sí"
                if citas_compliance.get("confidencialidad") == "SÍ":
                    puntuacion_icow += 30
                    confidencialidad_ok = "Sí"

        except Exception as e:
            url_canal = f"Error en rastreo: {e}"

        barra_progreso.progress(100, text="Investigación finalizada.")
        time.sleep(1)
        barra_progreso.empty()

        # ==========================================
        # DASHBOARD DE RESULTADOS
        # ==========================================
        st.markdown("---")
        st.header(f"📑 Informe de Inteligencia: {empresa}")
        
        tab1, tab2 = st.tabs(["🚨 Alertas de Riesgo (Antecedentes)", "🛡️ Auditoría Compliance (Ley 2/2023)"])
        
        # PESTAÑA 1: FORENSE / RIESGOS
        with tab1:
            st.subheader("Monitorización de Sanciones y Reputación")
            if alertas_ia.get("alerta_detectada") == "SÍ":
                st.error("⚠️ **¡ATENCIÓN!** Se han detectado posibles antecedentes, sanciones o investigaciones asociadas a esta empresa.")
                for hallazgo in alertas_ia.get("hallazgos", []):
                    st.warning(f"**Riesgo:** {hallazgo.get('riesgo')}")
                    # ESTE ES EL ENLACE CLICABLE DE LA FUENTE
                    st.markdown(f"🔗 **Fuente / Prueba:** [{hallazgo.get('fuente_url')}]({hallazgo.get('fuente_url')})")
                    st.markdown("---")
            elif alertas_ia.get("alerta_detectada") == "NO":
                st.success("🟢 No se han encontrado registros destacados de multas, sanciones o fraudes en fuentes abiertas recientes.")
            else:
                st.info("No se pudo realizar la búsqueda de antecedentes.")
                
        # PESTAÑA 2: COMPLIANCE
        with tab2:
            st.subheader(f"Índice de Cumplimiento Observable en Web (ICOW): {puntuacion_icow}/100")
            
            if puntuacion_icow >= 80:
                st.success("Cultura de Compliance: ALTA")
            elif puntuacion_icow >= 40:
                st.warning("Cultura de Compliance: MEDIA")
            else:
                st.error("Cultura de Compliance: BAJA")
                
            st.write(f"**URL del Canal Analizado:** {url_canal}")
            st.write(f"**Operatividad de Envío:** {canal_operativo}")
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("### 🕵️‍♂️ Garantía de Anonimato")
                st.write(f"**Veredicto:** {anonimato_ok}")
                if citas_compliance.get("cita_anonimato"):
                    st.info(f'"{citas_compliance.get("cita_anonimato")}"')
                    
            with col_b:
                st.markdown("### 🔐 Garantía de Confidencialidad")
                st.write(f"**Veredicto:** {confidencialidad_ok}")
                if citas_compliance.get("cita_confidencialidad"):
                    st.success(f'"{citas_compliance.get("cita_confidencialidad")}"')
