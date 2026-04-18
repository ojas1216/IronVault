# ─── Build Stage ─────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci --frozen-lockfile

COPY . .
RUN npm run build

# ─── Production Stage ─────────────────────────────────────────────────────────
FROM nginx:alpine AS production

# Copy build output
COPY --from=builder /app/dist /usr/share/nginx/html

# Nginx config for SPA routing
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
