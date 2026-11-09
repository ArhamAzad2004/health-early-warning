# Build the dashboard, then run it and the API as one app.
# Base images pinned by digest (Dependabot keeps them current) so a rebuild can't pick up a different image.
FROM node:26-slim@sha256:5adad64f9a1fca2d51972caa65983634c8a774eb300d72b20f7f2a0f60368072 AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim@sha256:e48f59cdba69a3cbd9ed2cf0f348d90d45a8d350d98134cf1070bc106ee9ed90
WORKDIR /app
COPY backend/requirements-lock.txt .
RUN pip install --no-cache-dir --require-hashes --only-binary=:all: -r requirements-lock.txt
COPY backend/ ./
COPY --from=web /web/dist ./static
ENV STATIC_DIR=/app/static API_DOCS=0
RUN useradd --system app
USER app
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
