# GreenGuard frontend (Next.js 15) production image, multi-stage so the
# final image only ships the standalone server output, not node_modules or
# the build cache. NEXT_PUBLIC_* values are baked in at build time (Next.js
# requirement) -- pass them as build args, never as secrets.

FROM node:22-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:22-slim AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
ARG NEXT_PUBLIC_APP_NAME=GreenGuard
ARG NEXT_PUBLIC_ENVIRONMENT=production
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL \
    NEXT_PUBLIC_APP_NAME=$NEXT_PUBLIC_APP_NAME \
    NEXT_PUBLIC_ENVIRONMENT=$NEXT_PUBLIC_ENVIRONMENT

RUN npm run build

FROM node:22-slim AS runner
WORKDIR /app
ENV NODE_ENV=production

COPY --from=build /app/public ./public
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static

# node:22-slim already ships a non-root "node" user (uid 1000).
RUN chown -R node:node /app
USER node

EXPOSE 3000
CMD ["node", "server.js"]
