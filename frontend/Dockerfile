FROM node:22-alpine AS builder

WORKDIR /app

ARG APP_PATH_PREFIX=/meals

COPY package*.json /app/
RUN npm ci

COPY . /app
RUN APP_PATH_PREFIX="${APP_PATH_PREFIX%/}" \
    && VITE_BASE_PATH="${APP_PATH_PREFIX}/" npm run build

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80
