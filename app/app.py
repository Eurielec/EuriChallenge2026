import os
import sys
import json
import time
import html
import base64
import hashlib
import threading
import streamlit as st
import streamlit.components.v1 as components
import mediapipe as mp
import av
from streamlit_webrtc import webrtc_streamer, WebRtcMode

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils import obtener_estilos_dibujo
from rehab_engine import RehabEngine

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

st.set_page_config(
    page_title="EuriChallenge · Rehab Monitor",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def leer(nombre):
    with open(os.path.join(ASSETS_DIR, nombre), encoding="utf-8") as f:
        return f.read()


@st.cache_data
def logo_b64(nombre):
    with open(os.path.join(ASSETS_DIR, nombre), "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


EURIELEC = logo_b64("eurielec.png")
ELGATO = logo_b64("elgato.png")

# ruido para el grano del loader
GRAIN = (
    "data:image/svg+xml;utf8,"
    "<svg xmlns='http://www.w3.org/2000/svg' width='220' height='220'>"
    "<filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='3' stitchTiles='stitch'/>"
    "<feColorMatrix values='0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 0.55 0'/></filter>"
    "<rect width='100%25' height='100%25' filter='url(%23n)'/></svg>"
)

estilos = leer("estilos.css").replace("__GRAIN__", GRAIN)
html_intro = leer("intro.html").replace("__EURIELEC__", EURIELEC).replace("__ELGATO__", ELGATO)
frag = leer("fondo.glsl")
js_sonido = leer("sonido.js")
version = hashlib.md5((estilos + html_intro + frag + leer("intro.js")).encode()).hexdigest()[:10]
js_intro = (
    leer("intro.js")
    .replace("__HTML__", json.dumps(html_intro))
    .replace("__FRAG__", json.dumps(frag))
    .replace("__VER__", version)
)

st.markdown(f"<style>{estilos}</style>", unsafe_allow_html=True)

st.markdown(
    f"""<div class="loader" aria-hidden="true">
<div class="loader-red"></div>
<div class="loader-logos">
<div class="logo eurielec"><img class="ghost" src="{EURIELEC}" alt=""><img class="sharp" src="{EURIELEC}" alt=""></div>
<div class="logo elgato"><img class="ghost" src="{ELGATO}" alt=""><img class="sharp" src="{ELGATO}" alt=""></div>
</div>
</div>""",
    unsafe_allow_html=True,
)

components.html(f"<script>{js_sonido}</script><script>{js_intro}</script>", height=0)

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
spec_puntos, spec_conexiones = obtener_estilos_dibujo()

if not isinstance(st.session_state.get("rehab_motor"), RehabEngine):
    st.session_state["rehab_motor"] = RehabEngine()
    st.session_state["rehab_tiempo"] = {
        "lock": threading.Lock(),
        "ultimo_reloj": None,
        "ultimo_frame_s": None,
        "acumulado_ms": 0.0,
    }

motor = st.session_state["rehab_motor"]
tiempo_ctx = st.session_state["rehab_tiempo"]


def _timestamp_ms(frame):
    ahora = time.monotonic()
    frame_s = frame.time
    with tiempo_ctx["lock"]:
        reloj_prev = tiempo_ctx["ultimo_reloj"]
        frame_prev = tiempo_ctx["ultimo_frame_s"]

        nueva_sesion = reloj_prev is None or (ahora - reloj_prev > 2.5)
        if not nueva_sesion and frame_s is not None and frame_prev is not None:
            if abs((frame_s - frame_prev) - (ahora - reloj_prev)) > 2.0:
                nueva_sesion = True

        if nueva_sesion:
            motor.reiniciar()
            tiempo_ctx["acumulado_ms"] = 0.0
        else:
            dt_s = (
                (frame_s - frame_prev)
                if (frame_s is not None and frame_prev is not None)
                else (ahora - reloj_prev)
            )
            tiempo_ctx["acumulado_ms"] += max(0.0, dt_s) * 1000.0

        tiempo_ctx["ultimo_reloj"] = ahora
        tiempo_ctx["ultimo_frame_s"] = frame_s
        return tiempo_ctx["acumulado_ms"]


def procesar_frame(frame):
    img = frame.to_ndarray(format="bgr24")
    t_ms = _timestamp_ms(frame)
    landmarks = motor.procesar_fotograma(img, t_ms)
    if landmarks:
        mp_drawing.draw_landmarks(
            img,
            landmarks,
            mp_pose.POSE_CONNECTIONS,
            spec_puntos,
            spec_conexiones,
        )
    return av.VideoFrame.from_ndarray(img, format="bgr24")


st.markdown(
    f"""<div class="rv-wrap rv d1"><div class="topbar">
<img src="{EURIELEC}" alt="Eurielec">
<div class="topbar-r"><button class="link" data-act="open-tutorial">Tutorial</button><img src="{ELGATO}" alt="Elgato"></div>
</div></div>
<div class="rv-wrap rv d2"><div class="title" role="heading" aria-level="1" aria-label="Rehab Monitor"><span class="t-keep t-r">R</span><span class="t-fade t-ehab">ehab&nbsp;</span><span class="t-keep t-m">M</span><span class="t-fade t-onitor">onitor</span></div></div>
<div class="rv-wrap rv d3"><p class="sub">Reto de Ingeniería Biomédica · EESTEC LC Madrid &amp; Eurielec · ETSIT, UPM</p></div>
<div class="rv-wrap rv d4"><p class="cue"><span>Pulsa <strong>START</strong> a la derecha para iniciar la monitorización biomecánica en tiempo real.</span></p></div>""",
    unsafe_allow_html=True,
)

col_izq, col_der = st.columns([1, 4], gap="medium")
with col_izq:
    st.markdown(
        """<div class="rv-wrap panel-anchor rv d4"><aside class="panel-lateral">
  <div class="panel-lateral-head">
    <span class="panel-tag">Métricas &amp; Control</span>
    <span class="panel-status">En espera</span>
  </div>
  <div class="panel-lateral-body">
    <div class="metric-slot s1">
      <span class="slot-k">Ángulo articular</span>
      <span class="slot-v">--°</span>
    </div>
    <div class="metric-slot s2">
      <span class="slot-k">Rango ROM</span>
      <span class="slot-v">--</span>
    </div>
    <div class="metric-slot s3">
      <span class="slot-k">Repeticiones</span>
      <span class="slot-v">0</span>
    </div>
  </div>
  <div class="panel-live" aria-live="off">
    <div class="live-head">Telemetría en vivo</div>
    <ul class="live-vec">
      <li><span>FPS</span><b data-k="fps">--</b></li>
      <li><span>Latencia</span><b data-k="lat">--</b></li>
      <li><span>Resolución</span><b data-k="res">--</b></li>
      <li><span>Brazo</span><b data-k="lado">--</b></li>
      <li><span>Fase</span><b data-k="fase">--</b></li>
      <li><span>Puntos</span><b data-k="vis">--</b></li>
    </ul>
    <div class="live-head">Vectores x, y, vis</div>
    <ul class="live-vec">
      <li><span>hombro</span><b data-k="v-hombro">--</b></li>
      <li><span>codo</span><b data-k="v-codo">--</b></li>
      <li><span>muñeca</span><b data-k="v-muneca">--</b></li>
    </ul>
    <div class="live-head">Registro</div>
    <ol class="live-log" data-k="log"></ol>
  </div>
  <div class="panel-hint">
    Motor lógico desacoplado en rehab_engine.py (evaluación CLI vía eval.py).
  </div>
</aside></div>""",
        unsafe_allow_html=True,
    )

with col_izq:
    datos_vivo = st.empty()

with col_der:
    ctx = webrtc_streamer(
        key="rehab-cam",
        mode=WebRtcMode.SENDRECV,
        video_frame_callback=procesar_frame,
        rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
    )


def publicar(payload):
    # el panel lo lee intro.js desde este nodo oculto
    dato = html.escape(json.dumps(payload), quote=True)
    datos_vivo.markdown(
        f'<div class="eur-live" data-json="{dato}"></div>', unsafe_allow_html=True
    )


estaba_activo = st.session_state.get("camara_activa", False)
st.session_state["camara_activa"] = ctx.state.playing
if not ctx.state.playing and estaba_activo:
    motor.reiniciar()
    with tiempo_ctx["lock"]:
        tiempo_ctx["ultimo_reloj"] = None
        tiempo_ctx["ultimo_frame_s"] = None
        tiempo_ctx["acumulado_ms"] = 0.0

# bucle de telemetria: mientras la camara este encendida empujamos datos al panel
while ctx.state.playing:
    publicar(motor.instantanea())
    time.sleep(0.3)
publicar({"live": False})
