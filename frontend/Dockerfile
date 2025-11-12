FROM node:18 AS build

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

RUN npm run build

FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html

COPY public/_redirects /usr/share/nginx/html/_redirects

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
