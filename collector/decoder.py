"""
Hearthstone 牌組代碼解碼器

牌組代碼格式（base64 編碼的二進位結構）：
  1. 保留位元組 (0x00)
  2. 版本 (varint, 目前為 1)
  3. 模式 (varint: 1=Wild, 2=Standard, 3=Classic, 4=Twist)
  4. 英雄數量 (varint, 通常為 1)
  5. 英雄卡牌 DB ID (varint × 英雄數量)
  6. 單張卡牌數量 (varint)
  7. 單張卡牌 DB ID (varint × 數量)
  8. 雙張卡牌數量 (varint)
  9. 雙張卡牌 DB ID (varint × 數量)
  10. N張卡牌數量 (varint)
  11. 每張: DB ID (varint) + 數量 (varint)
"""

import base64
import re
from typing import Optional

# 英雄 DB ID → 職業名稱對應表
HERO_CLASS_MAP = {
    274:   ("Druid",        "德魯伊",   "ドルイド"),
    31:    ("Hunter",       "獵人",     "ハンター"),
    637:   ("Mage",         "法師",     "メイジ"),
    671:   ("Paladin",      "聖騎士",   "パラディン"),
    813:   ("Priest",       "牧師",     "プリースト"),
    930:   ("Rogue",        "盜賊",     "ローグ"),
    1066:  ("Shaman",       "薩滿",     "シャーマン"),
    893:   ("Warlock",      "術士",     "ウォーロック"),
    7:     ("Warrior",      "戰士",     "ウォリアー"),
    56550: ("Demon Hunter", "惡魔獵人", "デモンハンター"),
    78065: ("Death Knight", "死亡騎士", "デスナイト"),
}

# 英雄 DB ID → 職業的替代英雄（造型英雄等）
# 當遇到未知英雄 ID 時，需要查卡牌資料庫確認職業
ALT_HEROES = {
    2826:  "Hunter",       # Alleria Windrunner
    2827:  "Mage",         # Medivh
    2828:  "Warrior",      # Magni Bronzebeard
    50484: "Druid",        # Lunara
    53237: "Warlock",      # Nemsy Necrofizzle
    58536: "Paladin",      # Sir Annoy-O
    57761: "Shaman",       # King Rastakhan
    60017: "Hunter",       # Sylvanas Windrunner
    60882: "Warrior",      # Thunder King
    61958: "Druid",        # Elise Starseeker
    62784: "Rogue",        # Maiev Shadowsong (not the real id, placeholder)
    64674: "Warlock",      # Mecha-Jaraxxus
    55963: "Priest",       # Tyrande Whisperwind
    57706: "Mage",         # Fire Mage Jaina
    59210: "Druid",        # Dame Hazelbark
    60238: "Paladin",      # Arthas
}

FORMAT_NAMES = {
    1: ("Wild",     "狂野",   "ワイルド"),
    2: ("Standard", "標準",   "スタンダード"),
    3: ("Classic",  "經典",   "クラシック"),
    4: ("Twist",    "扭曲",   "ツイスト"),
}

# 牌組代碼的正則表達式（base64 字串，通常以 AAE 開頭）
DECKSTRING_PATTERN = re.compile(
    r'(AAE[A-Za-z0-9+/=]{30,})'
)


def _read_varint(data: bytes, offset: int) -> tuple[int, int]:
    """讀取 Protocol Buffers 風格的 varint"""
    result = 0
    shift = 0
    while offset < len(data):
        byte = data[offset]
        offset += 1
        result |= (byte & 0x7F) << shift
        if (byte & 0x80) == 0:
            break
        shift += 7
    return result, offset


def decode_deckstring(deckstring: str) -> Optional[dict]:
    """
    解碼爐石牌組代碼字串。
    
    回傳格式:
    {
        "deckstring": 原始代碼,
        "version": 版本號,
        "format": 模式代碼 (1=Wild, 2=Standard, ...),
        "format_name": {"en": ..., "zh": ..., "ja": ...},
        "hero_id": 英雄 DB ID,
        "hero_class": {"en": ..., "zh": ..., "ja": ...},
        "cards": [{"id": DB_ID, "count": 數量}, ...],
        "total_cards": 總卡牌數,
    }
    """
    try:
        # 清理輸入（移除空白、換行）
        deckstring = deckstring.strip()
        data = base64.b64decode(deckstring)
    except Exception:
        return None

    try:
        offset = 0

        # 1. 保留位元組
        _reserved = data[offset]
        offset += 1

        # 2. 版本
        version, offset = _read_varint(data, offset)

        # 3. 模式
        format_type, offset = _read_varint(data, offset)

        # 4-5. 英雄
        num_heroes, offset = _read_varint(data, offset)
        heroes = []
        for _ in range(num_heroes):
            hero_id, offset = _read_varint(data, offset)
            heroes.append(hero_id)

        # 6-7. 單張卡牌
        num_single, offset = _read_varint(data, offset)
        cards = []
        for _ in range(num_single):
            card_id, offset = _read_varint(data, offset)
            cards.append({"id": card_id, "count": 1})

        # 8-9. 雙張卡牌
        num_double, offset = _read_varint(data, offset)
        for _ in range(num_double):
            card_id, offset = _read_varint(data, offset)
            cards.append({"id": card_id, "count": 2})

        # 10-11. N張卡牌
        if offset < len(data):
            num_multi, offset = _read_varint(data, offset)
            for _ in range(num_multi):
                card_id, offset = _read_varint(data, offset)
                count, offset = _read_varint(data, offset)
                cards.append({"id": card_id, "count": count})

        # 解析英雄職業
        hero_id = heroes[0] if heroes else 0
        hero_class_info = HERO_CLASS_MAP.get(hero_id)
        if hero_class_info:
            hero_class = {
                "en": hero_class_info[0],
                "zh": hero_class_info[1],
                "ja": hero_class_info[2],
            }
        elif hero_id in ALT_HEROES:
            alt_en = ALT_HEROES[hero_id]
            # 從標準英雄表中反查
            for _hid, info in HERO_CLASS_MAP.items():
                if info[0] == alt_en:
                    hero_class = {"en": info[0], "zh": info[1], "ja": info[2]}
                    break
            else:
                hero_class = {"en": alt_en, "zh": alt_en, "ja": alt_en}
        else:
            hero_class = {"en": "Unknown", "zh": "未知", "ja": "不明"}

        # 解析模式名稱
        fmt = FORMAT_NAMES.get(format_type, ("Unknown", "未知", "不明"))
        format_name = {"en": fmt[0], "zh": fmt[1], "ja": fmt[2]}

        total_cards = sum(c["count"] for c in cards)

        return {
            "deckstring": deckstring,
            "version": version,
            "format": format_type,
            "format_name": format_name,
            "hero_id": hero_id,
            "hero_class": hero_class,
            "cards": sorted(cards, key=lambda c: c["id"]),
            "total_cards": total_cards,
        }

    except (IndexError, ValueError):
        return None


def extract_deckstrings(text: str) -> list[str]:
    """從任意文本中擷取所有爐石牌組代碼"""
    return DECKSTRING_PATTERN.findall(text)


def fingerprint(deck: dict) -> str:
    """
    產生牌組指紋用於去重。
    相同的 30 張卡＋相同模式＝同一副牌組。
    """
    card_parts = []
    for c in sorted(deck["cards"], key=lambda x: x["id"]):
        card_parts.append(f"{c['id']}x{c['count']}")
    return f"{deck['format']}:{deck['hero_id']}:{','.join(card_parts)}"


if __name__ == "__main__":
    # 測試用牌組代碼
    test_codes = [
        # 經典 Mage deck (已知可解碼的格式)
        "AAECAf0EBsABobcCnccC7vYCp/cCyIcDDHG7ApUDlgWNCL8ImMQCj9MCAAA=",
        # 較短的測試代碼
        "AAECAf0GAAAP+v4C3IEDxIkD5awD/q4D068DnM0D184DkuQDiO8Dx/kD56AD/aUD/rQDh8QDAA==",
    ]
    
    for code in test_codes:
        result = decode_deckstring(code)
        if result:
            print(f"=== 解碼成功 ===")
            print(f"  模式: {result['format_name']['zh']} ({result['format_name']['en']})")
            print(f"  職業: {result['hero_class']['zh']} ({result['hero_class']['en']})")
            print(f"  卡牌數: {result['total_cards']}")
            print(f"  卡牌 ID 數: {len(result['cards'])}")
            print(f"  指紋: {fingerprint(result)[:60]}...")
            print()
        else:
            print(f"解碼失敗: {code[:30]}...")
            print()
