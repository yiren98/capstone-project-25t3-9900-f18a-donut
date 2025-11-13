# === Stage 1: Build frontend ===
FROM node:20 AS build

WORKDIR /app

# 复制依赖文件并安装
COPY package*.json ./
RUN npm install

# ✅ 复制环境变量文件（非常关键）
COPY .env.production ./

# 复制前端代码并构建
COPY . .
RUN npm run build

# === Stage 2: Serve static files with Nginx ===
FROM nginx:alpine

# 复制构建产物到 Nginx 静态目录
COPY --from=build /app/dist /usr/share/nginx/html

# 替换默认 Nginx 配置（支持 SPA 前端）
RUN printf "server {\n\
  listen 80;\n\
  server_name localhost;\n\
  root /usr/share/nginx/html;\n\
  index index.html;\n\
  location / {\n\
    try_files \$uri /index.html;\n\
  }\n\
}" > /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
