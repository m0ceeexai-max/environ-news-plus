#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
from datetime import datetime, timezone
import json, time, re
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
OUT = DATA / "crawler.json"

KEYWORDS = [
    "مناقصه توربو بلوئر",
    "میکسر مستغرق",
    "دکانتر آبگیری سانتریفیوژ",
    "دیفیوزر هوادهی",
    "CHP",
    "بیوگاز",
    "UV",
]

# سرچ روی DuckDuckGo (نسخه HTML با دسترسی آزاد)
DDG_URL = "https://html.duckduckgo.com/html/"

UA = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/124.0 Safari/537.36"
}

def ddg_search(query, max_items=15):
    """جستجو در DuckDuckGo HTML، خروجی: [{title, link, snippet}]"""
    try:
        r = requests.post(DDG_URL, data={"q": query, "kl": "ir-fa"}, headers=UA, timeout=25)
        r.raise_for_status()
    except Exception as ex:
        return {"error": f"request failed: {ex}", "items": []}

    soup = BeautifulSoup(r.text, "html.parser")
    items = []
    for res in soup.select("a.result__a"):
        title = res.get_text(" ", strip=True)
        link = res.get("href", "").strip()
        # اسنیپت
        sn = res.find_parent(class_="result").select_one(".result__snippet")
        snippet = sn.get_text(" ", strip=True) if sn else ""
        if title and link and link.startswith("http"):
            items.append({"title": title, "link": link, "snippet": snippet})

        if len(items) >= max_items:
            break
    return {"error": None, "items": items}

def normalize(q: str) -> str:
    # حذف فاصله‌های اضافی
    q = re.sub(r"\s+", " ", q).strip()
    return q

def main():
    # کوئری را کمی غنی می‌کنیم: به دنبال کلمات مناقصه/مزایده/استعلام هم بگرد
    SUFFIX = ' (site:.ir OR site:.org OR site:.com) (مناقصه OR مزایده OR استعلام)'
    result = {"updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "queries": []}

    for kw in KEYWORDS:
        q = normalize(f'{kw} {SUFFIX}')
        print(f"[INFO] search: {q}")
        data = ddg_search(q, max_items=15)
        # وقفه کوتاه برای ادب نسبت به موتور جستجو
        time.sleep(2)
        result["queries"].append({
            "keyword": kw,
            "query": q,
            "items": data["items"],
            "error": data["error"],
        })

    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] wrote {OUT}")

if __name__ == "__main__":
    main()
