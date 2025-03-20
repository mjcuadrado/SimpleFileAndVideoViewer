FROM python:3.9-slim

WORKDIR /app

# Instalar dependencias del sistema: ffmpeg y git
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el contenido de app/ a /app (sin el subdirectorio app/)
COPY app/ .

EXPOSE 5000

CMD ["python", "app.py"]