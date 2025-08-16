import os, json, hashlib
import yaml, feedparser
from jinja2 import Environment, FileSystemLoader, select_autoescape
from dateutil import parser as dtparser
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(__file__))
TPL_DIR = os.path.join(ROOT, "templates")
OUT = os.path.join(ROOT, "site")
os.makedirs(OUT, exist_ok=True)

with open(os.path.join(ROOT, "config_site.json"), encoding="utf-8") as f:
    SITE = json.load(f)
with open(os.path.join(ROOT, "feeds.yaml"), encoding="utf-8") as f:
    FEEDS = yaml.safe_load(f)

env = Environment(
    loader=FileSystemLoader(TPL_DIR),
    autoescape=select_autoescape(['html','xml'])
)
base_tpl = env.get_template("layout.html")

cat_titles = {
    "environment": "محیط‌زیست",
    "water": "آب",
    "wastewater": "فاضلاب",
    "oil_gas_petrochem": "نفت/گاز/پتروشیمی",
    "tenders": "مناقصه‌ها"
}

def norm_date(entry):
    for key in ("published", "updated", "created"):
        val = entry.get(key)
        if val:
            try:
                return dtparser.parse(val)
            except Exception:
                pass
    # feedparser puts parsed time in published_parsed sometimes
    if entry.get("published_parsed"):
        try:
            from datetime import datetime
            return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        except Exception:
            pass
    return datetime.now(timezone.utc)

def hash_key(s): return hashlib.sha1(s.encode("utf-8")).hexdigest()

items_all = []
for cat, urls in FEEDS.items():
    for url in urls or []:
        try:
            feed = feedparser.parse(url)
            source_title = (feed.feed.get("title") or "").strip()
            for e in feed.entries[:100]:
                link = e.get("link") or ""
                title = (e.get("title") or "").strip()
                if not title or not link: 
                    continue
                dt = norm_date(e)
                items_all.append({
                    "id": hash_key(link or title),
                    "title": title,
                    "link": link,
                    "summary": (e.get("summary") or "").strip()[:280],
                    "iso_date": dt.astimezone(timezone.utc).isoformat(),
                    "human_date": dt.strftime("%Y-%m-%d"),
                    "category": cat,
                    "category_fa": cat_titles.get(cat, cat),
                    "source": source_title[:40]
                })
        except Exception as ex:
            print("ERR feed", url, ex)

# dedupe by link hash, keep latest
seen = {}
for it in sorted(items_all, key=lambda x: x["iso_date"], reverse=True):
    key = it["id"]
    if key not in seen:
        seen[key] = it
deduped = list(seen.values())

# per-category slice
by_cat = {c: [] for c in cat_titles}
for it in deduped:
    if it["category"] in by_cat:
        by_cat[it["category"]].append(it)
maxn = int(SITE.get("max_items_per_category", 60))
for c in by_cat:
    by_cat[c] = sorted(by_cat[c], key=lambda x: x["iso_date"], reverse=True)[:maxn]

# build pages (index = all)
updated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
def render_page(filename, heading, items):
    html = base_tpl.render(
        page_title=heading,
        heading=heading,
        items=items,
        updated_at=updated_at,
        site=SITE
    )
    with open(os.path.join(OUT, filename), "w", encoding="utf-8") as f:
        f.write(html)

all_items = sorted(deduped, key=lambda x: x["iso_date"], reverse=True)[: sum(len(v) for v in by_cat.values())]
render_page("index.html", "همه دسته‌ها", all_items)
render_page("environment.html", "اخبار محیط‌زیست", by_cat["environment"])
render_page("water.html", "اخبار آب", by_cat["water"])
render_page("wastewater.html", "اخبار فاضلاب", by_cat["wastewater"])
render_page("oil_gas_petrochem.html", "اخبار نفت/گاز/پتروشیمی", by_cat["oil_gas_petrochem"])
render_page("tenders.html", "مناقصه‌ها", by_cat["tenders"])

# copy static assets
import shutil
shutil.copy(os.path.join(TPL_DIR,"styles.css"), os.path.join(OUT,"styles.css"))

print(f"Built {len(all_items)} items across {len(by_cat)} categories → site/")
