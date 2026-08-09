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

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    GUNICORN_WORKERS=1 \
    GUNICORN_THREADS=8 \
    GUNICORN_TIMEOUT=120 \
    SPA_ENABLED=true

COPY requirements.txt .
RUN pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip install gunicorn -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY . .
COPY --from=frontend /frontend/dist /app/ant-design-pro/dist

RUN mkdir -p /app/data && chmod +x /app/scripts/start-gunicorn.sh && \
    if [ -f /app/.build-info ]; then cp /app/.build-info /app/.build_info_copy; fi

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s CMD ["python","-c","import urllib.request as u; u.urlopen('http://localhost:5000/healthz', timeout=4).read()"]

CMD ["scripts/start-gunicorn.sh"]
