#!/bin/bash
set -e

echo "Iniciando container e serviço cron..."
touch /var/log/cron.log

# Ensure DB directory and file exist so scrapers can write
mkdir -p /app/db
touch /app/db/data.db

# Run once at startup if available (helps testing / immediate run)
if [ -f /app/run_all.py ]; then
	echo "Executando run_all.py no startup..." >> /var/log/cron.log 2>&1
	/usr/local/bin/python /app/run_all.py >> /var/log/cron.log 2>&1 || true
fi

# Start cron in background so we can tail the log to stdout (visible in `docker logs`)
cron

# Tail cron log to container stdout so Docker captures scraper logs
tail -n +1 -F /var/log/cron.log