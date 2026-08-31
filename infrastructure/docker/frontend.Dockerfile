FROM node:20-alpine AS dependencies

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund --fetch-retries=5 --fetch-retry-mintimeout=20000 --fetch-retry-maxtimeout=120000

FROM node:20-alpine AS builder

WORKDIR /app

ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_WS_URL
ARG NEXT_PUBLIC_PHASE5_PILOT_INVITES_ENABLED=false

ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL} \
    NEXT_PUBLIC_WS_URL=${NEXT_PUBLIC_WS_URL} \
    NEXT_PUBLIC_PHASE5_PILOT_INVITES_ENABLED=${NEXT_PUBLIC_PHASE5_PILOT_INVITES_ENABLED}

COPY --from=dependencies /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:20-alpine AS runtime

ENV NODE_ENV=production

RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

WORKDIR /app

RUN mkdir -p /app/.next/cache \
    && chown -R nextjs:nodejs /app

COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public
COPY --chown=nextjs:nodejs healthcheck.mjs ./healthcheck.mjs

# ECS Fargate bind mounts otherwise default to root-owned mode 0755. Define
# these paths in the image after setting ownership so writable ephemeral mounts
# preserve the permissions required by the non-root Next.js process.
RUN mkdir -p /app/.next/cache \
    && chown -R nextjs:nodejs /app \
    && chmod 1777 /tmp

VOLUME ["/tmp", "/app/.next/cache"]

USER nextjs

EXPOSE 3000

ENV PORT=3000 \
    HOSTNAME=0.0.0.0

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD ["node", "/app/healthcheck.mjs"]

CMD ["node", "server.js"]
