#!/bin/bash

# Define user and list of databases
DB_USER="kubesage"
DB_PASSWORD="linux"
DB_HOST="localhost"
DB_PORT="5432"

# List of databases to create
DATABASES=("k_remediation_db" "k_user_db" "k_kubeconfig_db" "k_security_db" "k_chat_lang_db")

# Create the PostgreSQL user with CREATEDB privilege
echo "Creating PostgreSQL user '$DB_USER'..."
sudo -u postgres psql <<EOF
DO \$\$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$DB_USER') THEN
      CREATE USER $DB_USER WITH ENCRYPTED PASSWORD '$DB_PASSWORD' CREATEDB;
   END IF;
END \$\$;
EOF

echo "User '$DB_USER' created successfully!"

# Loop through each database and create it
for DB_NAME in "${DATABASES[@]}"
do
    echo "Creating database '$DB_NAME'..."
    sudo -u postgres psql <<EOF
    CREATE DATABASE $DB_NAME OWNER $DB_USER;
    GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
EOF
    echo "Database '$DB_NAME' created successfully!"
done

echo "All databases have been created successfully!"
