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

# Copiar app.py desde la raíz del proyecto
COPY app.py .

# Copiar las subcarpetas static/ y templates/ desde app/
COPY app/static/ static/
COPY app/templates/ templates/

# Verificar que app.py existe (para depuración)
RUN ls -la /app/app.py || echo "app.py no encontrado"

# Verificar que las subcarpetas existen
RUN ls -la /app/static /app/templates || echo "static o templates no encontrado"

# Asegurar permisos
RUN chmod +r /app/app.py

# Exponer el puerto
EXPOSE 5000

# Ejecutar app.py
CMD ["python", "app.py"]