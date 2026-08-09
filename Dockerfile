# syntax=docker/dockerfile:1

FROM node:22-bookworm-slim AS frontend
WORKDIR /frontend

COPY ant-design-pro/ ./
ENV HUSKY=0 CI=true
RUN npm install --no-audit --no-fund --include=dev
ENV NODE_ENV=production
RUN npm run build

FROM python:3.11-slim

WORKDIR /app

ARG BUILD_SHA=unknown
ARG BUILD_BRANCH=unknown
ARG BUILD_TIME=unknown

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    GUNICORN_WORKERS=1 \
    GUNICORN_THREADS=8 \
    GUNICORN_TIMEOUT=120 \
    SPA_ENABLED=true \
    BUILD_SHA=${BUILD_SHA} \
    BUILD_BRANCH=${BUILD_BRANCH} \
    BUILD_TIME=${BUILD_TIME}

COPY requirements.txt .
RUN pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip install gunicorn -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY . .
COPY --from=frontend /frontend/dist /app/ant-design-pro/dist

# Persist build identity for runtime diagnostics (/healthz).
RUN printf '%s\n' "$BUILD_SHA" > /app/.build_sha && \
    printf '%s\n' "$BUILD_BRANCH" > /app/.build_branch && \
    printf '%s\n' "$BUILD_TIME" > /app/.build_time && \
    mkdir -p /app/data && chmod +x /app/scripts/start-gunicorn.sh

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s CMD ["python","-c","import urllib.request as u; u.urlopen('http://localhost:5000/healthz', timeout=4).read()"]

CMD ["scripts/start-gunicorn.sh"]
