import requests
import sqlite3
import time
from bs4 import BeautifulSoup
import os
from datetime import datetime
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NewsScheduler")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.abspath(os.path.join(BASE_DIR, "..", "db", "data.db"))
print("Usando banco em:", DB)  # Debug

def test_db_connection():
    try:
        conn = sqlite3.connect(DB, timeout=50)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print("Tabelas no banco:", tables)
        conn.close()
    except sqlite3.Error as e:
        print(f"Erro ao conectar ao banco de dados: {e}")

def save_article(url, title, content, published, source):
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
            try:
                cur.execute(
                    """
                    INSERT INTO news (url, title, content, source, published_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (url, title, content, source, published),
                )
                conn.commit()
                print(f"OK Inserido: {url}")
                return
            except sqlite3.IntegrityError:
                print(f"X Duplicado ignorado: {url}")
                return
            finally:
                conn.close()

        except sqlite3.OperationalError as e:
            logger.warning(f"SQLite operational error on save_article (attempt {attempt}): {e}")
            if attempt == attempts:
                logger.error(f"Failed to save article after {attempts} attempts: {url}")
                return
            time.sleep(delay)
            delay *= 2

def extract_g1_date(soup):

    tag_time = soup.find("time")
    if tag_time and tag_time.get("datetime"):
        return tag_time["datetime"]

    candidates = soup.find_all(class_="content-publication-data")
    for c in candidates:
        text = c.get_text(" ", strip=True)
        dt = parse_g1_date_text(text)
        if dt:
            return dt

    text = soup.get_text(" ", strip=True)
    dt = parse_g1_date_text(text)
    if dt:
        return dt

    return None

def parse_g1_date_text(text):

    patterns = [
        r"(\d{2}/\d{2}/\d{4})\s+(\d{2}h\d{2})",
        r"(\d{2}/\d{2}/\d{4})",  # data simples
    ]

    for p in patterns:
        match = re.search(p, text)
        if match:
            try:
                if len(match.groups()) == 2:
                    date_str, time_str = match.groups()
                    time_str = time_str.replace("h", ":")
                    dt = datetime.strptime(date_str + " " + time_str, "%d/%m/%Y %H:%M")
                else:
                    date_str = match.group(1)
                    dt = datetime.strptime(date_str, "%d/%m/%Y")

                return dt.isoformat()
            except:
                pass

    return None

def article_exists(url):
    conn = sqlite3.connect(DB, timeout=50)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
    except Exception:
        pass
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM news WHERE url = ? LIMIT 1", (url,))
    exists = cur.fetchone() is not None
    conn.close()
    return exists


def parse_g1(limit):
    import random
    import time

    base_url = "https://g1.globo.com/economia/negocios/"
    current_url = base_url
    collected = 0
    visited_pages = set()
    MIN_CONTENT_LENGTH = 200

    logger.info(f"Iniciando G1 — coletar até {limit} notícias novas")

    while current_url and collected < limit:
        if current_url in visited_pages:
            break
        visited_pages.add(current_url)

        logger.info(f"Acessando página: {current_url}")
        r = requests.get(current_url, timeout=10)
        soup = BeautifulSoup(r.content, "html.parser")

        links = [
            a.get("href")
            for a in soup.select("a[href]")
            if "/economia/" in (a.get("href") or "")
        ]

        unique_links = list(dict.fromkeys(links))

        for link in unique_links:
            if collected >= limit:
                break

            if article_exists(link):
                logger.info(f"Já existe no banco, pulando: {link}")
                continue

            try:
                r2 = requests.get(link, timeout=10)
                s2 = BeautifulSoup(r2.content, "html.parser")

                title_el = s2.find("h1")
                paragraphs = s2.select("article p")

                if not title_el or not paragraphs:
                    continue

                content = "\n".join(p.get_text(strip=True) for p in paragraphs)

                if not content or len(content.strip()) < MIN_CONTENT_LENGTH:
                    continue

                published = extract_g1_date(s2)

                save_article(
                    link,
                    title_el.get_text(strip=True),
                    content,
                    published,
                    source="g1"
                )

                collected += 1
                logger.info(f"Coletadas {collected}/{limit}")
                time.sleep(1)

            except Exception as e:
                logger.warning(f"Erro ao processar {link}: {e}")

        load_more = soup.find("div", class_="load-more")
        if load_more and load_more.find("a"):
            delay = random.uniform(5, 10)
            time.sleep(delay)
            current_url = load_more.find("a").get("href")
        else:
            break

    logger.info(f"G1 — execução finalizada, novas notícias: {collected}")



def parse_infomoney(limit):
    url = "https://www.infomoney.com.br/mercados/"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    logger.info("Scraping InfoMoney (primeira carga apenas)")
    r = requests.get(url, headers=headers, timeout=10)
    soup = BeautifulSoup(r.content, "html.parser")

    links = [
        a.get("href")
        for a in soup.select("a[href^='https://www.infomoney.com.br/mercados/']")
    ]

    unique_links = list(dict.fromkeys(links))
    collected = 0

    for link in unique_links:
        if collected >= limit:
            break

        try:
            r2 = requests.get(link, headers=headers, timeout=10)
            s2 = BeautifulSoup(r2.content, "html.parser")

            title_el = s2.find("h1")
            paragraphs = s2.find_all("p")

            if not title_el or not paragraphs:
                continue

            content = "\n".join(p.get_text(strip=True) for p in paragraphs)
            if len(content) < 200:
                continue

            published = None
            time_tag = s2.find("time")
            if time_tag and time_tag.get("datetime"):
                published = time_tag["datetime"]

            save_article(link, title_el.text.strip(), content, published, "infomoney")
            collected += 1

        except Exception as e:
            logger.warning(f"Erro InfoMoney {link}: {e}")

    logger.info(f"InfoMoney coletado: {collected}")


def extract_bbc_content_from_next_data(data):
    page_props = data.get("props", {}).get("pageProps", {})

    blocks = [
        v for v in page_props.values()
        if isinstance(v, dict) and "contents" in v
    ]

    if not blocks:
        return None, None

    title = None
    paragraphs = []

    for c in blocks[0]["contents"]:
        if c.get("type") == "headline":
            title = c["model"]["blocks"][0]["model"]["text"]

        elif c.get("type") == "text":
            paragraphs.append(
                c["model"]["blocks"][0]["model"]["text"]
            )

    content = "\n".join(paragraphs).strip()

    if not title or not content:
        return None, None

    return title, content

def parse_bbc_pubdate(pubdate_text):
    """
    Converte datas do RSS da BBC, por exemplo:
    'Tue, 05 Jan 2026 14:32:00 GMT'
    para 'YYYY-MM-DD'
    """
    if not pubdate_text:
        return None

    try:
        dt = datetime.strptime(pubdate_text.strip(), "%a, %d %b %Y %H:%M:%S %Z")
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return None

def parse_bbc(limit):
    import requests
    import time
    import xml.etree.ElementTree as ET
    from bs4 import BeautifulSoup

    RSS_URL = "https://feeds.bbci.co.uk/portuguese/topics/economia/rss.xml"
    HEADERS = {"User-Agent": "Mozilla/5.0"}
    MIN_CONTENT_LENGTH = 150
    REQUEST_DELAY = 1

    collected = 0

    logger.info("Scraping BBC Português via RSS (Economia)")

    try:
        rss_response = requests.get(RSS_URL, headers=HEADERS, timeout=15)
        rss_response.raise_for_status()
        root = ET.fromstring(rss_response.content)
    except Exception as e:
        logger.error(f"Erro ao acessar RSS BBC: {e}")
        return

    items = root.findall(".//item")
    logger.info(f"RSS BBC retornou {len(items)} itens")

    for item in items:
        if collected >= limit:
            break

        link = item.findtext("link")
        raw_published = item.findtext("pubDate")
        published = parse_bbc_pubdate(raw_published)

        if not link:
            continue

        link = link.strip()

        if article_exists(link):
            logger.info(f"Duplicado ignorado: {link}")
            continue

        try:
            logger.info(f"Fetching BBC link: {link}")
            r = requests.get(link, headers=HEADERS, timeout=15)
            logger.info(f"Fetched BBC link: {link} (status={getattr(r, 'status_code', 'n/a')})")
            soup = BeautifulSoup(r.content, "html.parser")

            title_el = soup.find("h1")
            paragraphs = soup.find_all("p")

            if not title_el or not paragraphs:
                continue

            content = "\n".join(p.get_text(strip=True) for p in paragraphs)

            if len(content) < MIN_CONTENT_LENGTH:
                logger.info(f"Conteúdo curto ignorado: {link}")
                continue

            save_article(
                link,
                title_el.get_text(strip=True),
                content,
                published,
                source="bbc"
            )

            collected += 1
            logger.info(f"BBC coletado: {collected}/{limit}")
            time.sleep(REQUEST_DELAY)

        except Exception as e:
            logger.warning(f"Erro BBC {link}: {e}")

    logger.info(f"BBC total coletado: {collected}")




    
    
    
    
    
    
    
