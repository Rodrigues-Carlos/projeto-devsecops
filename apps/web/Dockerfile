# syntax=docker/dockerfile:1
# Imagem nginx nao-privilegiada (roda como uid 101, atende em 8080) -> compativel
# com Pod Security Standard "restricted" (runAsNonRoot).
FROM nginxinc/nginx-unprivileged:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html styles.css app.js /usr/share/nginx/html/

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD wget -qO- http://127.0.0.1:8080/ >/dev/null 2>&1 || exit 1
