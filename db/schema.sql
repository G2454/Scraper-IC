CREATE TABLE IF NOT EXISTS news (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  url TEXT UNIQUE,
  title TEXT,
  content TEXT,
  source TEXT,
  published_at TIMESTAMP,
  scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE prices (
    ticker TEXT NOT NULL,
    dt TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER,
    PRIMARY KEY (ticker, dt)
);


CREATE TABLE IF NOT EXISTS sentiment (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  news_id INTEGER,
  score REAL,
  label TEXT,
  model TEXT,
  scored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(news_id) REFERENCES news(id)
);

CREATE INDEX IF NOT EXISTS idx_news_published ON news(published_at);
CREATE INDEX IF NOT EXISTS idx_prices_ticker_dt ON prices(ticker, dt);
