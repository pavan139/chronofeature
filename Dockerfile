FROM python:3.12-slim AS builder
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends gcc libc6-dev && rm -rf /var/lib/apt/lists/*
COPY . .
RUN pip wheel --no-cache-dir --wheel-dir /wheels .

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels && useradd --create-home astro
USER astro
ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn gunamilan.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
