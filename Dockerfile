# Utiliza la imagen oficial de Python 3.11
FROM python:3.11

# Establece el directorio de trabajo en /app
WORKDIR /app

# Declara el volumen para la carpeta uploads
VOLUME ["/app/uploads"]

# Copia el archivo requirements.txt a la imagen
COPY requirements.txt .

# Instala las dependencias listadas en el archivo requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copia todos los archivos del proyecto en el contenedor
COPY . .

# Exponer el puerto en el que corre Flask (por defecto 5000)
EXPOSE 5000

# Comando para ejecutar la aplicación
CMD ["python", "app.py"]
