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
# CONFIGURACIÓN ÉTICA Y MEMORIA HISTÓRICA
# ==========================================
st.set_page_config(page_title="Auditor ICOW - Ley 2/2023", page_icon="📊", layout="wide")

if 'historial_datos' not in st.session_state:
    st.session_state.historial_datos = pd.DataFrame()

st.title("📊 Observatorio OSINT de Transparencia Declarada (Ley 2/2023)")
st.markdown("""
**Marco Metodológico:** Esta herramienta evalúa exclusivamente la **transparencia declarada** en fuentes públicas sobre los Sistemas Internos de Información (Índice ICOW), sin auditar el funcionamiento interno real. Los resultados visuales se presentan de forma **agregada y anonimizada** con fines estrictamente académicos y propositivos.
""")

# ==========================================
# BARRA LATERAL Y CONFIGURACIÓN
# ==========================================
with st.sidebar:
    st.header("⚙️ Configuración Técnica")
    api_key_usuario = st.text_input("1. API Key de Gemini:", type="password")
    archivo_subido = st.file_uploader("2. Sube el Excel de la muestra", type=["xlsx"])
    
    st.markdown("---")
    st.header("🎛️ Rigor Metodológico")
    rondas_ia = st.slider("Rondas de Consenso IA (Paso 3):", min_value=1, max_value=5, value=3)
    max_paginas = st.slider("Profundidad de páginas web por empresa (Paso 2):", min_value=2, max_value=10, value=5)
    ocultar_nombres = st.checkbox("Anonimizar nombres en tablas (Código Sujeto_X)", value=True)

# ==========================================
# PASO 1: LECTURA Y COMPRENSIÓN DEL EXCEL
# ==========================================
if archivo_subido:
    df_input = pd.read_excel(archivo_subido)
    columnas = list(df_input.columns)
    
    st.subheader("📁 Paso 1: Reconocimiento de la Base de Datos")
    st.write(f"Archivo cargado correctamente: **{len(df_input)} registros** y **{len(columnas)} variables** detectadas.")
    
    # Detección inteligente de columnas por defecto
    idx_nombre = next((i for i, c in enumerate(columnas) if any(k in c.lower() for k in ['company', 'nombre', 'empresa', 'razon', 'razón'])), 0)
    idx_web = next((i for i, c in enumerate(columnas) if any(k in c.lower() for k in ['web', 'url', 'site', 'dominio'])), min(1, len(columnas)-1))
    
    col_map1, col_map2 = st.columns(2)
    with col_map1:
        col_empresa = st.selectbox("Columna identificativa de la entidad:", columnas, index=idx_nombre)
    with col_map2:
        col_url = st.selectbox("Columna con la dirección Web (URL):", columnas, index=idx_web)

    # ==========================================
    # EJECUCIÓN DE LOS PASOS 2 Y 3
    # ==========================================
    if st.button("🚀 Iniciar Análisis Secuencial (Pasos 2 y 3)", type="primary"):
        if not api_key_usuario:
            st.error("⚠️ Introduce tu API Key de Gemini en la barra lateral para ejecutar el Paso 3.")
        else:
            cliente_ia = genai.Client(api_key=api_key_usuario)
            datos_finales = []
            
            # Diccionarios objetivos del Paso 2
            palabras_clave_estrictas = ['denuncia', 'whistleblowing', 'etico', 'ética', 'compliance', 'informante', 'ley 2/2023', 'canal interno']
            rutas_exploracion = ['contacto', 'legal', 'sostenibilidad', 'corporativo', 'empresa', 'rsc', 'transparencia', 'gobierno', 'aviso']
            
            tiempo_inicio = time.time()
            barra_progreso = st.progress(0, text="Iniciando secuencia de análisis...")
            total_empresas = len(df_input)
            timestamp_ejecucion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
                'Connection': 'keep-alive'
            }

            for index, row in df_input.iterrows():
                codigo_sujeto = f"Sujeto_{index + 1:03d}"
                nombre_real = str(row[col_empresa])
                url_base = row[col_url]
                
                # Variables de estado
                paginas_rastreadas = 0
                conteo_keywords = 0
                url_canal = "No detectado públicamente"
                canal_operativo = "No"
                anonimato_ok = "No declarado"
                confidencialidad_ok = "No declarada"
                evidencia_anonimato = "Sin mención explícita en texto público"
                evidencia_confidencialidad = "Sin mención explícita en texto público"
                sugerencia_mejora = "Publicar acceso visible al Sistema Interno de Información en la página principal."
                
                puntuacion_paso2_sin_ia = 0
                puntuacion_paso3_con_ia = 0
                
                if pd.notna(url_base) and str(url_base).strip() != "":
                    url_base = str(url_base).strip()
                    if not url_base.startswith('http'):
                        url_base = 'https://' + url_base
                        
                    # ---------------------------------------------------------
                    # PASO 2: EXAMEN TÉCNICO DE PALABRAS CLAVE (SIN IA)
                    # ---------------------------------------------------------
                    try:
                        resp_portada = requests.get(url_base, headers=headers, timeout=15)
                        paginas_rastreadas += 1
                        soup_portada = BeautifulSoup(resp_portada.text, 'html.parser')
                        
                        dominio_base = urllib.parse.urlparse(url_base).netloc
                        enlaces_internos = []
                        urls_candidatas_canal = []
                        
                        for a in soup_portada.find_all('a', href=True):
                            href_limpio = a['href'].lower()
                            texto_limpio = a.get_text().lower()
                            url_completa = urllib.parse.urljoin(url_base, a['href'])
                            
                            # Si tiene palabra clave directa
                            if any(k in href_limpio or k in texto_limpio for k in palabras_clave_estrictas):
                                if url_completa not in urls_candidatas_canal:
                                    urls_candidatas_canal.append(url_completa)
                            # Si es una subpágina relevante del mismo dominio para explorar
                            elif any(r in href_limpio or r in texto_limpio for r in rutas_exploracion):
                                if urllib.parse.urlparse(url_completa).netloc == dominio_base and url_completa not in enlaces_internos:
                                    enlaces_internos.append(url_completa)
                        
                        # Explorar todas las páginas internas hasta el límite configurado
                        for url_int in enlaces_internos[:max_paginas]:
                            try:
                                time.sleep(0.5)
                                resp_int = requests.get(url_int, headers=headers, timeout=10)
                                paginas_rastreadas += 1
                                soup_int = BeautifulSoup(resp_int.text, 'html.parser')
                                
                                # Contar apariciones de palabras clave en esta página
                                texto_pag = soup_int.get_text().lower()
                                conteo_keywords += sum(texto_pag.count(k) for k in palabras_clave_estrictas)
                                
                                for a_sec in soup_int.find_all('a', href=True):
                                    h_sec = a_sec['href'].lower()
                                    t_sec = a_sec.get_text().lower()
                                    if any(k in h_sec or k in t_sec for k in palabras_clave_estrictas):
                                        url_hallada = urllib.parse.urljoin(url_int, a_sec['href'])
                                        if url_hallada not in urls_candidatas_canal:
                                            urls_candidatas_canal.append(url_hallada)
                            except Exception:
                                pass
                        
                        # Consolidar textos de las páginas del canal para el Paso 3
                        texto_acumulado_canal = ""
                        if urls_candidatas_canal:
                            url_canal = urls_candidatas_canal[0]
                            puntuacion_paso2_sin_ia += 20  # Visibilidad pública confirmada
                            
                            # Analizar hasta 3 enlaces de canal/documentos normativos encontrados
                            for u_canal in urls_candidatas_canal[:3]:
                                try:
                                    time.sleep(0.5)
                                    r_can = requests.get(u_canal, headers=headers, timeout=15)
                                    paginas_rastreadas += 1
                                    
                                    if u_canal.lower().endswith('.pdf') or 'application/pdf' in r_can.headers.get('Content-Type', ''):
                                        lector = PyPDF2.PdfReader(io.BytesIO(r_can.content))
                                        for pag in lector.pages[:10]:
                                            t_pdf = pag.extract_text()
                                            if t_pdf:
                                                texto_acumulado_canal += "\n" + t_pdf
                                    else:
                                        s_can = BeautifulSoup(r_can.text, 'html.parser')
                                        if s_can.find('form') or 'mailto:' in r_can.text or any(ext in u_canal.lower() for ext in ['eqs', 'navex', 'whistle', 'factorial', 'ethic']):
                                            canal_operativo = "Sí"
                                        texto_acumulado_canal += "\n" + s_can.get_text(separator=' ', strip=True)
                                except Exception:
                                    pass
                                    
                            if canal_operativo == "Sí":
                                puntuacion_paso2_sin_ia += 20
                            
                            conteo_keywords += sum(texto_acumulado_canal.lower().count(k) for k in palabras_clave_estrictas)

                        # ---------------------------------------------------------
                        # PASO 3: EXAMEN SEMÁNTICO CON IA (TRANSPARENCIA DECLARADA)
                        # ---------------------------------------------------------
                        if texto_acumulado_canal.strip():
                            texto_acotado = texto_acumulado_canal[:18000]
                            prompt = f"""
                            Actúa como un evaluador objetivo de transparencia pública conforme a la Ley 2/2023.
                            Evalúa únicamente lo que el texto declara explícitamente, sin suponer ni juzgar el funcionamiento interno real.
                            Devuelve ÚNICAMENTE un objeto JSON válido con esta estructura exacta:
                            {{
                                "anonimato": "SÍ" o "NO",
                                "citas_anonimato": [{{"seccion": "apartado o contexto", "cita": "frase literal exacta"}}],
                                "confidencialidad": "SÍ" o "NO",
                                "citas_confidencialidad": [{{"seccion": "apartado o contexto", "cita": "frase literal exacta"}}],
                                "sugerencia_constructiva": "Breve recomendación técnica y neutral de mejora de transparencia (máximo 1 frase)"
                            }}
                            Texto público extraído:
                            {texto_acotado}
                            """
                            
                            resultados_rondas = []
                            for _ in range(rondas_ia):
                                try:
                                    respuesta_ia = cliente_ia.models.generate_content(
                                        model='gemini-3.6-flash',
                                        contents=prompt,
                                        config=types.GenerateContentConfig(
                                            temperature=0.0,
                                            response_mime_type="application/json"
                                        )
                                    )
                                    json_limpio = respuesta_ia.text.replace('```json', '').replace('```', '').strip()
                                    resultados_rondas.append(json.loads(json_limpio))
                                    time.sleep(1)
                                except Exception:
                                    time.sleep(2)
                                    
                            if resultados_rondas:
                                mayoria = (rondas_ia // 2) + 1
                                votos_anon = sum(1 for r in resultados_rondas if r.get("anonimato", "NO").upper() == "SÍ")
                                votos_conf = sum(1 for r in resultados_rondas if r.get("confidencialidad", "NO").upper() == "SÍ")
                                
                                citas_a, citas_c = [], []
                                for r in resultados_rondas:
                                    for c in r.get("citas_anonimato", []):
                                        txt = f"[{c.get('seccion', 'Texto')}] {c.get('cita', '')}"
                                        if txt not in citas_a and len(c.get('cita', '')) > 5:
                                            citas_a.append(txt)
                                    for c in r.get("citas_confidencialidad", []):
                                        txt = f"[{c.get('seccion', 'Texto')}] {c.get('cita', '')}"
                                        if txt not in citas_c and len(c.get('cita', '')) > 5:
                                            citas_c.append(txt)
                                            
                                if votos_anon >= mayoria:
                                    puntuacion_paso3_con_ia += 30
                                    anonimato_ok = "Declarado"
                                    evidencia_anonimato = " | ".join(citas_a) if citas_a else "Declarado en texto"
                                    
                                if votos_conf >= mayoria:
                                    puntuacion_paso3_con_ia += 30
                                    confidencialidad_ok = "Declarada"
                                    evidencia_confidencialidad = " | ".join(citas_c) if citas_c else "Declarada en texto"
                                    
                                sugerencia_mejora = resultados_rondas[0].get("sugerencia_constructiva", sugerencia_mejora)
                                
                    except Exception:
                        url_canal = "Web inaccesible o bloqueo de servidor"
                        sugerencia_mejora = "Verificar accesibilidad pública del dominio corporativo."

                puntuacion_total = puntuacion_paso2_sin_ia + puntuacion_paso3_con_ia
                
                # Conservamos TODAS las casillas del Excel original y añadimos las métricas de los Pasos 2 y 3
                fila_resultado = row.to_dict()
                fila_resultado.update({
                    'ID_Muestra': timestamp_ejecucion,
                    'Codigo_Anonimizado': codigo_sujeto,
                    'Paso2_Paginas_Examinadas': paginas_rastreadas,
                    'Paso2_Frecuencia_Keywords': conteo_keywords,
                    'Paso2_Canal_Visible': "Sí" if puntuacion_paso2_sin_ia >= 20 else "No",
                    'Paso2_Mecanismo_Operativo': canal_operativo,
                    'Paso2_ICOW_Tecnico_Sin_IA': puntuacion_paso2_sin_ia,
                    'Paso3_Anonimato_Declarado': anonimato_ok,
                    'Paso3_Evidencia_Anonimato': evidencia_anonimato,
                    'Paso3_Confidencialidad_Declarada': confidencialidad_ok,
                    'Paso3_Evidencia_Confidencialidad': evidencia_confidencialidad,
                    'Paso3_ICOW_Semantico_IA': puntuacion_paso3_con_ia,
                    'ICOW_Total_Transparencia': puntuacion_total,
                    'Sugerencia_Constructiva': sugerencia_mejora
                })
                datos_finales.append(fila_resultado)
                
                # Actualizar barra con tiempo estimado
                progreso_actual = (index + 1) / total_empresas
                tiempo_transcurrido = time.time() - tiempo_inicio
                tiempo_restante = (tiempo_transcurrido / (index + 1)) * (total_empresas - (index + 1))
                mins, segs = int(tiempo_restante // 60), int(tiempo_restante % 60)
                barra_progreso.progress(progreso_actual, text=f"Analizando {codigo_sujeto} ({int(progreso_actual*100)}%) | Tiempo restante: {mins}m {segs}s")

            df_resultados = pd.DataFrame(datos_finales)
            st.session_state.historial_datos = pd.concat([st.session_state.historial_datos, df_resultados], ignore_index=True)

            # ==========================================
            # DASHBOARD DE RESULTADOS AGREGADOS (SIN SEÑALAR EMPRESAS)
            # ==========================================
            st.markdown("---")
            tab1, tab2 = st.tabs(["📊 Resultados Agregados de la Muestra", "📚 Histórico Comparativo de Muestras"])
            
            with tab1:
                st.header(" Diagnóstico Agregado de Transparencia Declarada")
                st.caption("Resultados estadísticos globales de la muestra analizada. No se exponen juicios individuales sobre entidades concretas.")
                
                # Métricas globales agregadas
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Media ICOW Técnico (Paso 2 - Sin IA)", f"{df_resultados['Paso2_ICOW_Tecnico_Sin_IA'].mean():.1f} / 40")
                m2.metric("Media ICOW Semántico (Paso 3 - IA)", f"{df_resultados['Paso3_ICOW_Semantico_IA'].mean():.1f} / 60")
                m3.metric("Media ICOW Total Transparencia", f"{df_resultados['ICOW_Total_Transparencia'].mean():.1f} / 100")
                pct_canal = (df_resultados['Paso2_Canal_Visible'] == 'Sí').mean() * 100
                m4.metric("% Entidades con Canal Visible", f"{pct_canal:.1f}%")
                
                st.markdown("---")
                col_g1, col_g2 = st.columns(2)
                
                with col_g1:
                    st.subheader("Distribución Agregada por Nivel de Transparencia")
                    # Clasificación agregada sin nombres de empresas
                    def clasificar_tramo(pts):
                        if pts >= 80: return "1. Transparencia Alta (80-100 pts)"
                        elif pts >= 40: return "2. Transparencia Media (40-79 pts)"
                        elif pts >= 20: return "3. Transparencia Básica (20-39 pts)"
                        else: return "4. Sin Evidencia Pública (0 pts)"
                        
                    conteo_tramos = df_resultados['ICOW_Total_Transparencia'].apply(clasificar_tramo).value_counts()
                    st.bar_chart(conteo_tramos)
                    
                with col_g2:
                    st.subheader("Desglose de Garantías Declaradas en la Muestra")
                    garantias_df = pd.DataFrame({
                        'Porcentaje de la Muestra (%)': [
                            (df_resultados['Paso2_Canal_Visible'] == 'Sí').mean() * 100,
                            (df_resultados['Paso2_Mecanismo_Operativo'] == 'Sí').mean() * 100,
                            (df_resultados['Paso3_Anonimato_Declarado'] == 'Declarado').mean() * 100,
                            (df_resultados['Paso3_Confidencialidad_Declarada'] == 'Declarada').mean() * 100
                        ]
                    }, index=['1. Canal Localizado', '2. Mecanismo Operativo', '3. Anonimato Declarado', '4. Confidencialidad Declarada'])
                    st.bar_chart(garantias_df)

                st.markdown("---")
                st.subheader("📋 Matriz de Datos del Estudio")
                df_vista = df_resultados.copy()
                if ocultar_nombres and col_empresa in df_vista.columns:
                    df_vista[col_empresa] = df_vista['Codigo_Anonimizado']
                    if col_url in df_vista.columns:
                        df_vista[col_url] = "[URL Oculta - Modo Anonimizado]"
                st.dataframe(df_vista, use_container_width=True)

                st.markdown("---")
                st.subheader("🔍 Revisión Metodológica y Sugerencias por Sujeto")
                for _, fila in df_resultados.iterrows():
                    etiqueta = fila['Codigo_Anonimizado'] if ocultar_nombres else f"{fila['Codigo_Anonimizado']} ({fila[col_empresa]})"
                    with st.expander(f"📄 {etiqueta} | Paso 2 (Sin IA): {fila['Paso2_ICOW_Tecnico_Sin_IA']}/40 | Total ICOW: {fila['ICOW_Total_Transparencia']}/100"):
                        st.write(f"**Paso 2 (Rastreo Técnico sin IA):** {fila['Paso2_Paginas_Examinadas']} páginas internas examinadas | {fila['Paso2_Frecuencia_Keywords']} coincidencias léxicas | Mecanismo operativo: {fila['Paso2_Mecanismo_Operativo']}")
                        st.write(f"**Paso 3 (Anonimato Declarado):** {fila['Paso3_Anonimato_Declarado']}")
                        st.info(f"Cita textual: {fila['Paso3_Evidencia_Anonimato']}")
                        st.write(f"**Paso 3 (Confidencialidad Declarada):** {fila['Paso3_Confidencialidad_Declarada']}")
                        st.success(f"Cita textual: {fila['Paso3_Evidencia_Confidencialidad']}")
                        st.warning(f"💡 **Propuesta de mejora:** {fila['Sugerencia_Constructiva']}")

                output_actual = io.BytesIO()
                with pd.ExcelWriter(output_actual, engine='xlsxwriter') as writer:
                    df_resultados.to_excel(writer, index=False)
                st.download_button("📥 Descargar Excel Completo con Todas las Casillas", data=output_actual.getvalue(), file_name="Resultados_ICOW_Muestra.xlsx", type="primary")

            with tab2:
                st.header("📚 Comparativa Histórica de Ejecuciones")
                if not st.session_state.historial_datos.empty:
                    resumen_hist = st.session_state.historial_datos.groupby('ID_Muestra')[['Paso2_ICOW_Tecnico_Sin_IA', 'Paso3_ICOW_Semantico_IA', 'ICOW_Total_Transparencia']].mean()
                    st.subheader("Evolución de Medias por Muestra Analizada")
                    st.bar_chart(resumen_hist)
                    st.dataframe(st.session_state.historial_datos, use_container_width=True)
                    
                    output_hist = io.BytesIO()
                    with pd.ExcelWriter(output_hist, engine='xlsxwriter') as writer:
                        st.session_state.historial_datos.to_excel(writer, index=False)
                    st.download_button("📥 Descargar Histórico Consolidado (.xlsx)", data=output_hist.getvalue(), file_name="Historico_Consolidado_TFG.xlsx")
