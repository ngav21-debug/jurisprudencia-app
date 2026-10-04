"""
Portal de Jurisprudencia para Suscriptores
Canal de Jurisprudencia · Nelson Arévalo
Aplicación web interactiva desarrollada en Streamlit con Buscador Semántico IA (Gemini).
"""

import os
import io
import datetime
import pandas as pd
import streamlit as st

# ==============================================================================
# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS
# ==============================================================================
st.set_page_config(
    page_title="Portal de Jurisprudencia | Suscriptores",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS personalizados
st.markdown("""
<style>
    .main-header {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        color: #03053A;
        font-weight: 700;
        margin-bottom: 0px;
    }
    .sub-header {
        color: #3D8FD6;
        font-size: 1.1rem;
        margin-top: -5px;
        margin-bottom: 20px;
    }
    .card-providencia {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-left: 5px solid #03053A;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 14px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .card-ia {
        background-color: #F8FAFC;
        border: 1px solid #CBD5E1;
        border-left: 5px solid #F2B544;
        border-radius: 8px;
        padding: 18px;
        margin-bottom: 20px;
    }
    .tag-corp {
        display: inline-block;
        background-color: #EBF8FF;
        color: #2B6CB0;
        font-size: 0.8rem;
        font-weight: 600;
        padding: 3px 8px;
        border-radius: 4px;
        margin-right: 6px;
    }
    .tag-fecha {
        display: inline-block;
        background-color: #EDF2F7;
        color: #4A5568;
        font-size: 0.8rem;
        padding: 3px 8px;
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. CONFIGURACIÓN Y CONSTANTES
# ==============================================================================
SPREADSHEET_ID = "1v-82olcq4QuLvNKoUswkjMe6Mcn42S5WLjpf2lZxsLw"
SHEET_TAB_ORIGEN = "Origen"
SHEET_TAB_SUSCRIPTORES = "Suscriptores"

# Intentar obtener API Key de Gemini desde variables de entorno o Streamlit Secrets
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY and "GEMINI_API_KEY" in st.secrets:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

# Lista de modelos soportados para fallback dinámico
GEMINI_MODELS_FALLBACK = [
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-1.5-flash-latest",
    "gemini-pro"
]

# ==============================================================================
# 3. CARGA DE DATOS DESDE GOOGLE SHEETS
# ==============================================================================
@st.cache_data(ttl=300)
def load_data():
    """Carga los datos de jurisprudencia y de suscriptores."""
    url_origen = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_TAB_ORIGEN}"
    url_suscriptores = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_TAB_SUSCRIPTORES}"
    
    try:
        df_juris = pd.read_csv(url_origen)
        df_juris.fillna("", inplace=True)
    except Exception as e:
        st.error(f"Error al cargar la base de jurisprudencia: {e}")
        df_juris = pd.DataFrame()
        
    try:
        df_subs = pd.read_csv(url_suscriptores)
        df_subs.fillna("", inplace=True)
        df_subs["Email"] = df_subs["Email"].astype(str).str.strip().str.lower()
        df_subs["Password"] = df_subs["Password"].astype(str).str.strip()
    except Exception as e:
        st.warning(f"Error al cargar la lista de suscriptores: {e}")
        df_subs = pd.DataFrame()

    return df_juris, df_subs

df_juris, df_subs = load_data()

# ==============================================================================
# 4. GESTIÓN DE SESIÓN Y AUTENTICACIÓN
# ==============================================================================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_info" not in st.session_state:
    st.session_state.user_info = None

def check_login(email_input, password_input):
    email_clean = email_input.strip().lower()
    pass_clean = password_input.strip()
    
    if df_subs.empty:
        return False, "La base de datos de suscriptores no está disponible."
    
    match = df_subs[(df_subs["Email"] == email_clean) & (df_subs["Password"] == pass_clean)]
    
    if match.empty:
        return False, "Correo electrónico o contraseña incorrectos."
    
    user_row = match.iloc[0].to_dict()
    
    estado = str(user_row.get("Estado", "")).strip().lower()
    fecha_vence_str = str(user_row.get("Fecha_Vence", "")).strip()
    
    if estado not in ["activo", "active"]:
        return False, f"Tu cuenta se encuentra en estado '{user_row.get('Estado')}'. Por favor contacta al administrador."
    
    if fecha_vence_str:
        try:
            if "-" in fecha_vence_str:
                parts = [int(p) for p in fecha_vence_str.split("-")]
                if parts[0] > 1000:
                    vence_date = datetime.date(parts[0], parts[1], parts[2])
                else:
                    vence_date = datetime.date(parts[2], parts[1], parts[0])
            elif "/" in fecha_vence_str:
                parts = [int(p) for p in fecha_vence_str.split("/")]
                if parts[0] > 1000:
                    vence_date = datetime.date(parts[0], parts[1], parts[2])
                else:
                    vence_date = datetime.date(parts[2], parts[1], parts[0])
            else:
                vence_date = None
            
            if vence_date and datetime.date.today() > vence_date:
                return False, f"Tu suscripción venció el {vence_date.strftime('%d/%m/%Y')}. Realiza tu renovación para continuar."
        except Exception:
            pass

    return True, user_row

# ==============================================================================
# 5. PANTALLA DE ACCESO (LOGIN)
# ==============================================================================
if not st.session_state.authenticated:
    col_l1, col_center, col_l2 = st.columns([1, 2, 1])
    with col_center:
        st.markdown("<h2 class='main-header' style='text-align: center;'>⚖️️ Portal de Jurisprudencia</h2>", unsafe_allow_html=True)
        st.markdown("<p class='sub-header' style='text-align: center;'>Acceso exclusivo para suscriptores de la Biblioteca Jurídica</p>", unsafe_allow_html=True)
        
        with st.form("form_login"):
            st.subheader("Iniciar Sesión")
            email = st.text_input("Correo electrónico", placeholder="ejemplo@correo.com")
            password = st.text_input("Contraseña / PIN de acceso", type="password")
            submit = st.form_submit_button("Ingresar al Portal", use_container_width=True)
            
            if submit:
                ok, res = check_login(email, password)
                if ok:
                    st.session_state.authenticated = True
                    st.session_state.user_info = res
                    st.rerun()
                else:
                    st.error(res)
        
        st.markdown("---")
        with st.expander("¿Aún no tienes una suscripción activa o deseas renovar?"):
            st.markdown("""
            **Planes y Membresías de la Biblioteca:**
            * 📘 **Acceso Completo:** Consulta ilimitada al catálogo oficial de providencias en PDF.
            * 🤖 **Buscador Semántico con IA:** Preguntas jurídicas en lenguaje natural con citas directas.
            * 🔔 **Actualizaciones Jurisprudenciales:** Nuevos fallos clasificados periódicamente.
            
            **Medios de Pago Disponibles (Colombia):**
            * **Nequi / Daviplata:** 300 000 0000
            * **Transferencia Bancaria:** Bancolombia / PSE
            
            *Una vez realizado el pago, envía tu comprobante para activar tu acceso de inmediato.*
            """)
            st.link_button("💬 Solicitar suscripción por WhatsApp", "https://wa.me/573000000000?text=Hola,%20deseo%20activar%20mi%20suscripci%C3%B3n%20al%20Portal%20de%20Jurisprudencia", use_container_width=True)
    st.stop()

# ==============================================================================
# 6. ENTORNO AUTENTICADO: BARRA LATERAL Y NAVEGACIÓN
# ==============================================================================
user = st.session_state.user_info
with st.sidebar:
    st.markdown("### 🏛️ **Canal de Jurisprudencia**")
    st.markdown(f"**Usuario:** {user.get('Nombre_Completo', 'Suscriptor')}")
    st.markdown(f"**Plan:** `{user.get('Plan', 'Activo')}`")
    st.markdown(f"**Vence:** `{user.get('Fecha_Vence', 'Vigente')}`")
    
    if st.button("Cerrar Sesión", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.user_info = None
        st.rerun()
        
    st.markdown("---")
    menu = st.radio(
        "Navegación",
        ["🤖 Buscador Semántico IA", "📚 Catálogo de Providencias", "👤 Mi Suscripción"],
        index=0
    )
    
    st.markdown("---")
    st.caption("Biblioteca Jurídica Digital · Google Workspace")

# ==============================================================================
# 7. MÓDULO 1: BUSCADOR SEMÁNTICO CON IA (GEMINI MULTI-MODEL FALLBACK)
# ==============================================================================
if menu == "🤖 Buscador Semántico IA":
    st.markdown("<h2 class='main-header'>🤖 Asistente Jurisprudencial con IA</h2>", unsafe_allow_html=True)
    st.markdown("<p class='sub-header'>Formula consultas jurídicas en lenguaje natural. La IA analizará la biblioteca y citará las sentencias exactas.</p>", unsafe_allow_html=True)
    
    col_input, col_config = st.columns([3, 1])
    with col_input:
        consulta_usuario = st.text_area(
            "¿Qué problema jurídico, regla o tesis deseas consultar?",
            placeholder="Ejemplo: ¿Cuál es el criterio frente a la sanción disciplinaria cuando las labores no están explícitas en el manual de funciones pero tienen conexidad con el cargo?",
            height=110
        )
    with col_config:
        modelo_preferido = st.selectbox(
            "Modelo Gemini preferido",
            ["Auto (Fallback dinámico)"] + GEMINI_MODELS_FALLBACK,
            help="Si el modelo seleccionado falla o agota cuota, el sistema probará automáticamente con las opciones alternativas."
        )
    
    col_btn, col_info = st.columns([1, 4])
    with col_btn:
        ejecutar_ia = st.button("Buscar con IA", type="primary", use_container_width=True)
    with col_info:
        st.caption("El análisis evalúa corporación, radicado, fecha, tema y la argumentación registrada en la biblioteca.")

    if ejecutar_ia and consulta_usuario.strip():
        with st.spinner("Analizando jurisprudencia y construyendo respuesta fundamentada..."):
            # 1. Preparar el contexto de la base de datos para la IA
            contexto_items = []
            cols_requeridas = ["Corporación", "Sala/Sección", "Tipo providencia", "Radicado", "Fecha providencia", "Tema", "Enlace", "Nombre copia"]
            cols_disp = [c for c in cols_requeridas if c in df_juris.columns]
            
            for idx, row in df_juris.iterrows():
                corp = row.get("Corporación", "")
                rad = row.get("Radicado", "")
                fecha = row.get("Fecha providencia", "")
                tema = row.get("Tema", "")
                link = row.get("Enlace", "")
                nombre = row.get("Nombre copia", row.get("Nombre", ""))
                
                if tema or rad:
                    contexto_items.append(f"• [{corp}] Radicado: {rad} | Fecha: {fecha} | Tema: {tema} | Documento: {nombre} | Link: {link}")
            
            contexto_texto = "\n".join(contexto_items[:120])  # Primeras 120 providencias más relevantes
            
            prompt = f"""
Eres un asistente jurídico experto en derecho público, disciplinario y contencioso administrativo en Colombia.
Analiza la siguiente pregunta del usuario y responde FUNDAMENTÁNDOTE ESTRICTAMENTE en la base de datos de providencias suministrada.

Pregunta del usuario:
"{consulta_usuario}"

Base de Providencias y Doctrina Disponible:
{contexto_texto}

Instrucciones para tu respuesta:
1. SÍNTESIS JURÍDICA: Explica con claridad técnica y rigor la tesis jurídica aplicable a la consulta.
2. PROVIDENCIAS FUNDAMENTO: Cita de forma expresa las providencias de la lista que respaldan tu respuesta (menciona Corporación, Radicado, Fecha y Tema).
3. ENLACES DIRECTOS: Si la providencia tiene un enlace en la lista, indícalo claramente con formato markdown [Ver Providencia](enlace) para que el suscriptor pueda abrir el archivo oficial.
4. Si la base no contiene un caso idéntico, explica el precedente más cercano disponible sin inventar radicados ni normas.
"""
            respuesta_texto = ""
            modelo_usado = None
            
            if GEMINI_API_KEY:
                try:
                    import google.generativeai as genai
                    genai.configure(api_key=GEMINI_API_KEY)
                    
                    # Orden de modelos según preferencia del usuario
                    if modelo_preferido != "Auto (Fallback dinámico)":
                        modelos_a_probar = [modelo_preferido] + [m for m in GEMINI_MODELS_FALLBACK if m != modelo_preferido]
                    else:
                        modelos_a_probar = GEMINI_MODELS_FALLBACK
                    
                    errores_modelos = []
                    for name_model in modelos_a_probar:
                        try:
                            model = genai.GenerativeModel(name_model)
                            response = model.generate_content(prompt)
                            if response and response.text:
                                respuesta_texto = response.text
                                modelo_usado = name_model
                                break
                        except Exception as em:
                            errores_modelos.append(f"{name_model}: {em}")
                    
                    if not respuesta_texto:
                        respuesta_texto = f"Error al generar respuesta con los modelos disponibles de Gemini.\n\nDetalles:\n" + "\n".join(errores_modelos)
                        
                except Exception as e:
                    respuesta_texto = f"Error general al consultar la API de Gemini: {e}\n\nAsegúrate de haber configurado tu GEMINI_API_KEY en los Secrets de Streamlit."
            else:
                # Modo demostración / Fallback local por palabras clave
                respuesta_texto = f"""
### 💡 Análisis Preliminar (Modo Demostración - Sin API Key configurada)

Para activar el análisis dinámico en tiempo real con Gemini, agrega tu `GEMINI_API_KEY` gratuita en los Secrets de Streamlit.

**Coincidencias encontradas por palabras clave en tu biblioteca:**
"""
                palabras = [p.lower() for p in consulta_usuario.split() if len(p) > 3]
                matches = []
                for _, row in df_juris.iterrows():
                    score = sum(1 for p in palabras if p in str(row.get("Tema", "")).lower() or p in str(row.get("Nombre", "")).lower())
                    if score > 0:
                        matches.append((score, row))
                
                matches.sort(key=lambda x: x[0], reverse=True)
                for _, m in matches[:5]:
                    link = m.get('Enlace', '#')
                    respuesta_texto += f"\n* **{m.get('Corporación')}** - Rad. `{m.get('Radicado')}` ({m.get('Fecha providencia')}): {m.get('Tema')} — [Abrir Documento en Drive]({link})"

            # Mostrar respuesta
            st.markdown("<div class='card-ia'>", unsafe_allow_html=True)
            if modelo_usado:
                st.caption(f"⚡ *Respuesta generada mediante Gemini (`{modelo_usado}`)*")
            st.markdown(respuesta_texto)
            st.markdown("</div>", unsafe_allow_html=True)

# ==============================================================================
# 8. MÓDULO 2: CATÁLOGO DE PROVIDENCIAS Y FILTROS
# ==============================================================================
elif menu == "📚 Catálogo de Providencias":
    st.markdown("<h2 class='main-header'>📚 Biblioteca de Jurisprudencia</h2>", unsafe_allow_html=True)
    st.markdown("<p class='sub-header'>Explora y filtra las sentencias, autos y conceptos oficiales clasificados.</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    # Filtro Corporación
    corps = ["Todas"] + sorted([c for c in df_juris["Corporación"].unique() if c])
    with col1:
        filtro_corp = st.selectbox("Corporación", corps)
        
    # Filtro Tipo Providencia
    tipos = ["Todos"]
    if "Tipo providencia" in df_juris.columns:
        tipos += sorted([t for t in df_juris["Tipo providencia"].unique() if t])
    with col2:
        filtro_tipo = st.selectbox("Tipo de Providencia", tipos)
        
    # Filtro de búsqueda por texto
    with col3:
        filtro_texto = st.text_input("Buscar por tema, radicado o palabra", placeholder="Ej: debido proceso, sanción...")
        
    # Aplicar filtros
    df_filtrado = df_juris.copy()
    if filtro_corp != "Todas":
        df_filtrado = df_filtrado[df_filtrado["Corporación"] == filtro_corp]
    if filtro_tipo != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Tipo providencia"] == filtro_tipo]
    if filtro_texto.strip():
        txt = filtro_texto.strip().lower()
        mascara = (
            df_filtrado["Tema"].astype(str).str.lower().str.contains(txt) |
            df_filtrado["Radicado"].astype(str).str.lower().str.contains(txt) |
            df_filtrado["Nombre"].astype(str).str.lower().str.contains(txt)
        )
        df_filtrado = df_filtrado[mascara]

    st.markdown(f"**Resultados encontrados:** `{len(df_filtrado)}` providencias")
    
    # Visualización en formato tarjetas
    for idx, row in df_filtrado.iterrows():
        corp = row.get("Corporación", "General")
        sala = row.get("Sala/Sección", "")
        tipo = row.get("Tipo providencia", "Providencia")
        rad = row.get("Radicado", "S/R")
        fecha = row.get("Fecha providencia", "S/F")
        tema = row.get("Tema", "Sin tema registrado")
        enlace = row.get("Enlace", "")
        nombre_copia = row.get("Nombre copia", row.get("Nombre", ""))
        
        with st.container():
            st.markdown(f"""
            <div class='card-providencia'>
                <div>
                    <span class='tag-corp'>{corp}</span>
                    <span class='tag-fecha'>📅 {fecha}</span>
                    <span style='color: #718096; font-size: 0.85rem; margin-left: 8px;'>{tipo} · {sala}</span>
                </div>
                <h4 style='color: #1A202C; margin-top: 8px; margin-bottom: 6px;'>Radicado: {rad}</h4>
                <p style='color: #2D3748; font-size: 0.95rem; margin-bottom: 8px;'><strong>Tema:</strong> {tema}</p>
                <div style='font-size: 0.82rem; color: #718096;'>
                    <strong>Archivo:</strong> {nombre_copia}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if enlace:
                st.link_button(f"📄 Abrir PDF en Google Drive ({rad})", enlace)
            st.write("")

# ==============================================================================
# 9. MÓDULO 3: MI SUSCRIPCIÓN
# ==============================================================================
elif menu == "👤 Mi Suscripción":
    st.markdown("<h2 class='main-header'>👤 Estado de tu Suscripción</h2>", unsafe_allow_html=True)
    st.markdown("<p class='sub-header'>Información de tu membresía y opciones de renovación.</p>", unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        st.info(f"""
        **Datos del Suscriptor:**
        * **Nombre:** {user.get('Nombre_Completo')}
        * **Correo registrado:** {user.get('Email')}
        * **Plan contratado:** {user.get('Plan')}
        * **Fecha de inicio:** {user.get('Fecha_Inicio')}
        * **Vigencia hasta:** {user.get('Fecha_Vence')}
        * **Estado de la cuenta:** `{user.get('Estado')}`
        """)
    with c2:
        st.success("""
        **Beneficios activos de tu plan:**
        * ✔️ Consultas semánticas con Inteligencia Artificial.
        * ✔️ Acceso directo a los PDFs en alta calidad.
        * ✔️ Descargas de resoluciones y conceptos oficiales.
        * ✔️ Soporte técnico y jurisprudencial prioritario.
        """)
        
    st.markdown("---")
    st.markdown("### ¿Deseas renovar o ampliar tu periodo de suscripción?")
    st.markdown("""
    Ponte en contacto directo con nuestro canal para procesar tu renovación y mantener tu acceso sin interrupciones.
    """)
    st.link_button("📲 Contactar soporte de suscripciones por WhatsApp", "https://wa.me/573000000000?text=Hola,%20deseo%20renovar%20mi%20suscripci%C3%B3n", use_container_width=True)
