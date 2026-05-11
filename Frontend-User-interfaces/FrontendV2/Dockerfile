# ── Stage 1: build ───────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Install deps first (layer cache)
COPY Frontend-User-interfaces/FrontendV2/package.json Frontend-User-interfaces/FrontendV2/package-lock.json* ./
RUN npm ci

# Copy source, data folder, and build
COPY Frontend-User-interfaces/FrontendV2/ ./
COPY data /app/data

# Build args are baked in at image build time.
# Pass them with --build-arg when using docker build directly,
# or via the `build.args` section in docker-compose.
ARG VITE_API_BASE_URL=http://localhost:8000/api
ARG VITE_WS_URL=ws://localhost:8765

ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_WS_URL=$VITE_WS_URL

RUN npm run build

# ── Stage 2: serve ────────────────────────────────────────────────────────────
FROM nginx:stable-alpine

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# nginx config — single-page app routing (all paths → index.html)
RUN printf 'server {\n\
    listen 80;\n\
    root /usr/share/nginx/html;\n\
    index index.html;\n\
\n\
    # All routes fall through to index.html (React Router)\n\
    location / {\n\
        try_files $uri $uri/ /index.html;\n\
    }\n\
\n\
    # Cache static assets aggressively (they have content hashes in filenames)\n\
    location /assets/ {\n\
        expires 1y;\n\
        add_header Cache-Control "public, immutable";\n\
    }\n\
}\n' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
