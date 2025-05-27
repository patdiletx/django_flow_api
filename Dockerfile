# Usa una imagen oficial de Python como base
FROM python:3.11-slim

# Evita que Python guarde el output en un buffer
ENV PYTHONUNBUFFERED 1

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia el archivo de requerimientos y los instala
# Hacemos esto primero para aprovechar el cache de Docker si no cambian las dependencias
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copia el resto del código del proyecto al directorio de trabajo
COPY . .

# Copia el script de inicio al contenedor
COPY ./entrypoint.sh /app/entrypoint.sh
# Asegúrate de que sea ejecutable DENTRO del contenedor también
RUN chmod +x /app/entrypoint.sh
# Expone el puerto en el que Gunicorn escuchará
EXPOSE 8000
# Comando para iniciar la aplicación cuando el contenedor arranque
CMD ["/app/entrypoint.sh"]