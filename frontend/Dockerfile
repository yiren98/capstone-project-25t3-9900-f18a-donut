# === Stage 1: Build frontend ===
FROM node:20 AS build

WORKDIR /app

# 复制依赖文件并安装
COPY package*.json ./
RUN npm install

# ✅ 接收 Render 环境变量
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

# ✅ 打印变量供日志验证
RUN echo ">>> Building with VITE_API_BASE_URL=$VITE_API_BASE_URL"

# 复制前端代码
COPY . .

# ✅ 直接 build，不要加 --mode production
RUN npm run build

# === Stage 2: Serve static files with Nginx ===
FROM nginx:alpine

# 复制构建结果
COPY --from=build /app/dist /usr/share/nginx/html

# Nginx 配置（支持 SPA）
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

