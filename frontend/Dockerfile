FROM node:18-alpine as build-stage
 
WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

RUN npm run build
 
FROM nginx:alpine as production-stage

COPY --from=build-stage /app/dist /var/www/html

COPY nginx.conf /etc/nginx/conf.d/default.conf

COPY ssl/self-signed.crt /etc/nginx/ssl/self-signed.crt

COPY ssl/self-signed.key /etc/nginx/ssl/self-signed.key

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
 
