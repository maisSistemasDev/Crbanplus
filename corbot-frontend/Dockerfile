FROM node:22-alpine AS builder

WORKDIR /app

# As envs PUBLIC_* do Astro são embutidas em build-time. Em produção, com NPM
# fazendo proxy de /api/, /ws/, /media/ e /static/ no mesmo domínio do
# frontend, basta deixá-las vazias para o cliente usar caminhos relativos.
ARG PUBLIC_API_URL=
ARG PUBLIC_WS_URL=
ARG PUBLIC_PORTAL_APP_URL=
ENV PUBLIC_API_URL=$PUBLIC_API_URL
ENV PUBLIC_WS_URL=$PUBLIC_WS_URL
ENV PUBLIC_PORTAL_APP_URL=$PUBLIC_PORTAL_APP_URL

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM node:22-alpine

WORKDIR /app

COPY --from=builder /app/dist ./dist
COPY --from=builder /app/package*.json ./
RUN npm ci --omit=dev

ENV HOST=0.0.0.0
ENV PORT=3000

EXPOSE 3000

CMD ["node", "./dist/server/entry.mjs"]
