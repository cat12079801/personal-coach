# 11. デザイン監査（2026-08-13）

Hallmark の `audit` を `web/src` に当てた結果と、その後の対応。
システムは [design.md](../design.md) が正である。

監査時点の判定は **6 critical · 5 major · 4 minor / reads as AI-generated**。
原因は装飾ではなく**判断の不在**だった（紫グラデ・偽ブラウザ枠・捏造メトリクス・
イタリック見出し・eyebrow はいずれも無かった）。

## critical

| 指摘 | 対応 |
|---|---|
| 純白の面と hex パレット（`#ffffff` / `#f7f8f9`） | ✅ OKLCH に移し anchor hue へ寄せた |
| 単一書体（system のみ、ペアリング無し） | ✅ display（Big Shoulders Display）を追加。和文は system のまま |
| `:focus-visible` が 1 件も無い | ✅ 全体に 2px の輪郭。トランジションは掛けない |
| 塗りボタンのコントラスト不足（dark で 2.70 / 2.52 と実測） | ✅ `--color-accent-ink` を導入。暗色では accent の上に暗い文字を置く |
| Card-in-card（`.card` の中に `.card`） | ✅ `.card` を「罫線で区切られた行」に変更。箱は `.panel` だけ |
| 7 画面が同一の構造フィンガープリント | 🚧 「今日」を Stat-Led で組み直した。残り 6 画面は未着手 |

## major

| 指摘 | 対応 |
|---|---|
| スペーシングスケール不在・インライン style での場当たり | ✅ 4pt トークン。「今日」からインライン style を排除。他画面に残 |
| モーショントークンと状態フィードバックが無い | ✅ easing 3 本・duration 3 本・reduced-motion・8 状態 |
| 数値に `tabular-nums` が無い | ✅ `.num` と `input[type=number]` に付与。他画面の適用は残 |
| 見出しの階層が反転（`h2` が本文より弱い） | ✅ `h2` を display のトラッキング付きラベルにした |
| 下部ナビが 11.2px のテキストのみ | ✅ 12.8px・現在タブに accent の帯・バッジを分離 |

## minor

角丸の不統一（✅ トークン化・原則 0）／記号の混在（🚧 `＋` `−` は言葉に置換したが `✓` は残す）／
すべてのカードが同じ余白（✅ 行と `.panel` で役割を分けた）／`:active` の素の opacity（✅ トークン化）

## 実測で通っていたもの

320px で横スクロール無し・クリック要素の 2 行折り返し無し・タップ領域 44px 以上・
`z-index` は 1 のみ・`100vw` 無し。**再設計後も同じ条件で再測して維持を確認している**
（`summary` が 21px だったので 44px に直した）。

## 残り

- `/activities` `/unlinked` `/logs` `/programs` `/settings` `/notifications` の 6 画面を
  同じ部品に寄せる
- `/logs` の `.card` 入れ子を解消する
- display 書体を Google Fonts の CDN から読んでいる。オフライン優先なら
  woff2（Latin サブセット）を自前配信に切り替える
