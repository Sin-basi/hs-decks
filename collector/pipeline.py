"""
牌組蒐集管線（v2，輸出到 data/ 資料夾供 Next.js 使用）

與 v1 的唯一差異：輸出位置從 output/ 改為 data/，
讓網站可以直接 import ../data/decks.json。
"""

import json
import os
import hashlib
from datetime import datetime, timezone
from collector.decoder import decode_deckstring, fingerprint
from collector.scraper import scrape_all_subreddits, parse_legend_rank, parse_winrate
from collector.hsdecks_net import scrape_hsdecks_net
from collector.outofcards import scrape_outofcards

# 輸出到專案根目錄的 data/ 資料夾（Next.js 會讀這裡）
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
CARDDB_PATH = os.path.join(OUTPUT_DIR, "cards.json")

# 卡牌資料庫的 cardClass（大寫）→ 三語職業名稱。
# 用來從英雄卡本身判斷職業，比 decoder 內建的英雄 ID 對照表可靠得多
# （爐石有上百種英雄造型，硬表列不完）。
CARDCLASS_TO_NAMES = {
    "DRUID":       {"en": "Druid",        "zh": "德魯伊",   "ja": "ドルイド"},
    "HUNTER":      {"en": "Hunter",       "zh": "獵人",     "ja": "ハンター"},
    "MAGE":        {"en": "Mage",         "zh": "法師",     "ja": "メイジ"},
    "PALADIN":     {"en": "Paladin",      "zh": "聖騎士",   "ja": "パラディン"},
    "PRIEST":      {"en": "Priest",       "zh": "牧師",     "ja": "プリースト"},
    "ROGUE":       {"en": "Rogue",        "zh": "盜賊",     "ja": "ローグ"},
    "SHAMAN":      {"en": "Shaman",       "zh": "薩滿",     "ja": "シャーマン"},
    "WARLOCK":     {"en": "Warlock",      "zh": "術士",     "ja": "ウォーロック"},
    "WARRIOR":     {"en": "Warrior",      "zh": "戰士",     "ja": "ウォリアー"},
    "DEMONHUNTER": {"en": "Demon Hunter", "zh": "惡魔獵人", "ja": "デモンハンター"},
    "DEATHKNIGHT": {"en": "Death Knight", "zh": "死亡騎士", "ja": "デスナイト"},
}


def load_card_db() -> dict:
    if not os.path.exists(CARDDB_PATH):
        print("  [提示] 卡牌資料庫不存在，卡牌名稱將以 ID 顯示。")
        print("  請先執行：python download_cards.py")
        return {}
    with open(CARDDB_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)
    db = {}
    for card in raw:
        dbf_id = card.get("dbfId")
        if dbf_id:
            db[dbf_id] = {
                "name_en": card.get("name", ""),
                "cost": card.get("cost", 0),
                "rarity": card.get("rarity", ""),
                "type": card.get("type", ""),
                "cardClass": card.get("cardClass", ""),
            }
    print(f"  卡牌資料庫已載入：{len(db)} 張卡牌")
    return db


def load_card_db_localized(locale: str) -> dict:
    path = os.path.join(OUTPUT_DIR, f"cards_{locale}.json")
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return {c.get("dbfId"): c.get("name", "") for c in raw if c.get("dbfId")}


def resolve_hero_class(decoded: dict, card_db: dict) -> dict:
    """優先用英雄卡的 cardClass 判斷職業，查不到才退回 decoder 的結果。"""
    if card_db:
        hero_info = card_db.get(decoded.get("hero_id"))
        if hero_info:
            names = CARDCLASS_TO_NAMES.get(hero_info.get("cardClass", ""))
            if names:
                return names
    return decoded["hero_class"]


def enrich_deck(deck: dict, card_db: dict, locales: dict) -> dict:
    enriched = []
    dust_cost = 0
    rarity_dust = {"COMMON": 40, "RARE": 100, "EPIC": 400, "LEGENDARY": 1600}
    for card in deck["cards"]:
        cid = card["id"]
        info = card_db.get(cid, {})
        entry = {
            "id": cid, "count": card["count"],
            "cost": info.get("cost", 0),
            "name_en": info.get("name_en", f"#{cid}"),
            "rarity": info.get("rarity", ""),
        }
        for lk, ldb in locales.items():
            entry[f"name_{lk}"] = ldb.get(cid, entry["name_en"])
        dust_cost += rarity_dust.get(info.get("rarity", ""), 0) * card["count"]
        enriched.append(entry)
    deck["cards"] = sorted(enriched, key=lambda c: (c["cost"], c["name_en"]))
    deck["dust_cost"] = dust_cost
    return deck


def process_scraped_data(scraped, card_db, locales):
    seen = set()
    decks = []
    for item in scraped:
        for code in item["deckstrings"]:
            decoded = decode_deckstring(code)
            if not decoded or decoded["total_cards"] != 30:
                continue
            fp = fingerprint(decoded)
            if fp in seen:
                continue
            seen.add(fp)
            entry = {
                "id": hashlib.md5(fp.encode()).hexdigest()[:12],
                "deckstring": code,
                "format": decoded["format_name"],
                "hero_class": resolve_hero_class(decoded, card_db),
                "archetype": item.get("archetype"),
                "total_cards": decoded["total_cards"],
                "cards": decoded["cards"],
                "source": {
                    "type": item.get("source", "manual"),
                    "url": item.get("post_url", ""),
                    "author": item.get("author", ""),
                    "title": item.get("post_title", ""),
                },
                "legend_rank": parse_legend_rank(item.get("post_title", "")),
                "winrate": parse_winrate(item.get("post_title", "")),
                "collected_at": datetime.now(timezone.utc).isoformat(),
            }
            if card_db:
                entry = enrich_deck(entry, card_db, locales)
            decks.append(entry)
    return decks


def save_output(decks, filename="decks.json"):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(decks, f, ensure_ascii=False, indent=2)
    print(f"  已輸出 {len(decks)} 副牌組 → {path}")


def save_by_class(decks):
    by_class = {}
    for d in decks:
        cls = d["hero_class"]["en"].lower().replace(" ", "-")
        by_class.setdefault(cls, []).append(d)
    class_dir = os.path.join(OUTPUT_DIR, "classes")
    os.makedirs(class_dir, exist_ok=True)
    for cls, cds in by_class.items():
        with open(os.path.join(class_dir, f"{cls}.json"), "w", encoding="utf-8") as f:
            json.dump(cds, f, ensure_ascii=False, indent=2)
        print(f"    {cls}: {len(cds)} 副")


def collect_all_sources():
    """從所有可用來源蒐集牌組代碼。"""
    items = []
    # 來源 1：Hearthstone-Decks.net（robots 允許）
    try:
        items += scrape_hsdecks_net(limit=40)
    except Exception as e:
        print(f"  [hearthstone-decks.net 發生錯誤] {e}")
    # 來源 2：Out of Cards（robots 允許）
    try:
        items += scrape_outofcards(limit=25)
    except Exception as e:
        print(f"  [outof.cards 發生錯誤] {e}")
    # 來源 3：Reddit — 需官方 API 事先審核（2025/11 起），暫緩；
    #         程式仍保留在 collector/scraper.py，取得授權後再啟用。
    # try:
    #     items += scrape_all_subreddits()
    # except Exception as e:
    #     print(f"  [reddit 發生錯誤] {e}")
    return items


def run_pipeline(skip_scrape=False):
    print("=== 爐石牌組蒐集管線 ===\n")
    print("[1/4] 載入卡牌資料庫...")
    card_db = load_card_db()
    locales = {"zhTW": load_card_db_localized("zhTW"), "jaJP": load_card_db_localized("jaJP")}

    print("\n[2/4] 蒐集牌組代碼...")
    scraped = _test_data() if skip_scrape else collect_all_sources()
    if not scraped:
        print("  未蒐集到任何資料。")
        return

    print(f"\n[3/4] 處理牌組代碼...")
    decks = process_scraped_data(scraped, card_db, locales)
    print(f"  解碼並去重後：{len(decks)} 副牌組")

    print(f"\n[4/4] 輸出結果...")
    save_output(decks)
    if decks:
        print("  按職業分類：")
        save_by_class(decks)
    print("\n=== 完成 ===")
    return decks


def _test_data():
    return [
        {"source": "reddit", "subreddit": "CompetitiveHS", "post_id": "t1",
         "post_title": "Elemental Mage #96 Legend (Score: 42-23)",
         "post_url": "https://reddit.com/r/CompetitiveHS/comments/t1",
         "author": "TestPlayer", "created_utc": 1719700000,
         "deckstrings": ["AAECAf0EBsABobcCnccC7vYCp/cCyIcDDHG7ApUDlgWNCL8ImMQCj9MCAAA="]},
    ]


if __name__ == "__main__":
    import sys
    skip = "--test" in sys.argv
    run_pipeline(skip_scrape=skip)
