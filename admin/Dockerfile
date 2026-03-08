# ── Stage 1: install dependencies ────────────────────────────────────────────
FROM node:20-alpine AS deps

WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci --omit=dev


# ── Stage 2: build Next.js ────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci
COPY . .

# Bake-in a placeholder; real secrets are injected via Cloud Run env vars
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build


# ── Stage 3: lean runtime image ───────────────────────────────────────────────
FROM node:20-alpine AS runner

WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Only copy what Next.js needs at runtime
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

# Cloud Run sets $PORT at runtime (defaults to 8080)
ENV PORT=8080
EXPOSE 8080

CMD ["node", "server.js"]
