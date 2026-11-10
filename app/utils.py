import cv2
import mediapipe as mp
import numpy as np

def obtener_estilos_dibujo():
    # estilo visual del esqueleto para superponer a la camara
    mp_drawing = mp.solutions.drawing_utils
    
    spec_puntos = mp_drawing.DrawingSpec(
        color=(245, 245, 250),
        thickness=-1,
        circle_radius=3
    )
    
    spec_conexiones = mp_drawing.DrawingSpec(
        color=(25, 25, 220),
        thickness=2,
        circle_radius=1
    )
    
    return spec_puntos, spec_conexiones


def calcular_angulo(a, b, c):
    # angulo entre tres puntos 2D con vertice en b
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)

    radianes = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    angulo = np.abs(radianes * 180.0 / np.pi)

    if angulo > 180.0:
        angulo = 360.0 - angulo

    return float(angulo)


# ---------------------------------------------------------------------------
# telemetria en vivo: el callback de video (hilo de webrtc) escribe aqui y la
# interfaz (hilo del script) lee una instantanea cada pocos milisegundos
# ---------------------------------------------------------------------------
import threading
import time
from collections import deque

# indices de mediapipe pose: hombro, codo y muneca de cada lado
BRAZO_DERECHO = (12, 14, 16)
BRAZO_IZQUIERDO = (11, 13, 15)
UMBRAL_FLEXION = 70.0
UMBRAL_EXTENSION = 150.0


class TelemetriaEnVivo:
    def __init__(self):
        self.lock = threading.Lock()
        self.reiniciar()

    def reiniciar(self):
        self.angulo = None
        self.rom_min = None
        self.rom_max = None
        self.reps = 0
        self.fase = "extension"
        self.lado = "-"
        self.latencia_ms = 0.0
        self.fps = 0.0
        self.resolucion = "-"
        self.visibles = 0
        self.vectores = {}
        self.pose = False
        self.frames = 0
        self.t_ultimo = 0.0
        self.t_fps = time.time()
        self.n_fps = 0
        self.log = deque(maxlen=30)

    def _anotar(self, texto):
        self.log.append(time.strftime("%H:%M:%S") + "  " + texto)

    def registrar(self, landmarks, ancho, alto, latencia_ms):
        ahora = time.time()
        with self.lock:
            # un hueco largo entre frames indica una sesion nueva
            if self.t_ultimo and ahora - self.t_ultimo > 3.0:
                self.reiniciar()
            if not self.frames:
                self._anotar("stream iniciado")
            self.t_ultimo = ahora
            self.frames += 1
            self.latencia_ms = latencia_ms
            self.resolucion = f"{ancho}x{alto}"

            self.n_fps += 1
            if ahora - self.t_fps >= 1.0:
                self.fps = self.n_fps / (ahora - self.t_fps)
                self.n_fps = 0
                self.t_fps = ahora

            if landmarks is None:
                if self.pose:
                    self._anotar("pose perdida")
                self.pose = False
                self.visibles = 0
                return

            if not self.pose:
                self._anotar("pose detectada")
            self.pose = True
            lm = landmarks.landmark
            self.visibles = sum(1 for p in lm if p.visibility > 0.5)

            # usamos el brazo mas visible
            def vis(ids):
                return sum(lm[i].visibility for i in ids)

            ids, lado = (
                (BRAZO_DERECHO, "derecho")
                if vis(BRAZO_DERECHO) >= vis(BRAZO_IZQUIERDO)
                else (BRAZO_IZQUIERDO, "izquierdo")
            )
            if lado != self.lado:
                self._anotar("brazo " + lado)
            self.lado = lado

            hombro, codo, muneca = (lm[i] for i in ids)
            self.vectores = {
                "hombro": (hombro.x, hombro.y, hombro.visibility),
                "codo": (codo.x, codo.y, codo.visibility),
                "muneca": (muneca.x, muneca.y, muneca.visibility),
            }
            angulo = calcular_angulo(
                (hombro.x, hombro.y), (codo.x, codo.y), (muneca.x, muneca.y)
            )
            self.angulo = angulo
            self.rom_min = angulo if self.rom_min is None else min(self.rom_min, angulo)
            self.rom_max = angulo if self.rom_max is None else max(self.rom_max, angulo)

            # contador de repeticiones con histeresis flexion -> extension
            if angulo < UMBRAL_FLEXION and self.fase == "extension":
                self.fase = "flexion"
                self._anotar(f"flexion {angulo:.0f} grados")
            elif angulo > UMBRAL_EXTENSION and self.fase == "flexion":
                self.fase = "extension"
                self.reps += 1
                self._anotar(f"repeticion {self.reps}")

    def instantanea(self):
        with self.lock:
            rom = (
                None
                if self.rom_min is None
                else round(self.rom_max - self.rom_min)
            )
            return {
                "live": True,
                "pose": self.pose,
                "angulo": None if self.angulo is None else round(self.angulo),
                "rom": rom,
                "reps": self.reps,
                "fase": self.fase,
                "lado": self.lado,
                "fps": round(self.fps, 1),
                "lat": round(self.latencia_ms, 1),
                "res": self.resolucion,
                "vis": self.visibles,
                "vec": {
                    k: [round(v[0], 2), round(v[1], 2), round(v[2], 2)]
                    for k, v in self.vectores.items()
                },
                "log": list(self.log)[-7:],
            }


telemetria = TelemetriaEnVivo()
