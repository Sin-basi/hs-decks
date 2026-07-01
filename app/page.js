"use client";

// 這是網站首頁。它會讀取 ../data/decks.json 裡的牌組資料並顯示出來。
// 「use client」這一行一定要放在最上面，因為這個頁面有互動功能（篩選、複製按鈕、展開卡表）。

import { useState, useMemo } from "react";
import decksData from "../data/decks.json";

// ── 主題色（黑／鐵灰為主，橘色作強調，走簡約黑/橘對比）──
const BG = "#0d0d0f";        // 頁面底
const PANEL = "#161619";     // 卡片底
const PANEL2 = "#1e1e22";    // 卡表列底
const BORDER = "#2b2b30";    // 鐵灰邊框
const TEXT = "#ededed";      // 主要文字
const MUTED = "#8a8a90";     // 次要文字
const FAINT = "#5c5c63";     // 更淡的文字
const ACCENT = "#ff7a1a";    // 橘色強調
const OK = "#3f9d52";        // 「已複製」用的綠

// 每個職業的代表色（只用在卡片頂端的細色條，作職業識別）
const CLASS_COLORS = {
  Mage: "#3C9BF0", Warrior: "#C41E3A", Shaman: "#0070DE",
  Priest: "#A2ABB3", Paladin: "#F48CBA", Druid: "#FF7C0A",
  Hunter: "#AAD372", Rogue: "#E8D44D", Warlock: "#8788EE",
  "Demon Hunter": "#A330C9", "Death Knight": "#6AB8C6",
};

const CLASSES = ["all", "Druid", "Hunter", "Mage", "Paladin", "Priest", "Rogue", "Shaman", "Warlock", "Warrior", "Demon Hunter", "Death Knight"];
const FORMATS = ["all", "Standard", "Wild"];

// 三語系的介面文字
const CLASS_NAMES = {
  zh: { all: "全部", Druid: "德魯伊", Hunter: "獵人", Mage: "法師", Paladin: "聖騎士", Priest: "牧師", Rogue: "盜賊", Shaman: "薩滿", Warlock: "術士", Warrior: "戰士", "Demon Hunter": "惡魔獵人", "Death Knight": "死亡騎士" },
  en: { all: "All", Druid: "Druid", Hunter: "Hunter", Mage: "Mage", Paladin: "Paladin", Priest: "Priest", Rogue: "Rogue", Shaman: "Shaman", Warlock: "Warlock", Warrior: "Warrior", "Demon Hunter": "Demon Hunter", "Death Knight": "Death Knight" },
  ja: { all: "全て", Druid: "ドルイド", Hunter: "ハンター", Mage: "メイジ", Paladin: "パラディン", Priest: "プリースト", Rogue: "ローグ", Shaman: "シャーマン", Warlock: "ウォーロック", Warrior: "ウォリアー", "Demon Hunter": "デモンハンター", "Death Knight": "デスナイト" },
};
const FORMAT_NAMES = {
  zh: { all: "全部", Standard: "標準", Wild: "狂野" },
  en: { all: "All", Standard: "Standard", Wild: "Wild" },
  ja: { all: "全て", Standard: "スタンダード", Wild: "ワイルド" },
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

// 卡牌清單相關
const CARDS_LABEL = { zh: "張卡牌", en: "cards", ja: "枚のカード" };
const RARITY_COLORS = { LEGENDARY: "#ff9a3c", EPIC: "#b07de0", RARE: "#6aa0d8", COMMON: "#dcdce0", FREE: "#dcdce0" };
const LANG_TO_NAMEKEY = { zh: "name_zhTW", en: "name_en", ja: "name_jaJP" };

function cardName(card, lang) {
  return card[LANG_TO_NAMEKEY[lang]] || card.name_en || `#${card.id}`;
}

function tileUrl(card) {
  return card.cardId ? `https://art.hearthstonejson.com/v1/tiles/${card.cardId}.png` : null;
}

function timeSince(dateStr, lang) {
  const hours = Math.floor((new Date() - new Date(dateStr)) / 3600000);
  if (hours < 1) return { zh: "剛剛", en: "just now", ja: "たった今" }[lang];
  if (hours < 24) return lang === "en" ? `${hours}h ago` : `${hours} 小時前`;
  const days = Math.floor(hours / 24);
  return lang === "en" ? `${days}d ago` : `${days} 天前`;
}

// 一列卡牌（主牌與副牌共用）。side=true 時為副牌（E.T.C./Zilliax），縮排 + 橘色左條。
function CardRow({ card, lang, side }) {
  return (
    <div style={{
      position: "relative", height: side ? 27 : 30, borderRadius: 3, overflow: "hidden",
      display: "flex", alignItems: "center",
      background: side ? "#111113" : PANEL2,
      marginLeft: side ? 14 : 0,
      borderLeft: side ? `2px solid ${ACCENT}` : "none",
    }}>
      {tileUrl(card) && (
        <img src={tileUrl(card)} alt="" loading="lazy" style={{
          position: "absolute", right: 0, top: 0, height: "100%", width: "62%",
          objectFit: "cover",
          WebkitMaskImage: "linear-gradient(to right, transparent, #000 55%)",
          maskImage: "linear-gradient(to right, transparent, #000 55%)",
        }} />
      )}
      <span style={{ position: "relative", zIndex: 1, width: 24, textAlign: "center", color: "#cfcfd4", fontWeight: 700, fontSize: side ? 12 : 14 }}>
        {card.cost}
      </span>
      <span style={{
        position: "relative", zIndex: 1, flex: 1, minWidth: 0,
        fontSize: side ? 12 : 13, fontWeight: 500,
        color: RARITY_COLORS[card.rarity] || "#dcdce0",
        textShadow: "0 1px 3px #000, 0 0 5px #000",
        whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", paddingRight: 4,
      }}>
        {cardName(card, lang)}
      </span>
      <span style={{ position: "relative", zIndex: 1, width: 26, textAlign: "center", fontSize: 12, fontWeight: 700, color: card.count >= 2 ? ACCENT : MUTED }}>
        {card.count >= 2 ? "×2" : ""}
      </span>
    </div>
  );
}

function DeckCard({ deck, lang }) {
  const [copied, setCopied] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const classColor = CLASS_COLORS[deck.hero_class.en] || "#888";
  const t = UI_TEXT[lang];
  const sideboard = deck.sideboard || [];

  const handleCopy = () => {
    navigator.clipboard.writeText(deck.deckstring).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };

  return (
    <div style={{ background: PANEL, borderRadius: 7, overflow: "hidden", border: `1px solid ${BORDER}` }}>
      <div style={{ height: 3, background: classColor }} />
      <div style={{ padding: "14px 16px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 7, gap: 8 }}>
          <span style={{ fontSize: 17, fontWeight: 700, color: TEXT }}>
            {deck.archetype || deck.hero_class[lang]}
          </span>
          <span style={{
            fontSize: 12, padding: "2px 8px", borderRadius: 4, fontWeight: 600, whiteSpace: "nowrap",
            background: deck.format.en === "Wild" ? "rgba(255,122,26,0.15)" : "#26262b",
            color: deck.format.en === "Wild" ? ACCENT : MUTED,
          }}>
            {deck.format[lang]}
          </span>
        </div>
        <div style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 9, flexWrap: "wrap" }}>
          <span style={{ fontSize: 14, color: TEXT, fontWeight: 600 }}>{deck.hero_class[lang]}</span>
          {deck.legend_rank && <span style={{ fontSize: 14, color: ACCENT, fontWeight: 600 }}>#{deck.legend_rank}</span>}
          {deck.winrate && deck.winrate.winrate && (
            <span style={{ fontSize: 14, fontWeight: 600, color: deck.winrate.winrate >= 60 ? ACCENT : MUTED }}>
              {deck.winrate.winrate}%
              {deck.winrate.wins != null && (
                <span style={{ color: FAINT, fontWeight: 400 }}> ({deck.winrate.wins}-{deck.winrate.losses})</span>
              )}
            </span>
          )}
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12, gap: 8 }}>
          <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
            {deck.dust_cost ? <span style={{ fontSize: 13, color: MUTED }}>{deck.dust_cost.toLocaleString()} 塵</span> : null}
            {deck.source && deck.source.author ? <span style={{ fontSize: 13, color: FAINT }}>{UI_TEXT[lang].by} {deck.source.author}</span> : null}
          </div>
          {deck.collected_at && <span style={{ fontSize: 12, color: FAINT, whiteSpace: "nowrap" }}>{timeSince(deck.collected_at, lang)}</span>}
        </div>
        <button onClick={handleCopy} style={{
          width: "100%", padding: "9px 0", borderRadius: 5, border: "none",
          background: copied ? OK : ACCENT, color: copied ? "#fff" : "#141414",
          fontSize: 14, fontWeight: 700, cursor: "pointer",
        }}>
          {copied ? t.copied : t.copy}
        </button>

        {deck.cards && deck.cards.length > 0 && (
          <>
            <button onClick={() => setExpanded((v) => !v)} style={{
              width: "100%", padding: "7px 0", marginTop: 5, borderRadius: 5,
              border: `1px solid ${BORDER}`, background: "transparent",
              color: MUTED, fontSize: 13, cursor: "pointer",
            }}>
              {expanded ? "▴ " : "▾ "}{deck.cards.length} {CARDS_LABEL[lang]}
            </button>
            {expanded && (
              <div style={{ marginTop: 7, display: "flex", flexDirection: "column", gap: 2 }}>
                {deck.cards.map((c, i) => {
                  const band = sideboard.filter((s) => s.owner === c.id);
                  return (
                    <div key={i} style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                      <CardRow card={c} lang={lang} />
                      {band.map((s, j) => <CardRow key={j} card={s} lang={lang} side />)}
                    </div>
                  );
                })}
              </div>
            )}
          </>
        )}
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
    padding: "6px 12px", borderRadius: 5, border: `1px solid ${active ? ACCENT : BORDER}`,
    background: active ? ACCENT : "transparent", color: active ? "#141414" : MUTED,
    fontSize: 14, cursor: "pointer", fontWeight: active ? 700 : 500, whiteSpace: "nowrap",
  });

  return (
    <div style={{ fontFamily: "'Noto Sans TC', 'Inter', sans-serif", background: BG, color: TEXT, minHeight: "100vh" }}>
      <header style={{ borderBottom: `1px solid ${BORDER}`, padding: "14px 16px" }}>
        <div style={{ maxWidth: 760, margin: "0 auto", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h1 style={{ fontSize: 20, fontWeight: 800, color: TEXT, margin: 0, letterSpacing: 0.5 }}>
            HS <span style={{ color: ACCENT }}>Decks</span>
          </h1>
          <div style={{ display: "flex", gap: 5 }}>
            {["zh", "en", "ja"].map(l => (
              <button key={l} onClick={() => setLang(l)} style={{ ...pill(lang === l), padding: "3px 11px", fontSize: 13 }}>
                {l === "zh" ? "中" : l === "en" ? "EN" : "日"}
              </button>
            ))}
          </div>
        </div>
      </header>

      <main style={{ maxWidth: 760, margin: "0 auto", padding: "14px 16px" }}>
        <div style={{ display: "flex", gap: 6, marginBottom: 8, flexWrap: "wrap" }}>
          {FORMATS.map(f => (
            <button key={f} onClick={() => setFormatFilter(f)} style={pill(formatFilter === f)}>
              {FORMAT_NAMES[lang][f]}
            </button>
          ))}
        </div>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 8 }}>
          {CLASSES.map(c => (
            <button key={c} onClick={() => setClassFilter(c)} style={pill(classFilter === c)}>
              {CLASS_NAMES[lang][c]}
            </button>
          ))}
        </div>
        <div style={{ display: "flex", gap: 6, marginBottom: 14, flexWrap: "wrap" }}>
          {["time", "rank", "winrate", "dust"].map(s => (
            <button key={s} onClick={() => setSortBy(s)} style={{ ...pill(sortBy === s), fontSize: 13, padding: "5px 11px" }}>
              {SORT_LABELS[lang][s]}
            </button>
          ))}
        </div>

        <div style={{ fontSize: 13, color: MUTED, marginBottom: 10 }}>
          {filtered.length} {UI_TEXT[lang].decks}
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: 10 }}>
          {filtered.map(deck => <DeckCard key={deck.id} deck={deck} lang={lang} />)}
        </div>

        {filtered.length === 0 && (
          <div style={{ textAlign: "center", padding: 40, color: MUTED, fontSize: 15 }}>
            {UI_TEXT[lang].empty}
          </div>
        )}
      </main>

      <footer style={{ borderTop: `1px solid ${BORDER}`, padding: 16, marginTop: 40, textAlign: "center" }}>
        <p style={{ fontSize: 12, color: FAINT, margin: 0 }}>
          This is an unofficial fan site and is not affiliated with or endorsed by Blizzard Entertainment.
        </p>
      </footer>
    </div>
  );
}
