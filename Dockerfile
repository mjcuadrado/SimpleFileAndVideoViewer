FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instalar ffmpeg
RUN apt-get update && apt-get install -y ffmpeg

# Copiar todo el contenido del proyecto
COPY . .

# Cambiar el comando para ejecutar app.py dentro de la subcarpeta app/
CMD ["python", "app/app.py"]