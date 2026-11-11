si, otro puto año mas haciendo la hackathon de los cojones
# EURI-CHALLENGE: Monitor de Rehabilitación Biomédica
**Hackathon Anual - EESTEC LC Madrid & Eurielec (ETSIT, UPM)**

Bienvenido al repositorio oficial del reto de Ingeniería Biomédica. Este proyecto plantea el desarrollo de un software interactivo capaz de guiar y evaluar ejercicios de rehabilitación física en tiempo real, utilizando únicamente una cámara web y modelos de visión por computador (MediaPipe Pose).

El objetivo es crear un prototipo funcional que garantice la continuidad asistencial del paciente en su domicilio, gamificando la rehabilitación y extrayendo métricas clínicas objetivas.

---

## 1. Requisitos Previos
Para garantizar un entorno de desarrollo estable y sin conflictos de hardware o sistema operativo, este proyecto está completamente "Dockerizado". Necesitas tener instalado:
* **Git** (Para clonar este repositorio).
* **Docker Desktop** o **Docker Engine** junto con **Docker Compose**.
* Un navegador web moderno (Google Chrome o Mozilla Firefox recomendados).

## 2. Instrucciones de Despliegue
La infraestructura base (conexión con la cámara, estimación de pose y servidor web) ya está configurada. Para iniciar el entorno de desarrollo, sigue estos pasos:

1. Abre tu terminal y clona este repositorio.
2. Navega hasta la raíz de la carpeta del proyecto.
3. Ejecuta el siguiente comando para construir y levantar el contenedor:
   ```bash
   docker compose up --build
   ```

---

## Normas de Evaluación Automatizada
**La interfaz gráfica (Streamlit) no se utilizará para evaluar la precisión matemática de tu solución.** La interfaz sirve para demostrar y depurar; la puntuación se obtiene ejecutando tu lógica de forma automática sobre vídeos de prueba y comparando el resultado con la referencia.

Por eso tu lógica de procesamiento debe poder ejecutarse **sin interfaz** y en cualquier lenguaje o entorno que prefieras (Python, C++, Node, etc.), siempre que respete el siguiente contrato.

### Contrato de ejecución
* Debes proporcionar un script de entrada en la raíz del proyecto: `eval.py` (por defecto) o `run.sh`.
* El script recibe **un único argumento posicional**: la ruta absoluta a un vídeo `.mp4`.
  ```bash
  python eval.py /ruta/absoluta/al/video.mp4
  # o bien
  ./run.sh /ruta/absoluta/al/video.mp4
  ```
* Debe procesar el vídeo **de principio a fin y lo más rápido posible** (no a velocidad de reproducción).
* Los intervalos de tiempo (`time-deltas`) se calculan **a partir de los timestamps de los fotogramas** del vídeo (por ejemplo `cap.get(cv2.CAP_PROP_POS_MSEC)` en OpenCV), **nunca contando fotogramas**. Así el resultado no depende de los FPS del vídeo ni de la velocidad de tu equipo.
* Al terminar debe generar un archivo llamado exactamente `resultados.json` en la raíz del proyecto.

### Esquema JSON obligatorio
```json
{
  "fase_1": { "repeticiones_abduccion": 0 },
  "fase_2": { "repeticiones_sentadilla": 0 },
  "fase_3": { "compensaciones_detectadas": false, "timestamps_errores_segundos": [] }
}
```
| Clave | Tipo | Descripción |
|---|---|---|
| `fase_1.repeticiones_abduccion` | entero | Repeticiones completas de abducción de hombro |
| `fase_2.repeticiones_sentadilla` | entero | Repeticiones completas de sentadilla |
| `fase_3.compensaciones_detectadas` | booleano | `true` si se detectó alguna compensación |
| `fase_3.timestamps_errores_segundos` | lista de números | Segundo del vídeo en el que ocurrió cada compensación |

> **Atención:** cualquier desviación en el nombre de las claves (mayúsculas, tildes, claves extra o ausentes, anidación distinta) hará que **la métrica correspondiente puntúe cero**. Respeta el esquema tal cual, incluso si una fase queda sin resolver (déjala con su valor por defecto).

### Plantilla incluida
El repositorio trae un ejemplo funcional del flujo completo:
* [`eval.py`](eval.py): lee `sys.argv[1]`, inicializa `RehabEngine`, recorre el vídeo con OpenCV pasando el timestamp de cada fotograma y vuelca el resultado en `resultados.json`.
* [`app/rehab_engine.py`](app/rehab_engine.py): clase `RehabEngine` con la lógica de las tres fases, **sin ninguna dependencia de Streamlit**. Es la parte que debes mejorar.

Para probarlo dentro del contenedor:
```bash
docker compose run --rm -v "$PWD":/proyecto -w /proyecto web python eval.py /proyecto/mi_video.mp4
```
