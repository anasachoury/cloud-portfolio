# Base runs as uid 101 on port 8080 — matches the chart's frontend values
# (runAsUser: 101, targetPort: 8080). Pinned exact version: trivy gates the
# image on HIGH/CRITICAL with fixes available, and floating tags like
# 1.27-alpine go stale (the 1.27 line shipped openssl 3.3.3 with 2 CRITICALs).
FROM nginxinc/nginx-unprivileged:1.31.7-alpine

# Patch distro packages ahead of upstream image rebuilds: the tag above was
# built before CVE fixes for brotli (CVE-2026-111497) and curl landed in
# alpine. Once nginxinc publishes a rebuilt tag, this layer becomes a no-op.
USER root
RUN apk upgrade --no-cache
USER 101

COPY index.html /usr/share/nginx/html/index.html
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

EXPOSE 8080
