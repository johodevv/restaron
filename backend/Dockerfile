FROM python:3.11-slim

WORKDIR /app

# Tizim kutubxonalari
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Python kutubxonalari
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kod
COPY . .

# Upload papkasi
RUN mkdir -p uploads/qr_codes uploads/menu_items uploads/logos

# Port
EXPOSE 8000

# Ishga tushirish
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
