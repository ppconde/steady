FROM python:3.13-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DB_PATH=/data/steady.db
RUN pip install --no-cache-dir anthropic==2.4.0 && useradd -u 1000 -m appuser && mkdir /data && chown appuser /data
WORKDIR /app
COPY steady ./steady
USER appuser
EXPOSE 8080
CMD ["python", "-m", "steady"]
