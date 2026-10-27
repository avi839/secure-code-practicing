# SecureReflex AI - Frontend image (Next.js 14)
# Next.js bakes rewrites in at build time, so BACKEND_URL must be a build argument.

# ---- build stage ----
FROM node:20-alpine AS build
WORKDIR /app

ARG BACKEND_URL=http://backend:8000
ENV BACKEND_URL=${BACKEND_URL} \
    NEXT_TELEMETRY_DISABLED=1

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# ---- runtime stage ----
FROM node:20-alpine AS runtime
WORKDIR /app

ARG BACKEND_URL=http://backend:8000
ENV NODE_ENV=production \
    BACKEND_URL=${BACKEND_URL} \
    NEXT_TELEMETRY_DISABLED=1

COPY package.json package-lock.json ./
RUN npm ci --omit=dev && npm cache clean --force

COPY --from=build /app/.next ./.next
COPY --from=build /app/public ./public
COPY --from=build /app/next.config.js ./next.config.js

USER node
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://127.0.0.1:3000/ || exit 1

CMD ["npm", "start", "--", "-p", "3000"]
