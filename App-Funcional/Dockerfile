# Imagen del prototipo funcional AZA Analyzer
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLBACKEND=Agg

# OpenCV necesita estas librerías de sistema en Linux
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 libglib2.0-0 tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY vision_aza ./vision_aza
COPY web ./web

EXPOSE 8000

# El pipeline de visión genera ráfagas en este volumen; en la nube además se
# suben a MinIO/S3, por lo que el disco solo se usa como caché de trabajo.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
