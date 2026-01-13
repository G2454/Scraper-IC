FROM python:3.11-slim

# Instala cron
RUN apt-get update && apt-get install -y cron && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copia projeto (use build context root when building)
COPY . /app

# Copia crontab
COPY docker/crontab /etc/cron.d/scraper-cron

# Permissões corretas
RUN chmod 0644 /etc/cron.d/scraper-cron

# Instala dependências
RUN pip install --no-cache-dir \
    requests beautifulsoup4 yfinance pandas numpy lxml

# Log do cron
RUN touch /var/log/cron.log

# Entry point
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]