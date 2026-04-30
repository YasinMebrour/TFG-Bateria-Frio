FROM python:3.12-slim

# ───────── zona horaria (opcional) ─────────
ENV TZ=Europe/Madrid

# ───────── dependencias de sistema ─────────
# • build-essential y cmake permiten compilar wheels que no traen binario pre-compilado
# • libgomp1  -> runtime OpenMP que usa LightGBM
# • libstdc++6 (viene con libgcc-1) por seguridad
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        libgomp1 \
        libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

# ───────── código de la aplicación ─────────
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app

EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
