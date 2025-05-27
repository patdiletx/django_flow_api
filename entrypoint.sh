#!/bin/sh

# Salir inmediatamente si un comando falla
set -e

# Ejecutar las migraciones de Django
# El flag --noinput evita que pida confirmación
echo "Aplicando migraciones de base de datos..."
python manage.py migrate --noinput

# Iniciar Gunicorn (el comando que ya teníamos)
# Usamos 'exec' para que Gunicorn reemplace este script y se convierta en el proceso principal (PID 1),
# lo cual es importante para que maneje correctamente las señales del sistema (como cuando Render lo detiene).
echo "Iniciando Gunicorn..."
exec gunicorn flow_project.wsgi:application --bind 0.0.0.0:8000 --log-level=debug --access-logfile=- --error-logfile=-