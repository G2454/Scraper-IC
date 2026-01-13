from scrapers.newsScraper import parse_g1, parse_infomoney, parse_bbc
from scrapers.financeScraper import fetch_prices
import logging
import time
import re

DEFAULT_INTERVAL = 60*5 
CRON_PATH = "/etc/cron.d/scraper-cron"

logging.basicConfig(level=logging.INFO)


def get_interval_from_cron(path=CRON_PATH):
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "/app/run_all.py" in line or "run_all.py" in line:
                    parts = re.split(r"\s+", line)
                    if len(parts) < 6:
                        continue
                    minute_field = parts[0]
                    m = re.match(r"^\*/(\d+)$", minute_field)
                    if m:
                        return int(m.group(1)) * 60
                    if minute_field == "*":
                        return 60
                    logging.warning(f"Unsupported cron minute field '{minute_field}', using default interval")
                    return DEFAULT_INTERVAL
    except Exception as e:
        logging.warning(f"Could not read cron file {path}: {e}")
    return DEFAULT_INTERVAL


if __name__ == "__main__":
    logging.info("Iniciando coleta diária (modo persistente)")

    SCRAPE_INTERVAL = get_interval_from_cron()
    logging.info(f"Usando SCRAPE_INTERVAL={SCRAPE_INTERVAL} segundos")

    while True:
        try:
            parse_g1(limit=50)
            parse_infomoney(limit=30)
            parse_bbc(limit=30)

            fetch_prices()

            logging.info("Coleta diária finalizada")

        except Exception:
            logging.exception("Erro durante a coleta")

        logging.info(f"Aguardando {SCRAPE_INTERVAL} segundos até a próxima execução")
        time.sleep(SCRAPE_INTERVAL)
