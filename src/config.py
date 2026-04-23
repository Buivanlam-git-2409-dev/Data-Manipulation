from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Config:
    data_dir: str
    db_path: str
    max_workers: int
    page_timeout: int
    request_timeout: int
    use_selenium: bool
    headless: bool
    user_agent: str


DEFAULTS = {
    "VNNEWS_DATA_DIR": "./data",
    "VNNEWS_DB_PATH": "./data/vn_news.db",
    "VNNEWS_MAX_WORKERS": "8",
    "VNNEWS_PAGE_TIMEOUT": "25",
    "VNNEWS_REQUEST_TIMEOUT": "20",
    "VNNEWS_USE_SELENIUM": "true",
    "VNNEWS_HEADLESS": "true",
    "VNNEWS_USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
}


def _get_setting(name: str, overrides: dict | None) -> str:
    if overrides and name in overrides:
        return str(overrides[name])
    return os.getenv(name, DEFAULTS.get(name, ""))


def load_config(overrides: dict | None = None) -> Config:
    data_dir = _get_setting("VNNEWS_DATA_DIR", overrides)
    db_path = _get_setting("VNNEWS_DB_PATH", overrides)
    max_workers = int(_get_setting("VNNEWS_MAX_WORKERS", overrides))
    page_timeout = int(_get_setting("VNNEWS_PAGE_TIMEOUT", overrides))
    request_timeout = int(_get_setting("VNNEWS_REQUEST_TIMEOUT", overrides))
    use_selenium = _get_setting("VNNEWS_USE_SELENIUM", overrides).lower() == "true"
    headless = _get_setting("VNNEWS_HEADLESS", overrides).lower() == "true"
    user_agent = _get_setting("VNNEWS_USER_AGENT", overrides)

    return Config(
        data_dir=data_dir,
        db_path=db_path,
        max_workers=max_workers,
        page_timeout=page_timeout,
        request_timeout=request_timeout,
        use_selenium=use_selenium,
        headless=headless,
        user_agent=user_agent,
    )
