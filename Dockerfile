# Tarot Thoth bot — a single long-lived aiogram long-polling process.
# No inbound HTTP: the bot only makes outbound calls (Telegram + Claude API),
# so the image exposes no port. The bundled card art (assets/) ships in the
# image; the SQLite DB lives on a mounted volume (DB_PATH).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot ./bot
COPY assets ./assets
COPY main.py .

CMD ["python", "main.py"]
