#!/bin/bash
# Script to reset PostgreSQL user password for 'vaishnavi' to 'linux'

# Check if psql command is available
if ! command -v psql &> /dev/null
then
    echo "psql could not be found. Please install PostgreSQL client tools."
    exit 1
fi

# Prompt for PostgreSQL superuser (default: postgres)
read -p "Enter PostgreSQL superuser name (default: postgres): " PG_SUPERUSER
PG_SUPERUSER=\${PG_SUPERUSER:-postgres}

# Prompt for PostgreSQL host (default: localhost)
read -p "Enter PostgreSQL host (default: localhost): " PG_HOST
PG_HOST=\${PG_HOST:-localhost}

# Prompt for PostgreSQL port (default: 5432)
read -p "Enter PostgreSQL port (default: 5432): " PG_PORT
PG_PORT=\${PG_PORT:-5432}

echo "You will be prompted for the password of the superuser '\$PG_SUPERUSER' to execute the command."

# Execute the ALTER USER command
psql -U "\$PG_SUPERUSER" -h "\$PG_HOST" -p "\$PG_PORT" -d postgres -c "ALTER USER vaishnavi WITH PASSWORD 'linux';"

if [ \$? -eq 0 ]; then
    echo "Password for user 'vaishnavi' has been reset to 'linux'."
else
