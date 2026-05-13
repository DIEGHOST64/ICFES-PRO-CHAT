# ── Etapa 1: Build ──────────────────────────────────────
FROM node:20-alpine AS builder

ARG VITE_AI_URL=/ai
ENV VITE_AI_URL=$VITE_AI_URL

WORKDIR /app
COPY package*.json ./
RUN npm ci --silent
COPY . .
RUN npm run build

# ── Etapa 2: Producción con Nginx ───────────────────────
FROM nginx:alpine

# Copiar build de Vite
COPY --from=builder /app/dist /usr/share/nginx/html

# Configuración personalizada de Nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
