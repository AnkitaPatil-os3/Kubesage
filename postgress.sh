#!/bin/bash
#
sudo apt install postgresql postgresql-contrib -y

DB_USER="test"
DB_PASSWORD="linux"
DB_NAME="test"
POSTGRES_PORT=5432

# Ensure the script is run as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root."
   exit 1
fi

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo "PostgreSQL is not installed. Installing now..."
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        case "$ID" in
            ubuntu|debian)
                apt update && apt install -y postgresql
                ;;
            centos|fedora|rhel)
                yum install -y postgresql-server
                postgresql-setup initdb
                systemctl enable --now postgresql
                ;;
            suse|opensuse)
                zypper install -y postgresql-server
                systemctl enable --now postgresql
                ;;
            *)
                echo "Unsupported Linux distribution."
                exit 1
                ;;
        esac
    fi
fi

# Start PostgreSQL if not running
systemctl start postgresql 2>/dev/null || service postgresql start 2>/dev/null

# Ensure PostgreSQL is listening on port 5432
PG_CONF=$(sudo -i -u postgres psql -t -A -c "SHOW config_file;")
PG_HBA=$(sudo -i -u postgres psql -t -A -c "SHOW hba_file;")

# Update postgresql.conf to listen on all interfaces on port 5432
sed -i "s/^#listen_addresses =.*/listen_addresses = '*'/" "$PG_CONF"
sed -i "s/^#port =.*/port = $POSTGRES_PORT/" "$PG_CONF"

# Allow all incoming connections in pg_hba.conf
echo "host    all             all             0.0.0.0/0               md5" >> "$PG_HBA"
echo "host    all             all             ::/0                    md5" >> "$PG_HBA"

# Restart PostgreSQL to apply changes
systemctl restart postgresql 2>/dev/null || service postgresql restart 2>/dev/null

# Create PostgreSQL user and database
sudo -i -u postgres psql <<EOF
CREATE USER $DB_USER WITH ENCRYPTED PASSWORD '$DB_PASSWORD';
CREATE DATABASE $DB_NAME OWNER $DB_USER;
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
EOF

echo "PostgreSQL user and database created successfully."

# Create Linux user without setting a password
if ! id "$DB_USER" &>/dev/null; then
    useradd -m -s /bin/bash $DB_USER
    echo "Linux user $DB_USER created successfully (without password)."
else
    echo "Linux user $DB_USER already exists."
fi

echo "Setup completed successfully. PostgreSQL is running on port $POSTGRES_PORT."

