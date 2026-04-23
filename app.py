from __future__ import annotations

import os
import zipfile
from io import BytesIO

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from src.config import load_config
from src.crawler import CATEGORY_MAP, crawl_category
from src.database import count_articles, fetch_articles, init_db, top_authors
from src.logger import configure_logging, get_logger


LOGGER = get_logger(__name__)


def ensure_paths(config_dir: str) -> None:
    os.makedirs(os.path.join(config_dir, "texts"), exist_ok=True)
    os.makedirs(os.path.join(config_dir, "images"), exist_ok=True)


def load_overrides() -> dict:
    overrides = {}
    for key in [
        "VNNEWS_DATA_DIR",
        "VNNEWS_DB_PATH",
        "VNNEWS_MAX_WORKERS",
        "VNNEWS_PAGE_TIMEOUT",
        "VNNEWS_REQUEST_TIMEOUT",
        "VNNEWS_USE_SELENIUM",
        "VNNEWS_HEADLESS",
        "VNNEWS_USER_AGENT",
    ]:
        if key in st.secrets:
            overrides[key] = st.secrets[key]
    return overrides


def get_export_csv(db_path: str) -> bytes:
    rows = fetch_articles(db_path)
    if not rows:
        return b""
    frame = pd.DataFrame([dict(row) for row in rows])
    return frame.to_csv(index=False).encode("utf-8")


def get_export_zip(data_dir: str, csv_bytes: bytes) -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        if csv_bytes:
            zip_file.writestr("articles.csv", csv_bytes)
        for root, _, files in os.walk(data_dir):
            for file_name in files:
                if file_name.endswith(".db"):
                    continue
                full_path = os.path.join(root, file_name)
                arc_name = os.path.relpath(full_path, data_dir)
                zip_file.write(full_path, arc_name)
    buffer.seek(0)
    return buffer.read()


def main() -> None:
    st.set_page_config(page_title="VietnamNet Data Hub", layout="wide")
    st.title("VietnamNet News Data Hub")

    configure_logging("INFO")
    load_dotenv()
    overrides = load_overrides()
    config = load_config(overrides)

    ensure_paths(config.data_dir)
    init_db(config.db_path)

    with st.sidebar:
        st.header("Crawler Settings")
        pages = st.number_input("Pages to crawl", min_value=1, max_value=50, value=3)
        category = st.selectbox("Category", list(CATEGORY_MAP.keys()), index=0)
        start = st.button("Start Crawling", type="primary")

    if start:
        progress = st.progress(0, text="Starting crawl...")
        try:
            processed = crawl_category(
                category_label=category,
                pages=int(pages),
                config=config,
                progress_callback=lambda cur, total: progress.progress(
                    cur / total, text=f"Listing pages {cur}/{total}"
                ),
            )
            progress.progress(1.0, text="Crawling complete")
            st.success(f"Crawled {processed} articles.")
        except Exception as exc:
            LOGGER.exception("crawl_failed", extra={"error": exc})
            st.error("Crawling failed. Check logs for details.")

    st.subheader("Data Statistics")
    total = count_articles(config.db_path)
    authors = top_authors(config.db_path)
    stats_cols = st.columns(2)
    stats_cols[0].metric("Total Articles", total)
    if authors:
        stats_cols[1].metric("Top Author", authors[0]["author"])

    if authors:
        author_frame = pd.DataFrame([dict(row) for row in authors])
        st.dataframe(author_frame, use_container_width=True)

    st.subheader("Data Explorer")
    filter_field = st.selectbox("Filter field", ["title", "author"], index=0)
    keyword = st.text_input("Search keyword")
    rows = fetch_articles(config.db_path, keyword=keyword, field=filter_field)
    if rows:
        st.dataframe(pd.DataFrame([dict(row) for row in rows]), use_container_width=True)
    else:
        st.info("No articles found.")

    st.subheader("Image Gallery")
    if rows:
        image_rows = [row for row in rows if row["image_path"]]
        if image_rows:
            cols = st.columns(4)
            for idx, row in enumerate(image_rows[:24]):
                with cols[idx % 4]:
                    st.image(row["image_path"], caption=row["title"], use_column_width=True)
        else:
            st.warning("No images available yet.")

    st.subheader("Export Center")
    csv_bytes = get_export_csv(config.db_path)
    if csv_bytes:
        st.download_button(
            "Download CSV",
            data=csv_bytes,
            file_name="vn_news.csv",
            mime="text/csv",
        )
        zip_bytes = get_export_zip(config.data_dir, csv_bytes)
        st.download_button(
            "Download ZIP (texts + images)",
            data=zip_bytes,
            file_name="vn_news_assets.zip",
            mime="application/zip",
        )
    else:
        st.info("No data to export.")


if __name__ == "__main__":
    main()
