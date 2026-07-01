"""
Hearthstone-Decks.net 牌組蒐集器（不需金鑰）

流程：
  1. 抓列表頁（例如 /standard-decks/），找出各個別牌組頁的網址
  2. 從網址 slug 解析牌組類型、傳說排名、勝負場
     例：quest-mage-11-legend-unknown-score-42-23
         → 類型 Quest Mage、排名 #11、戰績 42-23
  3. 進每個牌組頁抓出牌組代碼（頁面內的 deckstring）

回傳的每個元素格式與 collector.scraper 相同，方便主管線統一處理，
並額外帶一個 "archetype" 欄位（牌組類型名稱）。
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

# 要掃描的列表頁（日後可加入 /wild-decks/ 等）
LISTING_PAGES = [
    "/standard-decks/",
]

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


def _collect_deck_urls(limit: int) -> list:
    urls = []
    for page in LISTING_PAGES:
        html = _fetch(BASE + page)
        if not html:
            continue
        for slug in DECK_URL_RE.findall(html):
            u = f"{BASE}/{slug}/"
            if u not in urls:
                urls.append(u)
        time.sleep(1)
    return urls[:limit]


def scrape_hsdecks_net(limit: int = 40) -> list:
    """從 Hearthstone-Decks.net 蒐集牌組。"""
    print(f"  抓取 hearthstone-decks.net（最多 {limit} 副）...")
    deck_urls = _collect_deck_urls(limit)
    print(f"  → 找到 {len(deck_urls)} 個牌組頁面")

    results = []
    for u in deck_urls:
        html = _fetch(u)
        if not html:
            continue
        codes = list(dict.fromkeys(extract_deckstrings(html)))
        if not codes:
            continue

        slug = u.rstrip("/").split("/")[-1]
        meta = _parse_slug(slug)

        # 組成與 Reddit 相同格式的標題，讓 parse_legend_rank / parse_winrate 可沿用
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
            "deckstrings": codes[:1],  # 每頁通常只有一組代碼
        })
        time.sleep(0.5)  # 禮貌性延遲，避免對站方造成負擔

    print(f"  → 成功取得 {len(results)} 副含代碼的牌組")
    return results
