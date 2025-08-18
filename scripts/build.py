#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
import re
import sys

import yaml
import feedparser
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"
OUT = ROOT / "site"

def clean_html(text: str) -> str:
    if not text:
        return ""
    # حذف تگ‌ها و کوتاه‌سازی
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:300]

def parse_date(entry):
    # تلاش برای گرفتن تاریخ قابل مقایسه
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
    # یوزر ایجنت صریح؛ بعضی سایت‌ها بدون UA جواب نمی‌دهند
    parsed = feedparser.parse(url, request_headers={
        "User-Agent": "EnvironNewsBot/1.0 (+https://github.com/)",
        "Accept": "application/rss+xml, application/atom+xml;q=0.9, */*;q=0.8",
    })
    if parsed.bozo:
        print(f"[WARN] Problem parsing: {url} -> {parsed.bozo_exception}", file=sys.stderr)
    items = []
    for e in parsed.entries:
        items.append({
            "title": e.get("title", "").strip(),
            "link": e.get("link", "").strip(),
            "summary": clean_html(e.get("summary") or e.get("description") or ""),
            "published": parse_date(e).strftime("%Y-%m-%d %H:%M"),
            "source": (parsed.feed.get("title") or title_hint).strip(),
        })
    return items

def load_config():
    cfg_path = ROOT / "feeds.yaml"
    with cfg_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def aggregate(cfg):
    all_items_by_cat = {}
    for cat, feeds in (cfg.get("feeds") or {}).items():
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
        # حذف لینک‌های تکراری و مرتب‌سازی
        seen = set()
        uniq = []
        for it in bucket:
            if not it["link"] or it["link"] in seen:
                continue
            seen.add(it["link"])
            uniq.append(it)
        uniq.sort(key=lambda x: x["published"], reverse=True)
        all_items_by_cat[cat] = uniq[:120]  # سقف معقول
        print(f"[DONE] {cat}: {len(all_items_by_cat[cat])} items")
    return all_items_by_cat

def render(pages):
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=select_autoescape(["html"])
    )
    OUT.mkdir(exist_ok=True)
    # رندر صفحات دسته‌ها
    for cat, items in pages.items():
        tpl_name = f"{cat}.html"
        tpl_path = TEMPLATES / tpl_name
        if tpl_path.exists():
            html = env.get_template(tpl_name).render(items=items, updated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
            (OUT / tpl_name).write_text(html, encoding="utf-8")
        else:
            print(f"[WARN] template missing: {tpl_name}", file=sys.stderr)

    # رندر صفحه‌ی اصلی (اگر هست)
    index_tpl = TEMPLATES / "index.html"
    if index_tpl.exists():
        all_items = []
        for v in pages.values():
            all_items.extend(v)
        # کمی کوتاه‌تر برای صفحه‌ی اول
        all_items.sort(key=lambda x: x["published"], reverse=True)
        html = env.get_template("index.html").render(
            items=all_items[:200],
            pages=pages,
            updated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        )
        (OUT / "index.html").write_text(html, encoding="utf-8")

    # کپی استایل
    css = TEMPLATES / "styles.css"
    if css.exists():
        (OUT / "styles.css").write_text(css.read_text(encoding="utf-8"), encoding="utf-8")

def main():
    cfg = load_config()
    pages = aggregate(cfg)
    render(pages)
    print("[OK] build finished, wrote to site/")

if __name__ == "__main__":
    main()
