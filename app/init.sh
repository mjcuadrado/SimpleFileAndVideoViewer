#!/bin/bash
# Esperar a que la base de datos esté lista (aumentado a 30 segundos)
sleep 30

# Verificar si las migraciones ya existen y están inicializadas
if [ ! -f "/app/migrations/env.py" ]; then
    echo "Inicializando migraciones por primera vez..."
    flask db init
    flask db migrate -m "Initial migration with has_subtitles"
    flask db upgrade
else
    echo "Migraciones ya inicializadas, aplicando actualizaciones si las hay..."
    flask db upgrade
fi

# Ejecutar la aplicación
python app.py