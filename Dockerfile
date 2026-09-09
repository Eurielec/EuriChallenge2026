FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema necesarias para compilar el vídeo
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar librerías
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
#Tengo que poner las librerias buenas de streatmilt, UI Gráfica y la mierda esta de el globo

# Exponer el puerto de Streamlit
EXPOSE 8501

# El comando que arranca la web cuando se enciende el contenedor
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]