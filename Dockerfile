# Deployment ke liye Dockerfile (Hugging Face Spaces / Koyeb / Render / Railway sab par chalta hai)
FROM python:3.11-slim

WORKDIR /app

# Playwright / Chromium ke liye zaroori system libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl wget fonts-liberation libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 \
    libxrandr2 libgbm1 libasound2 libpangocairo-1.0-0 libpango-1.0-0 \
    libcairo2 libatspi2.0-0 libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

# python deps pehle install (cache friendly)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Chromium browser download (Playwright)
RUN playwright install chromium

# baqi code copy
COPY . .

# HF Spaces port 7860 use karte hain; doosri platforms PORT env use karte hain
ENV PORT=7860
EXPOSE 7860

# app start
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-7860}"]
