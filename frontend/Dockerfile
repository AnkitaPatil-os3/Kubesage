# Use Node.js 22 Alpine for the build stage
FROM node:22-alpine as build-stage
 
WORKDIR /app
 
# Copy package files and install dependencies
COPY package*.json ./
RUN npm install
 
# Copy the rest of the application code
COPY . .
 
# Build the application
RUN npm run build
 
# Use Nginx Alpine for the production stage
FROM nginx:alpine as production-stage
 
# Copy built application files from the build stage
COPY --from=build-stage /app/dist /var/www/html
 
# Copy Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf
 
# Copy SSL certificates
COPY ssl/self-signed.crt /etc/nginx/ssl/self-signed.crt
COPY ssl/self-signed.key /etc/nginx/ssl/self-signed.key
 
# Expose HTTP and HTTPS ports
EXPOSE 80 443
 
# Start Nginx in the foreground
CMD ["nginx", "-g", "daemon off;"]
