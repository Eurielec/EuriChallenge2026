import streamlit as st
import cv2
import mediapipe as mp
import av
from streamlit_webrtc import webrtc_streamer, WebRtcMode

# Configuración de la página web
st.set_page_config(page_title="EURI-CHALLENGE Rehab", layout="wide")

st.title("🦾 Monitor de Rehabilitación")
st.markdown("Hackathon EESTEC LC Madrid - **Reto de Ingeniería Biomédica**")

# Inicializar la Inteligencia Artificial
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)

# Esta función se ejecuta por cada fotograma (foto) que envía la cámara web
def procesar_frame(frame):
    # Extraer la foto de la cámara web
    img = frame.to_ndarray(format="bgr24")

    # Convertir color y pasar a MediaPipe
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = pose.process(img_rgb)

    # Si ve a una persona, dibujar el esqueleto
    if results.pose_landmarks:
        mp_drawing.draw_landmarks(
            img,
            results.pose_landmarks,
            mp_pose.POSE_CONNECTIONS,
            mp_drawing.DrawingSpec(color=(245, 117, 66), thickness=2, circle_radius=2),
            mp_drawing.DrawingSpec(color=(245, 66, 230), thickness=2, circle_radius=2)
        )

    # Devolver la foto pintada a la página web
    return av.VideoFrame.from_ndarray(img, format="bgr24")

# Panel lateral para que los estudiantes metan sus datos
with st.sidebar:
    st.header("Panel de Control")
    st.write("Paciente: **Demo**")
    st.write("Ejercicio: **Elevación de brazo**")

# El reproductor de vídeo en la web
st.write("### Cámara en Vivo")
st.info("💡 Haz clic en 'START' y concédele permisos a tu navegador para usar la cámara.")
webrtc_streamer(
    key="rehab-cam",
    mode=WebRtcMode.SENDRECV,
    video_frame_callback=procesar_frame,
    rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
)