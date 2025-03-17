#!/bin/bash

# Stop all running containers
echo "building the dir..."
npm run build

# Remove all containers
echo "Coping the file..."
sudo cp -rf dist/* /var/www/html/
# Remove all Docker images
echo "nginx service reload..."
sudo systemctl reload nginx.service
echo "Done done !!!."

