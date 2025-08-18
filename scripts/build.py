#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
import re
import sys

import yaml
import feedparser
from jinja2 import Environment, FileSystemLoader, select_autoescape

# --- Paths
ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"
OUT = ROOT / "site"

# --- Site meta passed to templates
SITE = {
    "title": "Environ News +",
    "description": "گردآوری خودکار اخبار محیط‌زیست، آب، فاضلاب، نفت و گاز و مناقصه‌ها",
    "base_url": "",  # اگر دامنه اختصاصی/آدرس pages داری، اینجا بگذار
    "nav": [
        {"key": "environment", "label": "محیط‌زیست"},
        {"key": "water", "label": "آب"},
        {"key": "wastewater", "label": "فاضلاب"},
        {"key": "oil_gas_petrochem", "label": "نفت/گاز/پتروشیمی"},
        {"key": "tenders", "label": "مناقصه‌ها"},
    ],
}

# --- Helpers
def clean_html(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)  # strip tags
    text = re.sub(r"\s+", " ", text).strip()
    return text[:300]

def parse_date(entry):
    dt = None
    for key in ("published_parsed", "updated_parsed"):
        if getattr(entry, key, None):
            try:
                dt = datetime(*getattr(entry, key)[:6], tzinfo=timezone.utc)
                break
            except Exception:
                pass
    return dt or datetime.now(timezone.utc)

def fetch_feed(url, title_hint=""):
    parsed = feedparser.parse(
        url,
        request_headers={
            "User-Agent": "EnvironNewsBot/1.0 (+https://github.com/)",
            "Accept": "application/rss+xml, application/atom+xml;q=0.9, */*;q=0.8",
        },
    )
    if parsed.bozo:
        print(f"[WARN] Problem parsing: {url} -> {parsed.bozo_exception}", file=sys.stderr)

    items = []
    for e in parsed.entries:
        items.append({
            "title": (e.get("title") or "").strip(),
            "link": (e.get("link") or "").strip(),
            "summary": clean_html(e.get("summary") or e.get("description") or ""),
            "published_dt": parse_date(e),
            "source": (parsed.feed.get("title") or title_hint).strip(),
        })
    return items

def load_config():
    cfg_path = ROOT / "feeds.yaml"
    with cfg_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def aggregate(cfg):
    all_items_by_cat = {}
    feeds_cfg = (cfg.get("feeds") or {})
    for cat, feeds in feeds_cfg.items():
        bucket = []
        for f in feeds or []:
            url = f.get("url")
            title = f.get("title", "")
            if not url:
                continue
            print(f"[INFO] Fetch {cat}: {url}")
            try:
                bucket.extend(fetch_feed(url, title_hint=title))
            except Exception as ex:
                print(f"[ERROR] fetch failed: {url} -> {ex}", file=sys.stderr)

        # de-dup + sort
        seen = set()
        uniq = []
        for it in bucket:
            if not it["link"] or it["link"] in seen:
                continue
            seen.add(it["link"])
            uniq.append(it)

        uniq.sort(key=lambda x: x["published_dt"], reverse=True)
        # prettify date string for templates
        for it in uniq:
            it["published"] = it["published_dt"].strftime("%Y-%m-%d %H:%M UTC")

        all_items_by_cat[cat] = uniq[:150]
        print(f"[DONE] {cat}: {len(all_items_by_cat[cat])} items")

    return all_items_by_cat

def render(pages):
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=select_autoescape(["html"]),
    )
    OUT.mkdir(exist_ok=True)

    updated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # category pages
    for cat, items in pages.items():
        tpl_name = f"{cat}.html"
        if (TEMPLATES / tpl_name).exists():
            html = env.get_template(tpl_name).render(
                site=SITE,
                page_title=cat,
                items=items,
                updated_at=updated_at,
                pages=pages,
            )
            (OUT / tpl_name).write_text(html, encoding="utf-8")
        else:
            print(f"[WARN] template missing: {tpl_name}", file=sys.stderr)

    # index page (optional)
    if (TEMPLATES / "index.html").exists():
        all_items = []
        for v in pages.values():
            all_items.extend(v)
        all_items.sort(key=lambda x: x["published_dt"], reverse=True)
        html = env.get_template("index.html").render(
            site=SITE,
            page_title="home",
            items=all_items[:250],
            updated_at=updated_at,
            pages=pages,
        )
        (OUT / "index.html").write_text(html, encoding="utf-8")

    # copy styles.css if present
    css = TEMPLATES / "styles.css"
    if css.exists():
        (OUT / "styles.css").write_text(css.read_text(encoding="utf-8"), encoding="utf-8")

    print("[OK] render finished")

def main():
    cfg = load_config()
    pages = aggregate(cfg)
    render(pages)
    print("[OK] build finished, wrote to site/")

if __name__ == "__main__":
    main()
