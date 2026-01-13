import yfinance as yf
import sqlite3
from datetime import datetime, timedelta
import time
import os
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PriceScraper")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.abspath(os.path.join(BASE_DIR, "..", "db", "data.db"))
print("Usando banco em:", DB)  # Debug

TICKERS = {
    "PETR3": "PETR3.SA",
    "ITUB3": "ITUB3.SA",
    "VALE3": "VALE3.SA",
    "ABEV3": "ABEV3.SA",
    "WEGE3": "WEGE3.SA"
}

START_DATE = "2024-01-01" 
REQUEST_DELAY = 1  


def save_price(ticker, dt, row):
    attempts = 5
    delay = 0.5
    for attempt in range(1, attempts + 1):
        try:
            conn = sqlite3.connect(DB, timeout=50)
            try:
                conn.execute("PRAGMA journal_mode=WAL;")
            except Exception:
                pass

            cur = conn.cursor()
            cur.execute("""
                INSERT OR IGNORE INTO prices
                (ticker, dt, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                ticker,
                dt,
                float(row["Open"]),
                float(row["High"]),
                float(row["Low"]),
                float(row["Close"]),
                int(row["Volume"])
            ))

            conn.commit()
            inserted = cur.rowcount == 1
            conn.close()
            return inserted

        except sqlite3.OperationalError as e:
            logger.warning(f"SQLite operational error (attempt {attempt}): {e}")
            if attempt == attempts:
                logger.error(f"Failed to save price for {ticker}")
                return False
            time.sleep(delay)
            delay *= 2

def get_last_date(ticker):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute(
        "SELECT MAX(dt) FROM prices WHERE ticker = ?",
        (ticker,)
    )
    result = cur.fetchone()[0]
    conn.close()
    return result


def fetch_prices():
    for ticker_b3, ticker_yahoo in TICKERS.items():
        logger.info(f"Coletando preços de {ticker_b3}")

        last_dt = get_last_date(ticker_b3)

        start_date = (
            datetime.fromisoformat(last_dt).date()
            if last_dt else
            datetime.fromisoformat(START_DATE).date()
        )

        while True:
            end_date = start_date + timedelta(days=90)

            df = yf.download(
                ticker_yahoo,
                start=start_date.isoformat(),
                end=end_date.isoformat(),
                progress=False
            )

            if df.empty:
                break

            df = df.head(50)

            inserted = 0
            for dt, row in df.iterrows():
                if save_price(
                    ticker_b3,
                    dt.to_pydatetime().isoformat(),
                    row
                ):
                    inserted += 1

            logger.info(
                f"{ticker_b3}: {inserted} novos registros "
                f"({start_date} → {end_date})"
            )

            last_saved = df.index.max().to_pydatetime().date()
            start_date = last_saved + timedelta(days=1)

            time.sleep(REQUEST_DELAY)


#
#if __name__ == "__main__":
#    fetch_prices()
#    logger.info("Coleta de preços finalizada")
