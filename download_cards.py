"""
下載爐石卡牌資料庫（三語系）。

用法（在專案根目錄執行）：
    python download_cards.py        (Windows)
    python3 download_cards.py       (Mac)

執行一次即可。之後每次改版（新資料片上線）想更新卡牌名稱時再跑一次。
這些檔案很大（約 15MB），不會被上傳到 GitHub（已在 .gitignore 排除）。
"""

import os
import urllib.request

# 有些伺服器會拒絕沒有 User-Agent 的請求（回 403 Forbidden），
# 因此裝上一個帶 User-Agent 的 opener，讓底下的 urlretrieve 一併套用。
_opener = urllib.request.build_opener()
_opener.addheaders = [("User-Agent", "hs-deck-collector/0.1 (deck aggregation tool)")]
urllib.request.install_opener(_opener)

os.makedirs("data", exist_ok=True)

FILES = {
    "data/cards.json":      "https://api.hearthstonejson.com/v1/latest/enUS/cards.json",
    "data/cards_zhTW.json": "https://api.hearthstonejson.com/v1/latest/zhTW/cards.json",
    "data/cards_jaJP.json": "https://api.hearthstonejson.com/v1/latest/jaJP/cards.json",
}

for path, url in FILES.items():
    print(f"下載中：{path} ...")
    urllib.request.urlretrieve(url, path)
    size_mb = os.path.getsize(path) / 1024 / 1024
    print(f"  完成（{size_mb:.1f} MB）")

print("\n全部下載完成。")
