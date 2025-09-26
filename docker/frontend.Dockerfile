# syntax=docker/dockerfile:1

# -------- Builder --------
FROM node:20-alpine AS builder

WORKDIR /app/frontend

# Install deps (cache-friendly)
COPY app/frontend/package.json app/frontend/package-lock.json ./
RUN npm ci

# Copy source and build
COPY app/frontend ./
RUN npm run build

# -------- Runner --------
FROM node:20-alpine AS runner

ENV NODE_ENV=production \
    PORT=3000

WORKDIR /app/frontend

# Copy minimal runtime artifacts
COPY --from=builder /app/frontend/node_modules ./node_modules
COPY --from=builder /app/frontend/.next ./.next
COPY --from=builder /app/frontend/public ./public
COPY app/frontend/package.json app/frontend/next.config.ts ./

EXPOSE 3000

USER node

CMD ["npm", "start", "--", "-p", "3000"]


