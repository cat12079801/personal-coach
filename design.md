# design.md — personal-coach のデザインシステム

**このファイルがシステムの正である。** 画面ごとに違う顔を作らない。7 画面すべてが
ここに書かれた 1 つのシステムを共有する。実体は
[web/src/tokens.css](web/src/tokens.css) と [web/src/app.css](web/src/app.css)。

Hallmark（`~/.claude/skills/hallmark`）の規則に沿って作った。監査結果は
[docs/11-design-audit.md](docs/11-design-audit.md)。

## 前提

| | |
|---|---|
| 使う人 | 本人 1 人。ラン・スケート・自重の記録を毎日見る |
| 用途 | **朝 08:00 の通知から開いて 5 秒で今日の量を把握し、実施したら完了を押す** |
| トーン | **競技（utilitarian-sport）**。スコアボードと台帳。装飾はしない |
| 環境 | iOS のホーム画面 PWA が主。375px を基準に 320〜768px で崩さない |
| macrostructure | Stat-Led（数字が先、言葉がそれを説明する） |

「今日やる量」が数字として最初に目に入ることを最優先する。読み物にしない。

## 色

anchor hue は暖色（60 前後）。accent は朱（32）を 1 色だけ。

- **純白・純黒を使わない。** すべて anchor hue へわずかに寄せる
- **accent は面の 3% を超えない。** 塗るのは ink。accent は readiness・現在タブ・
  リンク・強調の下線に限る
- **accent を塗った面に白を置かない。** 暗色モードで 2.7:1 まで落ちる（実測）。
  必ず `--color-accent-ink` を使う
- 暗色モードは hue を変えない。lightness と chroma だけ動かす

実測したコントラスト（375px・design mode・2026-08-13）:

| | light | dark |
|---|---|---|
| ラベル（muted） | 6.8 | 7.3 |
| readiness（accent） | 6.0 | 7.4 |
| 本文・見出し | 15.9 | 16.3 |
| 完了済み（good） | 6.4 | 8.2 |
| バッジ | 6.2 | 7.2 |

## 書体

**2 つ。display と body だけ。**

| 役割 | 書体 | 使う場所 |
|---|---|---|
| display | Big Shoulders Display（700） | 数字・英字ラベル・見出し・タブのバッジ |
| body | システム（Hiragino Sans / Noto Sans JP） | 和文すべて |

**和文の Web フォントは入れない。** 数 MB あり PWA の初回起動を壊す。したがって
display は**欧文と数字にだけ効く**。これは妥協ではなく役割分担として設計している
（データは display、言葉は system）。

- 数値を並べる場所は必ず `font-variant-numeric: tabular-nums`（`.num` / `input[type=number]`）
- 英字ラベルは大文字・`letter-spacing: 0.12em`。**和文に大文字化やトラッキングを掛けない**
- 大きさは 1.25 の等比（`--text-xs` 〜 `--text-2xl`）。1 画面で 5 段階まで

## 余白・罫線・角

- 余白は 4pt スケール（`--space-2xs` 〜 `--space-2xl`）。**リテラルの rem を書かない**
- **囲い（カード）は 1 層まで。** 既定は「罫線で区切られた行」であって箱ではない。
  箱にしたいときだけ `.panel` を使う
- 角は立てる（`--radius-none`）。丸めるのはバッジだけ（`--radius-pill`）
- 罫線は 3 段階（`--rule-hair` / `--rule-bold` / `--rule-heavy`）。
  見出しの下だけ heavy、行の区切りは hair

## 動き

- ブラウザ既定の `ease` を使わない。`--ease-out` / `--ease-in` / `--ease-in-out` の 3 本
- 動かすのは `transform` と `opacity` だけ
- **フォーカスの輪郭にトランジションを掛けない。** 遅れて出る輪郭は無いのと同じ
- `prefers-reduced-motion: reduce` で 150ms に畳む

## 操作子

**8 状態すべてを持たせる**（default / hover / focus / active / disabled / loading /
error / success）。触れる要素は 44px を下回らせない。

- hover は `@media (hover: hover)` の中だけ（触るだけで hover が残る端末があるため）
- 入力の枠の太さはどの状態でも変えない。フォーカスの輪郭ぶんの席を透明で確保しておく
- ラベルは入力の上に置く。プレースホルダをラベル代わりにしない
- 取り消せる操作に確認ダイアログを出さない

## 画面の組み

| 画面 | 組み |
|---|---|
| `/` 今日 | スコアボード（日付 + readiness）→ 要約 → 台帳の行（ラベル / 名前 / 数字）。主役 |
| `/activities` `/unlinked` | 台帳の行に徹する。数字は右端で揃える |
| `/logs` `/programs` `/settings` | 入力と設定。`.panel` を使ってよい唯一の場所 |
| `/notifications` | 履歴の行。未読は accent の点で示す |

**主役は「今日」だけ。** ほかの画面は同じ部品で静かに組む。

## やらないこと

- 紫・青のグラデーション、ぼかした円、ガラス風の面
- 影で浮かせる表現（暗色では明度で階層を作る）
- 無い数字を作ること（readiness が無い日は出さない。`—` にする）
- 絵文字をアイコン代わりに使うこと
- 記号の混在（`✓` は完了だけ、`＋`/`−` は使わず言葉にする）
