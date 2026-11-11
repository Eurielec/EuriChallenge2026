"""Punto de entrada del evaluador automatico.

Uso:
    python eval.py /ruta/absoluta/al/video.mp4

Procesa el video completo, lo mas rapido posible, y escribe `resultados.json`
en la raiz del proyecto. No usa Streamlit ni ninguna interfaz grafica.
"""
import json
import os
import sys

import cv2

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(RAIZ, "app"))

from rehab_engine import RehabEngine  # noqa: E402

SALIDA = os.path.join(RAIZ, "resultados.json")


def main():
    if len(sys.argv) != 2:
        print("Uso: python eval.py <ruta_absoluta_al_video.mp4>", file=sys.stderr)
        return 2

    ruta = sys.argv[1]
    cap = cv2.VideoCapture(ruta)
    if not os.path.isfile(ruta) or not cap.isOpened():
        print(f"No se pudo abrir el video: {ruta}", file=sys.stderr)
        return 1

    motor = RehabEngine()
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    ultimo_ms = -1.0
    n = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        # tiempo real del fotograma segun el contenedor, independiente de la velocidad de proceso
        t_ms = cap.get(cv2.CAP_PROP_POS_MSEC)
        if t_ms <= ultimo_ms:  # contenedores sin timestamps validos
            t_ms = ultimo_ms + 1000.0 / fps
        ultimo_ms = t_ms
        motor.procesar_fotograma(frame, t_ms)
        n += 1

    cap.release()

    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(motor.resultados(), f, ensure_ascii=False, indent=2)
    print(f"{n} fotogramas procesados -> {SALIDA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

