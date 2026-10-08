import cv2
import mediapipe as mp
import numpy as np

def obtener_estilos_dibujo():
    """
    Retorna la configuracion visual del esqueleto para MediaPipe.
    Paleta roja y blanca de alto contraste sobre fondo de camara.
    """
    mp_drawing = mp.solutions.drawing_utils
    
    # Puntos articulares (blanco frio de alta visibilidad)
    spec_puntos = mp_drawing.DrawingSpec(
        color=(245, 245, 250),
        thickness=-1,
        circle_radius=3
    )
    
    # Lineas de conexion osea (rojo carmesi en formato BGR)
    spec_conexiones = mp_drawing.DrawingSpec(
        color=(25, 25, 220),
        thickness=2,
        circle_radius=1
    )
    
    return spec_puntos, spec_conexiones


def calcular_angulo(a, b, c):
    """
    Calcula el angulo articular formado por tres puntos (A -> B -> C)
    donde B es el vertice articular (por ejemplo hombro o codo).
    Retorna el angulo en grados [0 - 180].
    """
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)

    radianes = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    angulo = np.abs(radianes * 180.0 / np.pi)

    if angulo > 180.0:
        angulo = 360.0 - angulo

    return float(angulo)