#!/bin/bash

echo "-----------------------------"
echo "Updating system packages..."
echo "-----------------------------"
sudo apt update

echo ""
echo "-----------------------------"
echo "Installing RabbitMQ Server..."
echo "-----------------------------"
sudo apt install -y rabbitmq-server

echo ""
echo "----------------------------------------"
echo "Enabling RabbitMQ Management Plugin..."
echo "----------------------------------------"
sudo rabbitmq-plugins enable rabbitmq_management

echo ""
echo "---------------------------------"
echo "Starting and Enabling RabbitMQ..."
echo "---------------------------------"
sudo systemctl start rabbitmq-server
sudo systemctl enable rabbitmq-server

echo ""
echo "RabbitMQ Web Interface: http://<your-server-ip>:15672"
echo ""

echo "--------------------------"
echo "Installing Redis Server..."
echo "--------------------------"
sudo apt install -y redis-server

echo ""
echo "--------------------------------"
echo "Starting and Enabling Redis..."
echo "--------------------------------"
sudo systemctl enable redis-server
sudo systemctl start redis-server

echo ""
echo "Checking Redis status:"
sudo systemctl status redis | grep Active

echo ""
echo "Testing Redis connection:"
echo "Expecting PONG response..."
redis-cli ping

echo ""
echo "✅ Installation Completed"

