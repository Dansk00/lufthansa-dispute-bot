# Lufthansa Dispute Ops & Bot - Cloud Container
FROM python:3.12-slim-bookworm

# Avoid prompts from apt
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV HEADLESS=true
ENV PORT=8000
ENV TZ="America/Sao_Paulo"

# Install system dependencies required for Chromium & Patchright + Timezone Brasilia
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    gnupg \
    ca-certificates \
    tzdata \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency definition
COPY lufthansa_bot/requirements.txt /app/requirements.txt

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install browser binary and system libraries for Patchright
RUN python -m patchright install --with-deps chromium

# Copy application files
COPY lufthansa_bot /app/lufthansa_bot

# Create data directories
RUN mkdir -p /app/lufthansa_bot/data/attachments /app/lufthansa_bot/data/evidence

EXPOSE 8000

# Start FastAPI web portal with embedded daily scheduler
CMD ["sh", "-c", "uvicorn lufthansa_bot.web.app:app --host 0.0.0.0 --port ${PORT}"]
