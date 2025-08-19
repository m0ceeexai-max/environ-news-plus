#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Build the static site from RSS data + Jinja2 templates.

- Reads feeds.yml (list of categories and their sources)
- Downloads/normalizes items (title/link/source/date/summary)
- Renders:
    - index.html      (home + all categories summary)
    - <category>.html (environment/water/wastewater/tenders/oil_gas_petrochem)
    - crawler.html    (tools page for “search tenders”)
- Copies templates/styles.css to output
"""

from __future__ import annotations

import datetime as dt
import html
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Iterable

import yaml
import feedparser
from jinja2 import Environment, FileSystemLoader, select_autoescape

# ----------------------------
# Paths
# ----------------------------
ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"
SITE_DIR = ROOT / "site"          # build output
OUT = SITE_DIR                    # alias (برای راحتی)

# ----------------------------
# Config / constants
# ----------------------------

@dataclass
class SiteConfig:
    site_name: str = "Environ News+"
    tz: str = "UTC"

DEFAULT_NAV = [
    {"key": "environment",       "label": "محیط‌زیست"},
    {"key": "water",             "label": "آب"},
    {"key": "wastewater",        "label": "فاضلاب"},
    {"key": "oil_gas_petrochem", "label": "نفت/گاز/پتروشیمی"},
    {"key": "tenders",           "label": "مناقصه‌ها"},
]

# کلید قالب به نام فایل قالب در فولدر templates
PAGE_TEMPLATES = {
    "index": "index.html",
    "environment": "environment.html",
    "water": "water.html",
    "wastewater": "wastewater.html",
    "tenders": "tenders.html",
    "oil_gas_petrochem": "oil_gas_petrochem.html",
    "crawler": "crawler.html",
}

# ----------------------------
# Utilities
# ----------------------------

def load_config() -> SiteConfig:
    cfg_path = ROOT / "config_site.json"
    if cfg_path.exists():
        try:
            import json
            data = json.loads(cfg_path.read_text(encoding="utf-8"))
            return SiteConfig(**{**asdict(SiteConfig()), **data})
        except Exception:
            # اگر خراب بود با پیش‌فرض ادامه بده
            pass
    return SiteConfig()

def load_feeds() -> Dict:
    feeds_path = ROOT / "feeds.yml"
    data = yaml.safe_load(feeds_path.read_text(encoding="utf-8"))
    return data or {}

def parse_date(entry) -> dt.datetime:
    # تلاش برای گرفتن تاریخ از entry
    # fallback = حال حاضر
    try:
        if getattr(entry, "published_parsed", None):
            return dt.datetime.fromtimestamp(
                dt.datetime(*entry.published_parsed[:6]).timestamp(), tz=dt.timezone.utc
            )
        if getattr(entry, "updated_parsed", None):
            return dt.datetime.fromtimestamp(
                dt.datetime(*entry.updated_parsed[:6]).timestamp(), tz=dt.timezone.utc
            )
    except Exception:
        pass
    return dt.datetime.now(dt.timezone.utc)

def clean_text(s: str) -> str:
    if not s:
        return ""
    s = html.unescape(s)
    # حذف تگ‌های خیلی ساده
    s = re.sub(r"<[^>]+>", "", s)
    return s.strip()

@dataclass
class Item:
    title: str
    link: str
    source: str
    summary: str
    published_dt: dt.datetime
    category: str

def fetch_source(url: str) -> Iterable[Item]:
    fp = feedparser.parse(url)
    src_title = fp.feed.get("title") or url
    for e in fp.entries:
        yield Item(
            title=clean_text(e.get("title", "")) or "(no title)",
            link=e.get("link", url),
            source=clean_text(src_title),
            summary=clean_text(e.get("summary", ""))[:400],
            published_dt=parse_date(e),
            category="",  # بعداً پر می‌کنیم
        )

def aggregate(cfg: SiteConfig) -> Dict[str, List[Item]]:
    feeds = load_feeds()
    pages: Dict[str, List[Item]] = {
        "environment": [],
        "water": [],
        "wastewater": [],
        "tenders": [],
        "oil_gas_petrochem": [],
    }

    # feeds.yml انتظار: هر کلید یک لیست از URL ها
    for key in pages.keys():
        urls = feeds.get(key, []) or []
        for u in urls:
            try:
                for it in fetch_source(u):
                    it.category = key
                    pages[key].append(it)
            except Exception:
                # اگر فید مشکل داشت، رد می‌کنیم
                pass

        # مرتب‌سازی نزولی بر اساس زمان
        pages[key].sort(key=lambda x: x.published_dt, reverse=True)

    return pages

# ----------------------------
# Rendering
# ----------------------------

def build_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=select_autoescape(enabled_extensions=("html",)),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    return env

def site_context(cfg: SiteConfig, pages: Dict[str, List[Item]]) -> Dict:
    # ناوبری بر اساس DEFAULT_NAV
    nav = []
    for n in DEFAULT_NAV:
        href = f"{n['key']}.html"
        nav.append({**n, "href": href})

    return {
        "site": {
            "name": cfg.site_name,
            "nav": nav,
        }
    }

def render(pages: Dict[str, List[Item]]) -> None:
    SITE_DIR.mkdir(parents=True, exist_ok=True)

    env = build_env()
    cfg = load_config()
    ctx_site = site_context(cfg, pages)

    # ---------- Index ----------
    tpl = env.get_template(PAGE_TEMPLATES["index"])
    all_items: List[Item] = []
    for k, lst in pages.items():
        all_items.extend(lst)
    all_items.sort(key=lambda x: x.published_dt, reverse=True)

    html_index = tpl.render(
        site=ctx_site["site"],
        site_title="home",
        updated_at=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        pages=pages,
        items=all_items[:250],
    )
    (OUT / "index.html").write_text(html_index, encoding="utf-8")

    # ---------- Category pages ----------
    for key in pages.keys():
        tpl_page = env.get_template(PAGE_TEMPLATES[key])
        html_page = tpl_page.render(
            site=ctx_site["site"],
            page_title=key,
            items=pages[key],
            updated_at=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        )
        (OUT / f"{key}.html").write_text(html_page, encoding="utf-8")

    # ---------- Crawler page ----------
    tpl_crawler = env.get_template(PAGE_TEMPLATES["crawler"])
    html_crawler = tpl_crawler.render(
        site=ctx_site["site"],
        page_title="crawler",
    )
    (OUT / "crawler.html").write_text(html_crawler, encoding="utf-8")

    # ---------- Copy styles.css if present ----------
    css = TEMPLATES / "styles.css"
    if css.exists():
        (OUT / "styles.css").write_text(css.read_text(encoding="utf-8"), encoding="utf-8")

    print("[OK] render finished")

# ----------------------------
# Main
# ----------------------------

def main():
    cfg = load_config()
    pages = aggregate(cfg)
    render(pages)
    print("[OK] build finished, wrote to site/")

if __name__ == "__main__":
    main()
