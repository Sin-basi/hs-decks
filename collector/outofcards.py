"""
Out of Cards (outof.cards) 牌組蒐集器（不需金鑰）

robots.txt 僅禁止後台/deckbuilder 儲存等路徑，牌組頁允許抓取。
流程：列表頁 → 各牌組頁 → 抓頁面內的牌組代碼；牌組名稱取自 og:title。
"""

import re
import time
import html
import urllib.request
import urllib.error
from typing import Optional

from collector.decoder import extract_deckstrings

BASE = "https://outof.cards"
LISTING = "https://outof.cards/hearthstone/decks/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
}

DECK_URL_RE = re.compile(r'href="(/realms/hearthstone/decks/\d+[^"#?]*)"')


def _fetch(url: str) -> Optional[str]:
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.read().decode("utf-8", "replace")
    except (urllib.error.URLError, urllib.error.HTTPError, Exception) as e:
        print(f"  [錯誤] 無法取得 {url}: {e}")
        return None


def _archetype_from_title(title: Optional[str]) -> Optional[str]:
    """從 og:title 取出乾淨的牌組名稱。"""
    if not title:
        return None
    t = html.unescape(title)                     # &#x27; -> '
    t = re.split(r'\s+Deck\b|\s*\|', t)[0].strip()  # 截到 " Deck" 或 " |" 之前
    t = re.sub(r'\s+\d+(?:\.\d+)?$', '', t).strip()  # 去掉結尾的版本號，例如 " 11.0"
    return t or None


def scrape_outofcards(limit: int = 25) -> list:
    """從 outof.cards 蒐集牌組。"""
    print(f"  抓取 outof.cards（最多 {limit} 副）...")
    listing = _fetch(LISTING)
    if not listing:
        return []

    paths = []
    for p in DECK_URL_RE.findall(listing):
        if p not in paths:
            paths.append(p)
    paths = paths[:limit]
    print(f"  → 找到 {len(paths)} 個牌組頁面")

    results = []
    for p in paths:
        url = BASE + p
        page = _fetch(url)
        if not page:
            continue
        codes = list(dict.fromkeys(extract_deckstrings(page)))
        if not codes:
            continue
        og = re.search(r'<meta property="og:title" content="([^"]+)"', page)
        arch = _archetype_from_title(og.group(1) if og else None)
        results.append({
            "source": "outof.cards",
            "subreddit": "",
            "post_id": p.split("/")[-1][:40],
            "post_title": arch or "",
            "post_url": url,
            "author": "outof.cards",
            "created_utc": 0,
            "archetype": arch,
            "deckstrings": codes[:1],
        })
        time.sleep(0.5)

    print(f"  → 成功取得 {len(results)} 副含代碼的牌組")
    return results
