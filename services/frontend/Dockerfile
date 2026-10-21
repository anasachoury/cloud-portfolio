# Base runs as uid 101 on port 8080 — matches the chart's frontend values
# (runAsUser: 101, targetPort: 8080).
FROM nginxinc/nginx-unprivileged:1.27-alpine

COPY index.html /usr/share/nginx/html/index.html
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

EXPOSE 8080
