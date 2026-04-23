from __future__ import annotations

import hashlib
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from tqdm import tqdm

from .config import Config
from .database import ArticleRecord, upsert_article
from .logger import get_logger
from .processor import clean_text


LOGGER = get_logger(__name__)

CATEGORY_MAP = {
    "Thoi su": "thoi-su",
    "The gioi": "the-gioi",
    "Kinh doanh": "kinh-doanh",
    "Giai tri": "giai-tri",
    "The thao": "the-thao",
    "Giao duc": "giao-duc",
    "Suc khoe": "suc-khoe",
}


def create_driver(config: Config) -> webdriver.Chrome:
    options = Options()
    if config.headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(f"--user-agent={config.user_agent}")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def fetch_html_with_fallback(
    url: str,
    driver: webdriver.Chrome | None,
    config: Config,
) -> str | None:
    if driver:
        try:
            driver.set_page_load_timeout(config.page_timeout)
            driver.get(url)
            WebDriverWait(driver, config.page_timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            return driver.page_source
        except Exception as exc:
            LOGGER.warning("selenium_fetch_failed", extra={"url": url, "error": exc})
            time.sleep(1)

    try:
        headers = {"User-Agent": config.user_agent}
        resp = requests.get(url, headers=headers, timeout=config.request_timeout)
        resp.raise_for_status()
        return resp.text
    except Exception as exc:
        LOGGER.error("request_fetch_failed", extra={"url": url, "error": exc})
        return None


def parse_listing_urls(page_html: str) -> list[str]:
    soup = BeautifulSoup(page_html, "html.parser")
    selectors = [
        "div.topStory-15nd div div a",
        "h3 a",
        "a.vnn-title",
    ]
    urls: list[str] = []
    for selector in selectors:
        for tag in soup.select(selector):
            href = tag.get("href")
            if href:
                urls.append(href)
    return list(dict.fromkeys(urls))


def parse_article(url: str, html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    content = soup.select_one("div.content-detail") or soup.select_one("article")
    if not content:
        return {}
    if content.select_one("div.video-detail"):
        return {}

    title_tag = content.find("h1") or soup.find("h1")
    abstract_tag = content.find("h2")
    author_tag = content.select_one("span.name")
    time_tag = content.find("time") or soup.find("time")

    title = title_tag.get_text(strip=True) if title_tag else ""
    abstract = abstract_tag.get_text(strip=True) if abstract_tag else ""
    author = author_tag.get_text(strip=True) if author_tag else ""
    published = time_tag.get_text(strip=True) if time_tag else ""

    paragraphs = content.select("div.maincontent.main-content p")
    if not paragraphs:
        paragraphs = content.find_all("p")
    paragraph_text = "\n\n".join(
        [p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)]
    )

    image_url = ""
    og_image = soup.find("meta", property="og:image")
    if og_image and og_image.get("content"):
        image_url = og_image.get("content")

    return {
        "title": title,
        "abstract": abstract,
        "author": author,
        "published": published,
        "content": paragraph_text,
        "image_url": image_url,
        "url": url,
    }


def save_text(content: str, text_dir: str, url: str) -> str:
    os.makedirs(text_dir, exist_ok=True)
    name = hashlib.md5(url.encode("utf-8")).hexdigest() + ".txt"
    path = os.path.join(text_dir, name)
    with open(path, "w", encoding="utf-8") as file:
        file.write(content)
    return path


def download_image(image_url: str, image_dir: str, url: str, config: Config) -> str:
    if not image_url:
        return ""
    os.makedirs(image_dir, exist_ok=True)
    name = hashlib.md5(url.encode("utf-8")).hexdigest() + ".jpg"
    path = os.path.join(image_dir, name)
    try:
        headers = {"User-Agent": config.user_agent}
        resp = requests.get(image_url, headers=headers, timeout=config.request_timeout)
        resp.raise_for_status()
        with open(path, "wb") as file:
            file.write(resp.content)
        return path
    except Exception as exc:
        LOGGER.warning("image_download_failed", extra={"url": image_url, "error": exc})
        return ""


def process_article(
    url: str,
    config: Config,
) -> ArticleRecord | None:
    html = fetch_html_with_fallback(url, None, config)
    if not html:
        return None
    payload = parse_article(url, html)
    if not payload or not payload.get("content"):
        return None

    text_dir = os.path.join(config.data_dir, "texts")
    image_dir = os.path.join(config.data_dir, "images")
    cleaned_text = clean_text(payload["content"])
    content_path = save_text(cleaned_text, text_dir, url)
    image_path = download_image(payload.get("image_url", ""), image_dir, url, config)

    return ArticleRecord(
        title=payload.get("title", ""),
        abstract=payload.get("abstract", ""),
        author=payload.get("author", ""),
        url=url,
        content_path=content_path,
        image_path=image_path,
        published_date=payload.get("published", ""),
    )


def crawl_category(
    category_label: str,
    pages: int,
    config: Config,
    progress_callback: Callable[[int, int], None] | None = None,
) -> int:
    category_slug = CATEGORY_MAP.get(category_label, "thoi-su")
    driver = create_driver(config) if config.use_selenium else None
    all_urls: list[str] = []

    try:
        for idx in tqdm(range(pages), desc="Listing pages"):
            list_url = f"https://vietnamnet.vn/{category_slug}-page{idx}"
            html = fetch_html_with_fallback(list_url, driver, config)
            if not html:
                continue
            urls = parse_listing_urls(html)
            all_urls.extend(urljoin("https://vietnamnet.vn", url) for url in urls)
            if progress_callback:
                progress_callback(idx + 1, pages)
    finally:
        if driver:
            driver.quit()

    deduped_urls = list(dict.fromkeys(all_urls))
    if not deduped_urls:
        return 0

    processed = 0
    with ThreadPoolExecutor(max_workers=config.max_workers) as executor:
        future_map = {
            executor.submit(process_article, url, config): url for url in deduped_urls
        }
        for future in tqdm(as_completed(future_map), total=len(future_map), desc="Articles"):
            record = future.result()
            if record:
                upsert_article(config.db_path, record)
                processed += 1

    return processed
