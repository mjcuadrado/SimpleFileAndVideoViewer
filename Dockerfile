FROM python:3.9-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Establecer el directorio de trabajo
WORKDIR /app

# Copiar requirements.txt e instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Verificar instalación de dependencias
RUN pip show Flask Flask-SQLAlchemy psycopg2-binary python-dotenv bcrypt tenacity || echo "Dependencias no instaladas correctamente"

# Copiar el contenido de app/ a /app/app/
COPY app/ app/

# Copiar main.py a /app/
COPY main.py .

# Verificar que los archivos existen y listar el contenido de /app y /app/app
RUN ls -la /app && ls -la /app/app && ls -la /app/main.py && ls -la /app/app/__init__.py && ls -la /app/app/routes && ls -la /app/app/services && ls -la /app/app/models || echo "Algunos archivos no encontrados"

# Asegurar permisos
RUN chmod +r /app/main.py

# Exponer el puerto
EXPOSE 5000

# Ejecutar main.py
CMD ["python", "main.py"]