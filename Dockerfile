# Usa Python base (compatibile con PyTorch e Transformers)
FROM python:3.10-slim

# Evita messaggi interattivi durante l'installazione
ENV DEBIAN_FRONTEND=noninteractive

# Installa ffmpeg e pacchetti di sistema
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Crea directory lavoro
WORKDIR /app

# Copia i file del progetto
COPY . .

# Installa le dipendenze Python
RUN pip install --no-cache-dir -r requirements.txt

# Comando di avvio
CMD ["python", "neaBot.py"]
