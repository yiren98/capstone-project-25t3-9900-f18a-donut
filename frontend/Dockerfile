# build stage
FROM node:20 AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# serve stage
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
# Redirects file to support React Router
COPY public/_redirects /usr/share/nginx/html/_redirects
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
