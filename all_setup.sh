#!/bin/bash

set -e  # Exit immediately if a command exits with non-zero status
set -o pipefail

echo "=============================="
echo " Updating system packages..."
echo "=============================="
sudo apt update && sudo apt upgrade -y

# Install Google Chrome
echo "=============================="
echo " Installing Google Chrome..."
echo "=============================="
wget -q -O google-chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt install -y ./google-chrome.deb
rm google-chrome.deb

# Install Node.js (latest version using NodeSource)
echo "=============================="
echo " Installing Node.js (latest)..."
echo "=============================="
curl -fsSL https://deb.nodesource.com/setup_current.x | sudo -E bash -
sudo apt install -y nodejs

# Install Visual Studio Code
echo "=============================="
echo " Installing Visual Studio Code..."
echo "=============================="
sudo apt update
sudo apt install wget gpg
wget -qO- https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > packages.microsoft.gpg
sudo install -o root -g root -m 644 packages.microsoft.gpg /usr/share/keyrings/
sudo sh -c 'echo "deb [arch=amd64 signed-by=/usr/share/keyrings/packages.microsoft.gpg] \
https://packages.microsoft.com/repos/code stable main" > /etc/apt/sources.list.d/vscode.list'
sudo apt update
sudo apt install code

# Install Helm
echo "=============================="
echo " Installing Helm..."
echo "=============================="
curl https://baltocdn.com/helm/signing.asc | sudo apt-key add -
sudo apt install -y apt-transport-https --no-install-recommends
echo "deb https://baltocdn.com/helm/stable/debian/ all main" | sudo tee /etc/apt/sources.list.d/helm-stable-debian.list
sudo apt update
sudo apt install -y helm

# Install kubectl (official apt repository method)
echo "=============================="
echo " Installing kubectl (via apt repo)..."
echo "=============================="
sudo apt update
curl -LO https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl

chmod +x ./kubectl

sudo mv ./kubectl /usr/local/bin/kubectl

# Check kubectl version
kubectl version --client


# latest version of k8sgpt
https://github.com/k8sgpt-ai/k8sgpt/releases/download/v0.4.1/k8sgpt_amd64.deb


# Install PostgreSQL
echo "=============================="
echo " Installing PostgreSQL..."
echo "=============================="
# Import the repository signing key
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
# Add PostgreSQL APT repository
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
# Install PostgreSQL
sudo apt update
sudo apt install -y postgresql postgresql-contrib

echo "=============================="
echo "✅ All installations completed successfully! 🎉"
echo "=============================="
