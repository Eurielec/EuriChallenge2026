"""Motor de rehabilitacion: logica de procesamiento sin ninguna dependencia de Streamlit.

La interfaz (app.py) y el evaluador automatico (eval.py) usan este mismo motor.
Todo el tiempo se calcula a partir de los timestamps de los fotogramas (milisegundos),
nunca contando fotogramas, de modo que el resultado no depende de los FPS del video
ni de la velocidad a la que se procese.
"""
import math
import threading
import time
from collections import deque

import cv2
import mediapipe as mp

from utils import calcular_angulo

# indices de MediaPipe Pose
OREJA_I, OREJA_D = 7, 8
HOMBRO_I, HOMBRO_D = 11, 12
CODO_I, CODO_D = 13, 14
MUNECA_I, MUNECA_D = 15, 16
CADERA_I, CADERA_D = 23, 24
RODILLA_I, RODILLA_D = 25, 26
TOBILLO_I, TOBILLO_D = 27, 28

VISIBILIDAD_MIN = 0.5

# fase 1: abduccion de hombro (angulo cadera-hombro-muneca)
ABD_ARRIBA = 80.0
ABD_ABAJO = 35.0
# fase 2: sentadilla (angulo cadera-rodilla-tobillo)
SENT_ABAJO = 110.0
SENT_ARRIBA = 160.0
# fase 3: compensacion por inclinacion lateral del tronco
INCLINACION_MAX = 15.0       # grados respecto a la vertical
INCLINACION_PERSISTE_S = 0.3  # segundos seguidos para considerarlo error
ERROR_SEPARACION_S = 1.0      # separacion minima entre errores registrados

TAU_SUAVIZADO_S = 0.08  # constante de tiempo del filtro exponencial


class RehabEngine:
    def __init__(self):
        self.pose = mp.solutions.pose.Pose(
            static_image_mode=False,
            model_complexity=1,  # modelo incluido en el paquete: funciona sin conexion
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        # la interfaz lee el estado desde otro hilo mientras el callback de video lo escribe
        self.lock = threading.RLock()
        self.reiniciar()

    def reiniciar(self):
        with self.lock:
            self.t_prev = None
            self.fps = 0.0
            self.latencia_ms = 0.0
            self.resolucion = "-"
            self.pose_detectada = False
            self.visibles = 0
            self.lado = "-"
            self.vectores = {}
            self.rom_min = None
            self.rom_max = None
            self.log = deque(maxlen=30)
            self.abd = None
            self.sent = None
            self.abd_arriba = False
            self.sent_abajo = False
            self.repeticiones_abduccion = 0
            self.repeticiones_sentadilla = 0
            self.inclinado_desde = None
            self.error_activo = False
            self.timestamps_errores = []

    # ---------------------------------------------------------------- entrada
    def procesar_fotograma(self, frame_bgr, t_ms):
        """Detecta la pose en un fotograma BGR y actualiza el estado con su timestamp (ms).

        Devuelve los landmarks de MediaPipe (o None) para que la interfaz pueda dibujarlos.
        """
        inicio = time.perf_counter()
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        res = self.pose.process(rgb)
        lm = res.pose_landmarks.landmark if res.pose_landmarks else None
        with self.lock:
            alto, ancho = frame_bgr.shape[:2]
            self.actualizar(lm, t_ms)
            self.resolucion = f"{ancho}x{alto}"
            self.latencia_ms = (time.perf_counter() - inicio) * 1000.0
        return res.pose_landmarks

    def actualizar(self, lm, t_ms):
        """Actualiza la logica con una lista de 33 landmarks (o None) y el tiempo en ms."""
        with self.lock:
            t = t_ms / 1000.0
            if self.t_prev is None:
                self._anotar(t, "stream iniciado")
                dt = 0.0
            else:
                dt = max(0.0, t - self.t_prev)
            self.t_prev = t
            if dt > 0:
                self.fps = self._suavizar(self.fps or None, 1.0 / dt, dt)

            if lm is None:
                if self.pose_detectada:
                    self._anotar(t, "pose perdida")
                self.pose_detectada = False
                self.visibles = 0
                self.inclinado_desde = None
                return
            if not self.pose_detectada:
                self._anotar(t, "pose detectada")
            self.pose_detectada = True
            self.visibles = sum(1 for p in lm if p.visibility > VISIBILIDAD_MIN)

            self._fase_1(lm, dt, t)
            self._fase_2(lm, dt, t)
            self._fase_3(lm, t)

    def _anotar(self, t, texto):
        self.log.append(f"{t:6.1f}s  {texto}")

    # ---------------------------------------------------------------- utilidades
    @staticmethod
    def _p(lm, i):
        return (lm[i].x, lm[i].y)

    @staticmethod
    def _visibles(lm, ids):
        return all(lm[i].visibility >= VISIBILIDAD_MIN for i in ids)

    @staticmethod
    def _suavizar(previo, nuevo, dt):
        if previo is None:
            return nuevo
        alfa = 1.0 - math.exp(-dt / TAU_SUAVIZADO_S) if dt > 0 else 0.0
        return previo + alfa * (nuevo - previo)

    # ---------------------------------------------------------------- fases
    def _fase_1(self, lm, dt, t):
        # abduccion: el brazo que mas se separa del tronco
        candidatos = []
        for lado, (cadera, hombro, codo, muneca) in (
            ("izquierdo", (CADERA_I, HOMBRO_I, CODO_I, MUNECA_I)),
            ("derecho", (CADERA_D, HOMBRO_D, CODO_D, MUNECA_D)),
        ):
            if self._visibles(lm, (cadera, hombro, muneca)):
                ang = calcular_angulo(self._p(lm, cadera), self._p(lm, hombro), self._p(lm, muneca))
                candidatos.append((ang, lado, hombro, codo, muneca))
        if not candidatos:
            return
        ang, lado, hombro, codo, muneca = max(candidatos)
        self.lado = lado
        self.vectores = {
            nombre: (lm[i].x, lm[i].y, lm[i].visibility)
            for nombre, i in (("hombro", hombro), ("codo", codo), ("muneca", muneca))
        }
        self.abd = self._suavizar(self.abd, ang, dt)
        self.rom_min = self.abd if self.rom_min is None else min(self.rom_min, self.abd)
        self.rom_max = self.abd if self.rom_max is None else max(self.rom_max, self.abd)
        if not self.abd_arriba and self.abd > ABD_ARRIBA:
            self.abd_arriba = True
        elif self.abd_arriba and self.abd < ABD_ABAJO:
            self.abd_arriba = False
            self.repeticiones_abduccion += 1
            self._anotar(t, f"abduccion {self.repeticiones_abduccion}")

    def _fase_2(self, lm, dt, t):
        # sentadilla: la rodilla mas flexionada
        angulos = []
        for cadera, rodilla, tobillo in ((CADERA_I, RODILLA_I, TOBILLO_I), (CADERA_D, RODILLA_D, TOBILLO_D)):
            if self._visibles(lm, (cadera, rodilla, tobillo)):
                angulos.append(calcular_angulo(self._p(lm, cadera), self._p(lm, rodilla), self._p(lm, tobillo)))
        if not angulos:
            return
        self.sent = self._suavizar(self.sent, min(angulos), dt)
        if not self.sent_abajo and self.sent < SENT_ABAJO:
            self.sent_abajo = True
        elif self.sent_abajo and self.sent > SENT_ARRIBA:
            self.sent_abajo = False
            self.repeticiones_sentadilla += 1
            self._anotar(t, f"sentadilla {self.repeticiones_sentadilla}")

    def _fase_3(self, lm, t):
        # compensacion: tronco inclinado lateralmente de forma sostenida
        if not self._visibles(lm, (HOMBRO_I, HOMBRO_D, CADERA_I, CADERA_D)):
            self.inclinado_desde = None
            return
        hx = (lm[HOMBRO_I].x + lm[HOMBRO_D].x) / 2
        hy = (lm[HOMBRO_I].y + lm[HOMBRO_D].y) / 2
        cx = (lm[CADERA_I].x + lm[CADERA_D].x) / 2
        cy = (lm[CADERA_I].y + lm[CADERA_D].y) / 2
        inclinacion = abs(math.degrees(math.atan2(hx - cx, cy - hy)))

        if inclinacion <= INCLINACION_MAX:
            self.inclinado_desde = None
            self.error_activo = False
            return
        if self.inclinado_desde is None:
            self.inclinado_desde = t
        if not self.error_activo and t - self.inclinado_desde >= INCLINACION_PERSISTE_S:
            self.error_activo = True
            if not self.timestamps_errores or t - self.timestamps_errores[-1] >= ERROR_SEPARACION_S:
                self.timestamps_errores.append(round(t, 2))
                self._anotar(t, "compensacion tronco")

    # ---------------------------------------------------------------- salida
    def resultados(self):
        """Diccionario con el esquema exacto exigido por el evaluador."""
        return {
            "fase_1": {"repeticiones_abduccion": int(self.repeticiones_abduccion)},
            "fase_2": {"repeticiones_sentadilla": int(self.repeticiones_sentadilla)},
            "fase_3": {
                "compensaciones_detectadas": bool(self.timestamps_errores),
                "timestamps_errores_segundos": list(self.timestamps_errores),
            },
        }

    def instantanea(self):
        """Estado actual para la interfaz en vivo (panel de metricas de app.py)."""
        with self.lock:
            rom = None if self.rom_min is None else round(self.rom_max - self.rom_min)
            if self.abd_arriba:
                fase = "abduccion"
            elif self.sent_abajo:
                fase = "sentadilla"
            else:
                fase = "reposo"
            return {
                "live": True,
                "pose": self.pose_detectada,
                "angulo": None if self.abd is None else round(self.abd),
                "rom": rom,
                "reps": f"{self.repeticiones_abduccion} / {self.repeticiones_sentadilla}",
                "fase": fase,
                "lado": self.lado,
                "fps": round(self.fps, 1),
                "lat": round(self.latencia_ms, 1),
                "res": self.resolucion,
                "vis": self.visibles,
                "vec": {k: [round(v[0], 2), round(v[1], 2), round(v[2], 2)] for k, v in self.vectores.items()},
                "log": list(self.log)[-7:],
            }
