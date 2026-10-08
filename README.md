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