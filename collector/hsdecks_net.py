"""
Hearthstone-Decks.net 牌組蒐集器（不需金鑰）

流程：
  1. 掃描列表頁（standard + wild，各含後續分頁 page/2、page/3…），找出個別牌組頁網址
     — 每個列表各給一個配額，確保標準與狂野都抓得到
  2. 從網址 slug 解析牌組類型、傳說排名、勝負場
     例：quest-mage-11-legend-unknown-score-42-23
  3. 進每個牌組頁抓出牌組代碼（頁面內的 deckstring）

回傳格式與 collector.scraper 相同，並額外帶 "archetype"。
"""

import re
import time
import urllib.request
import urllib.error
from typing import Optional

from collector.decoder import extract_deckstrings

BASE = "https://hearthstone-decks.net"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
}

# 要掃描的列表頁（標準 + 狂野）
LISTING_PAGES = [
    "/standard-decks/",
    "/wild-decks/",
]

# 每個列表頁往後翻幾頁
PAGES = 50

# 個別牌組頁的網址：slug 內含 "legend"
DECK_URL_RE = re.compile(r'https://hearthstone-decks\.net/([a-z0-9\-]*legend[a-z0-9\-]*)/')


def _fetch(url: str) -> Optional[str]:
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.read().decode("utf-8", "replace")
    except (urllib.error.URLError, urllib.error.HTTPError, Exception) as e:
        print(f"  [錯誤] 無法取得 {url}: {e}")
        return None


def _parse_slug(slug: str) -> dict:
    """從網址 slug 解析類型、排名、勝負場。"""
    meta = {"archetype": None, "legend_rank": None, "wins": None, "losses": None}

    ms = re.search(r'score-(\d+)-(\d+)$', slug)
    if ms:
        meta["wins"], meta["losses"] = int(ms.group(1)), int(ms.group(2))

    mr = re.search(r'^(.+?)-(\d+)-legend', slug)
    if mr:
        meta["archetype"] = mr.group(1).replace("-", " ").title()
        meta["legend_rank"] = int(mr.group(2))
    else:
        ma = re.search(r'^(.+?)-legend', slug)
        if ma:
            meta["archetype"] = ma.group(1).replace("-", " ").title()

    if not meta["archetype"]:
        meta["archetype"] = slug.replace("-", " ").title()
    return meta


def _collect_deck_urls(per_listing: int) -> list:
    """每個列表頁各收集最多 per_listing 個牌組網址（確保標準/狂野都有）。"""
    urls = []
    for base_path in LISTING_PAGES:
        got = []
        for pg in range(1, PAGES + 1):
            if len(got) >= per_listing:
                break
            page_path = base_path if pg == 1 else f"{base_path}page/{pg}/"
            html = _fetch(BASE + page_path)
            if not html:
                continue
            before = len(got)
            for slug in DECK_URL_RE.findall(html):
                u = f"{BASE}/{slug}/"
                if u not in urls and u not in got:
                    got.append(u)
            print(f"    {base_path} p{pg}: +{len(got)-before} → 累計 {len(got)}", flush=True)
            time.sleep(0.8)
        urls.extend(got[:per_listing])
    return urls


def scrape_hsdecks_net(per_listing: int = 45) -> list:
    """從 Hearthstone-Decks.net 蒐集牌組（標準 + 狂野各約 per_listing 副）。"""
    print(f"  抓取 hearthstone-decks.net（標準/狂野各最多 {per_listing} 副）...")
    deck_urls = _collect_deck_urls(per_listing)
    print(f"  → 找到 {len(deck_urls)} 個牌組頁面")

    results = []
    total = len(deck_urls)
    for i, u in enumerate(deck_urls, 1):
        if i % 100 == 0 or i == total:
            print(f"    進度：{i}/{total}（已取得 {len(results)} 副）", flush=True)
        html = _fetch(u)
        if not html:
            continue
        codes = list(dict.fromkeys(extract_deckstrings(html)))
        if not codes:
            continue

        slug = u.rstrip("/").split("/")[-1]
        meta = _parse_slug(slug)

        title = meta["archetype"] or slug
        if meta["legend_rank"] is not None:
            title += f" #{meta['legend_rank']} Legend"
        if meta["wins"] is not None and meta["losses"] is not None:
            title += f" (Score: {meta['wins']}-{meta['losses']})"

        results.append({
            "source": "hearthstone-decks.net",
            "subreddit": "",
            "post_id": slug,
            "post_title": title,
            "post_url": u,
            "author": "hearthstone-decks.net",
            "created_utc": 0,
            "archetype": meta["archetype"],
            "deckstrings": codes[:1],
        })
        time.sleep(0.4)

    print(f"  → 成功取得 {len(results)} 副含代碼的牌組")
    return results
