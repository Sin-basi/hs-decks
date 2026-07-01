"""
Reddit / 文本來源的牌組代碼蒐集器

使用 Reddit 公開 JSON API（不需 OAuth），
從 r/CompetitiveHS、r/hearthstone 等來源擷取牌組代碼。
"""

import json
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional
from collector.decoder import extract_deckstrings, decode_deckstring, fingerprint

REDDIT_HEADERS = {
    "User-Agent": "hs-deck-collector/0.1 (deck aggregation tool)"
}

# 蒐集來源設定
SUBREDDITS = [
    {"name": "CompetitiveHS", "sort": "new", "limit": 50},
    {"name": "hearthstone",   "sort": "new", "limit": 50},
]


def fetch_reddit_json(url: str) -> Optional[dict]:
    """
    從 Reddit JSON API 取得資料。
    Reddit 限制：每分鐘不超過 30 次請求。
    """
    req = urllib.request.Request(url, headers=REDDIT_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, Exception) as e:
        print(f"  [錯誤] 無法取得 {url}: {e}")
        return None


def scrape_subreddit(subreddit: str, sort: str = "new", limit: int = 50) -> list[dict]:
    """
    從單一 subreddit 蒐集牌組。
    
    回傳列表，每個元素:
    {
        "source": "reddit",
        "subreddit": str,
        "post_id": str,
        "post_title": str,
        "post_url": str,
        "author": str,
        "created_utc": float,
        "deckstrings": [str, ...],
    }
    """
    url = f"https://www.reddit.com/r/{subreddit}/{sort}.json?limit={limit}"
    print(f"  抓取 r/{subreddit} ({sort}, limit={limit})...")

    data = fetch_reddit_json(url)
    if not data or "data" not in data:
        return []

    results = []
    posts = data["data"].get("children", [])

    for post in posts:
        pdata = post.get("data", {})
        title = pdata.get("title", "")
        selftext = pdata.get("selftext", "")
        post_id = pdata.get("id", "")
        author = pdata.get("author", "unknown")
        created = pdata.get("created_utc", 0)
        permalink = pdata.get("permalink", "")

        # 從標題和內文中擷取牌組代碼
        combined_text = f"{title}\n{selftext}"
        codes = extract_deckstrings(combined_text)

        if codes:
            results.append({
                "source": "reddit",
                "subreddit": subreddit,
                "post_id": post_id,
                "post_title": title,
                "post_url": f"https://www.reddit.com{permalink}",
                "author": author,
                "created_utc": created,
                "deckstrings": codes,
            })

    print(f"  → 找到 {len(results)} 篇含牌組代碼的貼文（共 {sum(len(r['deckstrings']) for r in results)} 組代碼）")
    return results


def scrape_all_subreddits() -> list[dict]:
    """依序蒐集所有設定的 subreddit"""
    all_results = []
    for cfg in SUBREDDITS:
        results = scrape_subreddit(cfg["name"], cfg["sort"], cfg["limit"])
        all_results.extend(results)
        # Reddit rate limit: 遵守每分鐘 30 次限制
        time.sleep(2)
    return all_results


def parse_legend_rank(title: str) -> Optional[int]:
    """
    從貼文標題中解析傳說排名。
    常見格式: "#1 Legend", "Legend #42", "Top 100 Legend"
    """
    import re
    # "#數字 Legend" 或 "Legend #數字"
    m = re.search(r'#(\d+)\s*(?:legend|Legend|LEGEND)', title)
    if m:
        return int(m.group(1))
    m = re.search(r'(?:legend|Legend|LEGEND)\s*#?(\d+)', title)
    if m:
        return int(m.group(1))
    # "Top 數字 Legend"
    m = re.search(r'[Tt]op\s*(\d+)\s*[Ll]egend', title)
    if m:
        return int(m.group(1))
    return None


def parse_winrate(title: str) -> Optional[dict]:
    """
    從標題中解析勝敗比。
    常見格式: "(Score: 42-23)", "72% WR", "15W-3L"
    """
    import re
    # "Score: W-L" 或 "W-L"
    m = re.search(r'(\d+)\s*[-–]\s*(\d+)', title)
    if m:
        wins = int(m.group(1))
        losses = int(m.group(2))
        total = wins + losses
        if total > 0 and wins > losses:  # 基本合理性檢查
            return {
                "wins": wins,
                "losses": losses,
                "total": total,
                "winrate": round(wins / total * 100, 1),
            }
    # "XX% WR" 或 "XX% winrate"
    m = re.search(r'(\d+(?:\.\d+)?)\s*%', title)
    if m:
        wr = float(m.group(1))
        if 50 <= wr <= 100:  # 合理範圍
            return {"winrate": wr}
    return None
