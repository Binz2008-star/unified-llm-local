# Code It Dashboard - Multi-stage build (3 stages)
# Stage 1: Build application assets & server code
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# 1. Build UI (React / Vite)
RUN npm run build

# 2. Bundle server.ts explicitly to dist/server.cjs
RUN npx esbuild server.ts --bundle --platform=node --target=node20 --outfile=dist/server.cjs

# Stage 2: Install production dependencies only
FROM node:20-alpine AS prod-deps

WORKDIR /app

COPY package*.json ./
RUN npm ci --omit=dev && npm cache clean --force

# Stage 3: Production runner
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV PORT=3000

COPY --from=prod-deps /app/node_modules ./node_modules
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/package*.json ./

USER node

EXPOSE 3000

CMD ["node", "dist/server.cjs"]