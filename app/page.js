"use client";

// 這是網站首頁。它會讀取 ../data/decks.json 裡的牌組資料並顯示出來。
// 「use client」這一行一定要放在最上面，因為這個頁面有互動功能（篩選、複製按鈕）。

import { useState, useMemo } from "react";
import decksData from "../data/decks.json";

// 每個職業的代表色
const CLASS_COLORS = {
  Mage: "#3C9BF0", Warrior: "#C41E3A", Shaman: "#0070DE",
  Priest: "#A2ABB3", Paladin: "#F48CBA", Druid: "#FF7C0A",
  Hunter: "#AAD372", Rogue: "#E8D44D", Warlock: "#8788EE",
  "Demon Hunter": "#A330C9", "Death Knight": "#6AB8C6",
};

const CLASSES = ["all", "Druid", "Hunter", "Mage", "Paladin", "Priest", "Rogue", "Shaman", "Warlock", "Warrior", "Demon Hunter", "Death Knight"];
const FORMATS = ["all", "Standard", "Wild", "Twist"];

// 三語系的介面文字
const CLASS_NAMES = {
  zh: { all: "全部", Druid: "德魯伊", Hunter: "獵人", Mage: "法師", Paladin: "聖騎士", Priest: "牧師", Rogue: "盜賊", Shaman: "薩滿", Warlock: "術士", Warrior: "戰士", "Demon Hunter": "惡魔獵人", "Death Knight": "死亡騎士" },
  en: { all: "All", Druid: "Druid", Hunter: "Hunter", Mage: "Mage", Paladin: "Paladin", Priest: "Priest", Rogue: "Rogue", Shaman: "Shaman", Warlock: "Warlock", Warrior: "Warrior", "Demon Hunter": "Demon Hunter", "Death Knight": "Death Knight" },
  ja: { all: "全て", Druid: "ドルイド", Hunter: "ハンター", Mage: "メイジ", Paladin: "パラディン", Priest: "プリースト", Rogue: "ローグ", Shaman: "シャーマン", Warlock: "ウォーロック", Warrior: "ウォリアー", "Demon Hunter": "デモンハンター", "Death Knight": "デスナイト" },
};
const FORMAT_NAMES = {
  zh: { all: "全部", Standard: "標準", Wild: "狂野", Twist: "扭曲" },
  en: { all: "All", Standard: "Standard", Wild: "Wild", Twist: "Twist" },
  ja: { all: "全て", Standard: "スタンダード", Wild: "ワイルド", Twist: "ツイスト" },
};
const SORT_LABELS = {
  zh: { time: "最新", rank: "排名", winrate: "勝率", dust: "粉塵" },
  en: { time: "New", rank: "Rank", winrate: "Win%", dust: "Dust" },
  ja: { time: "新着", rank: "ランク", winrate: "勝率", dust: "ダスト" },
};
const UI_TEXT = {
  zh: { decks: "副牌組", empty: "沒有符合條件的牌組", copy: "複製牌組代碼", copied: "已複製", by: "來源" },
  en: { decks: "decks", empty: "No decks found", copy: "Copy deck code", copied: "Copied", by: "by" },
  ja: { decks: "デッキ", empty: "該当するデッキがありません", copy: "デッキコードをコピー", copied: "コピー済み", by: "by" },
};

function timeSince(dateStr, lang) {
  const hours = Math.floor((new Date() - new Date(dateStr)) / 3600000);
  if (hours < 1) return { zh: "剛剛", en: "just now", ja: "たった今" }[lang];
  if (hours < 24) return lang === "en" ? `${hours}h ago` : `${hours} 小時前`;
  const days = Math.floor(hours / 24);
  return lang === "en" ? `${days}d ago` : `${days} 天前`;
}

function DeckCard({ deck, lang }) {
  const [copied, setCopied] = useState(false);
  const classColor = CLASS_COLORS[deck.hero_class.en] || "#888";
  const t = UI_TEXT[lang];

  const handleCopy = () => {
    navigator.clipboard.writeText(deck.deckstring).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };

  return (
    <div style={{ background: "#1a1a2e", borderRadius: 6, overflow: "hidden", border: "1px solid #2a2a4a" }}>
      <div style={{ height: 3, background: classColor }} />
      <div style={{ padding: "12px 14px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 6 }}>
          <span style={{ fontSize: 14, fontWeight: 600, color: "#e8e8f0" }}>
            {deck.archetype || deck.hero_class[lang]}
          </span>
          <span style={{
            fontSize: 10, padding: "1px 6px", borderRadius: 3, fontWeight: 600,
            background: deck.format.en === "Wild" ? "#4a2a6a" : "#1a3a5a",
            color: deck.format.en === "Wild" ? "#c084fc" : "#60a5fa",
          }}>
            {deck.format[lang]}
          </span>
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 8 }}>
          <span style={{ fontSize: 12, color: classColor, fontWeight: 500 }}>{deck.hero_class[lang]}</span>
          {deck.legend_rank && <span style={{ fontSize: 12, color: "#fbbf24" }}>#{deck.legend_rank}</span>}
          {deck.winrate && deck.winrate.winrate && (
            <span style={{ fontSize: 12, fontWeight: 500, color: deck.winrate.winrate >= 65 ? "#4ade80" : deck.winrate.winrate >= 55 ? "#a3e635" : "#94a3b8" }}>
              {deck.winrate.winrate}%
              {deck.winrate.wins != null && (
                <span style={{ color: "#64748b", fontWeight: 400 }}> ({deck.winrate.wins}-{deck.winrate.losses})</span>
              )}
            </span>
          )}
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            {deck.dust_cost ? <span style={{ fontSize: 11, color: "#6b7280" }}>{deck.dust_cost.toLocaleString()} 塵</span> : null}
            {deck.source && deck.source.author ? <span style={{ fontSize: 11, color: "#4b5563" }}>{UI_TEXT[lang].by} {deck.source.author}</span> : null}
          </div>
          {deck.collected_at && <span style={{ fontSize: 10, color: "#4b5563" }}>{timeSince(deck.collected_at, lang)}</span>}
        </div>
        <button onClick={handleCopy} style={{
          width: "100%", padding: "7px 0", borderRadius: 4, border: "none",
          background: copied ? "#166534" : "#2563eb", color: "#fff",
          fontSize: 12, fontWeight: 600, cursor: "pointer",
        }}>
          {copied ? t.copied : t.copy}
        </button>
      </div>
    </div>
  );
}

export default function Home() {
  const [formatFilter, setFormatFilter] = useState("all");
  const [classFilter, setClassFilter] = useState("all");
  const [lang, setLang] = useState("zh");
  const [sortBy, setSortBy] = useState("time");

  const filtered = useMemo(() => {
    let list = [...decksData];
    if (formatFilter !== "all") list = list.filter(d => d.format.en === formatFilter);
    if (classFilter !== "all") list = list.filter(d => d.hero_class.en === classFilter);
    list.sort((a, b) => {
      if (sortBy === "rank") return (a.legend_rank || 9999) - (b.legend_rank || 9999);
      if (sortBy === "winrate") return ((b.winrate && b.winrate.winrate) || 0) - ((a.winrate && a.winrate.winrate) || 0);
      if (sortBy === "dust") return (a.dust_cost || 0) - (b.dust_cost || 0);
      return new Date(b.collected_at || 0) - new Date(a.collected_at || 0);
    });
    return list;
  }, [formatFilter, classFilter, sortBy]);

  const pill = (active) => ({
    padding: "4px 10px", borderRadius: 4, border: "1px solid #2a2a4a",
    background: active ? "#2563eb" : "transparent", color: active ? "#fff" : "#94a3b8",
    fontSize: 12, cursor: "pointer", fontWeight: active ? 600 : 400, whiteSpace: "nowrap",
  });

  return (
    <div style={{ fontFamily: "'Noto Sans TC', 'Inter', sans-serif", background: "#0f0f23", color: "#e2e4ea", minHeight: "100vh" }}>
      <header style={{ borderBottom: "1px solid #1a1a3a", padding: "12px 16px" }}>
        <div style={{ maxWidth: 720, margin: "0 auto", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h1 style={{ fontSize: 16, fontWeight: 700, color: "#e8e8f0", margin: 0 }}>HS Decks</h1>
          <div style={{ display: "flex", gap: 4 }}>
            {["zh", "en", "ja"].map(l => (
              <button key={l} onClick={() => setLang(l)} style={{ ...pill(lang === l), padding: "2px 8px", fontSize: 11 }}>
                {l === "zh" ? "中" : l === "en" ? "EN" : "日"}
              </button>
            ))}
          </div>
        </div>
      </header>

      <main style={{ maxWidth: 720, margin: "0 auto", padding: "12px 16px" }}>
        <div style={{ display: "flex", gap: 4, marginBottom: 6, flexWrap: "wrap" }}>
          {FORMATS.map(f => (
            <button key={f} onClick={() => setFormatFilter(f)} style={pill(formatFilter === f)}>
              {FORMAT_NAMES[lang][f]}
            </button>
          ))}
        </div>
        <div style={{ display: "flex", gap: 4, flexWrap: "wrap", marginBottom: 6 }}>
          {CLASSES.map(c => (
            <button key={c} onClick={() => setClassFilter(c)} style={{
              ...pill(classFilter === c),
              color: classFilter === c ? "#fff" : (CLASS_COLORS[c] || "#94a3b8"),
              borderColor: classFilter === c ? "#2563eb" : (CLASS_COLORS[c] ? CLASS_COLORS[c] + "33" : "#2a2a4a"),
            }}>
              {CLASS_NAMES[lang][c]}
            </button>
          ))}
        </div>
        <div style={{ display: "flex", gap: 4, marginBottom: 12 }}>
          {["time", "rank", "winrate", "dust"].map(s => (
            <button key={s} onClick={() => setSortBy(s)} style={{ ...pill(sortBy === s), fontSize: 11, padding: "3px 8px" }}>
              {SORT_LABELS[lang][s]}
            </button>
          ))}
        </div>

        <div style={{ fontSize: 11, color: "#4b5563", marginBottom: 8 }}>
          {filtered.length} {UI_TEXT[lang].decks}
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 8 }}>
          {filtered.map(deck => <DeckCard key={deck.id} deck={deck} lang={lang} />)}
        </div>

        {filtered.length === 0 && (
          <div style={{ textAlign: "center", padding: 40, color: "#4b5563", fontSize: 13 }}>
            {UI_TEXT[lang].empty}
          </div>
        )}
      </main>

      <footer style={{ borderTop: "1px solid #1a1a3a", padding: 16, marginTop: 40, textAlign: "center" }}>
        <p style={{ fontSize: 10, color: "#374151", margin: 0 }}>
          This is an unofficial fan site and is not affiliated with or endorsed by Blizzard Entertainment.
        </p>
      </footer>
    </div>
  );
}
