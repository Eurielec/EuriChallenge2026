import os
import sys
import streamlit as st
import cv2
import mediapipe as mp
import av
from streamlit_webrtc import webrtc_streamer, WebRtcMode

# Anadir el directorio actual al path para importar utilidades
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils import obtener_estilos_dibujo

# Configuracion de pagina
st.set_page_config(
    page_title="EuriChallenge - Monitor de Rehabilitacion",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Control de estado: El tutorial solo se muestra la primera vez que se abre la app
if "mostrar_tutorial" not in st.session_state:
    st.session_state.mostrar_tutorial = True

# Inyeccion de estilos CSS: Estetica Roja y Negra, Helvetica, Lineas Finas y Estilo Burbuja
st.markdown("""
<style>
    /* Tipografia global Helvetica */
    * {
        font-family: "Helvetica Neue", Helvetica, Arial, sans-serif !important;
    }

    /* Fondo principal y estructura */
    .stApp {
        background-color: #09090b !important;
        color: #f4f4f5 !important;
    }

    /* Ocultar elementos genericos de cabecera de Streamlit */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { background-color: transparent !important; }

    /* Barra lateral */
    section[data-testid="stSidebar"] {
        background-color: #0d0d11 !important;
        border-right: 1px solid rgba(239, 68, 68, 0.18) !important;
    }
    section[data-testid="stSidebar"] > div {
        padding-top: 1.5rem;
    }

    /* Contenedores estilo burbuja */
    .bubble-card {
        background: #141418;
        border: 1px solid rgba(239, 68, 68, 0.22);
        border-radius: 20px;
        padding: 18px 22px;
        margin-bottom: 16px;
        box-shadow: 0 8px 24px -6px rgba(0, 0, 0, 0.6);
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }
    .bubble-card:hover {
        border-color: rgba(239, 68, 68, 0.45);
        box-shadow: 0 10px 28px -4px rgba(220, 38, 38, 0.18);
    }

    /* Tarjetas de metrica / pildoras */
    .pill-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(220, 38, 38, 0.1);
        border: 1px solid rgba(239, 68, 68, 0.35);
        border-radius: 9999px;
        padding: 5px 14px;
        font-size: 0.76rem;
        font-weight: 600;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        color: #fca5a5;
        margin-bottom: 12px;
    }

    .pill-indicator {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background-color: #ef4444;
        box-shadow: 0 0 8px #ef4444;
        display: inline-block;
    }

    /* Titulos y textos */
    h1.app-title {
        font-size: 2.2rem;
        font-weight: 700;
        letter-spacing: -0.03em;
        color: #ffffff;
        margin: 0 0 4px 0;
        padding: 0;
    }
    p.app-subtitle {
        font-size: 0.95rem;
        color: #a1a1aa;
        margin: 0 0 20px 0;
        letter-spacing: -0.01em;
    }

    .sidebar-section-title {
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: #ef4444;
        margin-bottom: 10px;
        padding-bottom: 6px;
        border-bottom: 1px solid rgba(239, 68, 68, 0.2);
    }

    .sidebar-item-label {
        font-size: 0.78rem;
        color: #71717a;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 2px;
    }
    .sidebar-item-val {
        font-size: 1.05rem;
        font-weight: 600;
        color: #f4f4f5;
        margin-bottom: 12px;
    }

    /* Banner informativo estilo burbuja */
    .bubble-notice {
        background: rgba(220, 38, 38, 0.08);
        border: 1px solid rgba(239, 68, 68, 0.3);
        border-radius: 9999px;
        padding: 10px 20px;
        font-size: 0.88rem;
        color: #f4f4f5;
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 20px;
    }

    /* Marco de la camara en estilo burbuja */
    div[data-testid="stWebRtcStreamer"] {
        background: #000000;
        border: 1px solid rgba(239, 68, 68, 0.28);
        border-radius: 24px;
        padding: 12px;
        box-shadow: 0 14px 35px -8px rgba(0, 0, 0, 0.85);
    }

    /* Estilos para botones de Streamlit y WebRTC (estilo pildora / burbuja) */
    button, div.stButton > button {
        border-radius: 9999px !important;
        border: 1px solid rgba(239, 68, 68, 0.38) !important;
        background: #18181d !important;
        color: #f4f4f5 !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        padding: 0.5rem 1.6rem !important;
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }
    button:hover, div.stButton > button:hover {
        background: #dc2626 !important;
        border-color: #ef4444 !important;
        color: #ffffff !important;
        box-shadow: 0 0 16px rgba(220, 38, 38, 0.45) !important;
        transform: translateY(-1px);
    }

    /* Contenedor del Tutorial Minimalista */
    .tutorial-container {
        background: #111116;
        border: 1px solid rgba(239, 68, 68, 0.35);
        border-radius: 24px;
        padding: 24px 28px;
        margin-bottom: 24px;
        box-shadow: 0 12px 36px -8px rgba(0, 0, 0, 0.8), 0 0 18px rgba(220, 38, 38, 0.1);
    }

    .tutorial-top {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
        padding-bottom: 12px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    }

    .tutorial-header-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: #ffffff;
        letter-spacing: -0.02em;
    }

    .tutorial-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: 16px;
        margin-bottom: 18px;
    }

    .tutorial-bubble {
        background: #16161c;
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 18px;
        padding: 16px 18px;
    }

    .tutorial-bubble-tag {
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #ef4444;
        margin-bottom: 6px;
    }

    .tutorial-bubble-title {
        font-size: 0.95rem;
        font-weight: 600;
        color: #ffffff;
        margin-bottom: 8px;
    }

    .tutorial-bubble-desc {
        font-size: 0.82rem;
        color: #a1a1aa;
        line-height: 1.5;
        margin: 0;
    }

    .schema-diagram {
        background: #09090d;
        border: 1px solid rgba(239, 68, 68, 0.2);
        border-radius: 14px;
        padding: 14px 18px;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace !important;
        font-size: 0.8rem;
        color: #e4e4e7;
        line-height: 1.55;
        overflow-x: auto;
        margin: 12px 0 16px 0;
    }

    .flow-line {
        display: flex;
        align-items: center;
        gap: 10px;
        background: #0c0c10;
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 14px;
        padding: 10px 16px;
        font-size: 0.8rem;
        color: #d4d4d8;
        margin-bottom: 16px;
        flex-wrap: wrap;
    }

    .flow-pill {
        background: #1b1b22;
        border: 1px solid rgba(239, 68, 68, 0.3);
        border-radius: 9999px;
        padding: 4px 12px;
        font-weight: 600;
        color: #ffffff;
    }

    .flow-arrow {
        color: #ef4444;
        font-weight: 700;
    }
</style>
""", unsafe_allow_html=True)

# Inicializacion del detector de pose MediaPipe
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)

# Obtener configuracion de dibujo en paleta roja y blanca
spec_puntos, spec_conexiones = obtener_estilos_dibujo()

def procesar_frame(frame):
    """
    Procesa cada fotograma recibido por la camara web,
    aplica la estimacion de pose y superpone el trazado.
    """
    img = frame.to_ndarray(format="bgr24")
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = pose.process(img_rgb)

    if results.pose_landmarks:
        mp_drawing.draw_landmarks(
            img,
            results.pose_landmarks,
            mp_pose.POSE_CONNECTIONS,
            spec_puntos,
            spec_conexiones
        )

    return av.VideoFrame.from_ndarray(img, format="bgr24")

# Barra lateral: Panel de control con estructura de burbujas
with st.sidebar:
    st.markdown('<div class="sidebar-section-title">Panel de Control</div>', unsafe_allow_html=True)
    
    # Boton para volver a abrir el tutorial si se ha cerrado
    if not st.session_state.mostrar_tutorial:
        if st.button("Ver guia de desarrollo", key="btn_abrir_tuto"):
            st.session_state.mostrar_tutorial = True
            st.rerun()

    st.markdown("""
    <div class="bubble-card">
        <div class="sidebar-item-label">Paciente</div>
        <div class="sidebar-item-val">Demo</div>
        <div class="sidebar-item-label">ID de Sesion</div>
        <div class="sidebar-item-val">REHAB-2026-01</div>
        <div class="sidebar-item-label">Estado</div>
        <div class="sidebar-item-val" style="color: #4ade80;">Conectado</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="bubble-card">
        <div class="sidebar-item-label">Ejercicio Seleccionado</div>
        <div class="sidebar-item-val">Elevacion de brazo</div>
        <div class="sidebar-item-label">Articulaciones Objetivo</div>
        <div class="sidebar-item-val">Hombro / Codo</div>
        <div class="sidebar-item-label">Meta</div>
        <div class="sidebar-item-val">10 repeticiones</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="bubble-card">
        <div class="sidebar-item-label">Modo de Video</div>
        <div class="sidebar-item-val">WebRTC SENDRECV</div>
        <div class="sidebar-item-label">Trazado</div>
        <div class="sidebar-item-val">MediaPipe Pose (33 pts)</div>
    </div>
    """, unsafe_allow_html=True)

# Area principal
st.markdown('<div class="pill-badge"><span class="pill-indicator"></span> SISTEMA DE MONITORIZACION BIOMEDICA</div>', unsafe_allow_html=True)
st.markdown('<h1 class="app-title">Monitor de Rehabilitacion</h1>', unsafe_allow_html=True)
st.markdown('<p class="app-subtitle">Reto de Ingenieria Biomedica | EESTEC LC Madrid & Eurielec</p>', unsafe_allow_html=True)

# Tutorial minimalista (se muestra unicamente en la primera ejecucion o al solicitarlo)
if st.session_state.mostrar_tutorial:
    st.markdown("""
    <div class="tutorial-container">
        <div class="tutorial-top">
            <div>
                <span class="pill-badge" style="margin-bottom: 4px;">GUIA DE ARQUITECTURA</span>
                <div class="tutorial-header-title">Estructura de Trabajo y Desarrollo</div>
            </div>
        </div>
        
        <div class="flow-line">
            <span class="flow-pill">Editor Local (IDE)</span>
            <span class="flow-arrow">&rarr;</span>
            <span class="flow-pill">Volumen en Vivo (./app)</span>
            <span class="flow-arrow">&rarr;</span>
            <span class="flow-pill">Contenedor Docker (Streamlit :8501)</span>
            <span class="flow-arrow">&rarr;</span>
            <span class="flow-pill">Navegador WebRTC</span>
        </div>

        <div class="tutorial-grid">
            <div class="tutorial-bubble">
                <div class="tutorial-bubble-tag">01. Entorno de Edicion</div>
                <div class="tutorial-bubble-title">Donde Desarrollar</div>
                <p class="tutorial-bubble-desc">
                    Desarrolla en tu editor preferido (VS Code, Cursor, etc.) sobre los archivos locales.
                    El volumen montado replica cambios instantaneamente en el contenedor sin reiniciar Docker.
                </p>
            </div>
            <div class="tutorial-bubble">
                <div class="tutorial-bubble-tag">02. Stack Tecnologico</div>
                <div class="tutorial-bubble-title">Lenguajes y Librerias</div>
                <p class="tutorial-bubble-desc">
                    <strong>Python 3.11</strong> como lenguaje principal.<br>
                    Modulos core: <code>mediapipe</code> (pose 33 landmarks), <code>opencv-python</code> (matrices de imagen),
                    <code>numpy</code> (calculo articular) y <code>streamlit</code>.
                </p>
            </div>
            <div class="tutorial-bubble">
                <div class="tutorial-bubble-tag">03. Estado del Desafio</div>
                <div class="tutorial-bubble-title">Funcionamiento del Reto</div>
                <p class="tutorial-bubble-desc">
                    El modulo actual provee la infraestructura base y captura en tiempo real.<br>
                    La especificacion clinica y los ejercicios biomédicos se añadiran en la siguiente etapa.
                </p>
            </div>
        </div>

        <div style="font-size: 0.78rem; font-weight: 700; color: #ef4444; letter-spacing: 0.05em; text-transform: uppercase; margin-bottom: 6px;">
            Esquema del Sistema de Archivos
        </div>
        <div class="schema-diagram">
EURICHALLENGE/
├── app/
│   ├── app.py          <- Interfaz grafica, dashboard y flujo de video WebRTC
│   └── utils.py        <- Modulo de calculo cinematico, angulos y estilos
├── Dockerfile          <- Definicion de entorno y librerias del sistema
├── docker-compose.yml  <- Mapeo de puerto 8501 y montaje en vivo ./app:/app
└── requirements.txt    <- Dependencias oficiales del proyecto
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col_btn, col_rest = st.columns([1, 4])
    with col_btn:
        if st.button("Cerrar guia e ir al monitor", key="btn_cerrar_tuto"):
            st.session_state.mostrar_tutorial = False
            st.rerun()

# Banner de instrucciones estilo burbuja
st.markdown("""
<div class="bubble-notice">
    <span class="pill-indicator"></span>
    <span>Pulsa <strong>START</strong> y permite el acceso a la camara en el navegador para iniciar la monitorizacion en tiempo real.</span>
</div>
""", unsafe_allow_html=True)

# Modulo de video WebRTC
webrtc_streamer(
    key="rehab-cam",
    mode=WebRtcMode.SENDRECV,
    video_frame_callback=procesar_frame,
    rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
)