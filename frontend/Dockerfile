FROM node:22

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy the rest of the project
COPY . .

# Copy SSL certs (you must have these in your project directory)
COPY cert.pem .
COPY key.pem .

# Expose the dev server port
EXPOSE 9980

# Run the dev server with HTTPS
CMD ["npm", "run", "dev"]
