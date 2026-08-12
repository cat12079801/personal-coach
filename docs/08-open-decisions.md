# 08. 未決定の設計判断

制約（[03-constraints.md](03-constraints.md)）では決まりきらず、実装中に判断が必要になったもの。

---

## OD-1: メニュー再生成のリクエストを誰が拾うか

**状態:** ⬜ 未決定（マイルストーン 6 で決める）

PWA は `regenerate_requests` に 1 行入れるところまで実装済み
（[0003_regenerate_requests.sql](../supabase/migrations/0003_regenerate_requests.sql)）。
**このリクエストを処理する側はまだ無い。**

独自バックエンドを持たない方針なので、PWA から直接 GitHub Actions を起動することはできない
（`workflow_dispatch` を叩くにはトークンが要るが、フロントに置けば公開されてしまう）。

### 案 A: ポーリングするワークフローを足す（推奨）

15 分おきに起動し、未処理のリクエストがあれば再生成する。

- 実装が単純で、新しい資格情報が要らない
- public リポジトリなので実行時間は無料
- 反映は最大 15 分待ち。無駄な起動が 1 日 96 回

### 案 B: Supabase Database Webhook から `repository_dispatch` を叩く

`regenerate_requests` への INSERT をトリガーに、pg_net で GitHub API を呼ぶ。

- 即時に反映される。無駄な起動もない
- GitHub の PAT を Supabase Vault に置く必要がある。資格情報が 1 つ増える
- pg_net と Vault の設定が増え、動作確認の経路が長くなる

### 案 C: Edge Function を挟む

方針（「独自バックエンドは作らない」）に反するので採らない。

> 案 A で始め、待ち時間が実際に不便なら案 B に移す。

---

## OD-2: PWA のログイン方式

**状態:** ✅ 決定（Google OAuth のみ）

当初はメール + パスワードを暫定で入れていたが、成立しないことが判明した。
相乗り先の count-upper が Google SSO を使っており、対象アカウント（`auth.users` の行）は
Google の identity に紐づくだけで**パスワードを持たない**ため。

- Google provider はプロジェクト側で既に有効。追加設定は不要
- count-upper は Next.js のサーバルートで認可コードを交換しているが、こちらは静的 SPA な
  ので `detectSessionInUrl`（PKCE）でブラウザ側で交換する
- `Authentication > URL Configuration > Redirect URLs` に戻り先の許可が必要

### 残る懸念: iOS のホーム画面 PWA での OAuth

standalone 表示の PWA から OAuth に飛ぶと、戻りが PWA ではなく Safari になることがある。
実機で確認する（マイルストーン 5）。

問題が出た場合の緩和策:

- セッションは localStorage に永続化され自動リフレッシュされるので、**ログインは事実上初回のみ**。
  日常運用では OAuth の往復が発生しない
- それでも詰まるならマジックリンクを検討する

---

## OD-3: 手動ログの jsonb スキーマ

**状態:** 🚧 暫定

[logs/+page.svelte](../web/src/routes/logs/+page.svelte) の `FIELDS` が実体。
運用しながら項目を足し引きする前提で、DB 側は `jsonb` のままにしてある。

---

## OD-4: ボルダリングの RPE をどこで入れるか

**状態:** ⬜ 未決定

ボルダリングを Garmin 記録に切り替えたため、手動ログが無くなり **RPE の入力先が消えた**。
一方でボルダリングの心拍は信用できないので、負荷を測るには主観強度が要る。

- Garmin のアクティビティには主観的な運動強度（Feel / Effort）を入れる欄がある。
  `activities.raw` に入ってくるかを PoC-2 で確認する
- 入っていればそれを使う。入っていなければ、負荷指標からボルダリングを外すだけにする

---

## OD-5: 筋トレのルールが Garmin コーチと重複している

**状態:** ⬜ 未決定（メニュー生成の実装前に決める）

PoC-1 で判明した。**Garmin コーチは筋トレまでスケジュールしている。**

```
supplementalSports: ["STRENGTH_TRAINING_BODYWEIGHT"]
```

しかも「ポイント練習の日は筋トレを入れない」を既にやっている。

| date | ラン | 筋トレ |
|---|---|---|
| 08-12 | ベース（AEROBIC_BASE） | ラン前のアクティベーション |
| 08-14 | 無酸素（ANAEROBIC_CAPACITY） | なし |
| 08-15 | ベース（AEROBIC_BASE） | コアスタビリティ2 |
| 08-17 | 乳酸閾値（LACTATE_THRESHOLD） | なし |

したがって当初のルール 3
「ランがポイント練習の日は筋トレを入れない、休養/イージーの日は筋トレを差し込む」は
**ほぼ Garmin 側で実現されている**。

ルール 1「コーチのプランは改変しない」と併せると、こちらで筋トレを足す余地は無い。

### 選択肢

- **A. ルール 3 を廃止する。** アプリは Garmin のプランをそのまま表示し、
  独自の付加はルール 2 / 4（スケート予定）とルール 5（readiness）に絞る
- **B. Garmin が筋トレを置かない日にだけ独自の筋トレを足す。**
  ただし休養日に足すのはコーチの意図（回復）に反する
- **C. Garmin の筋トレとは別枠で、器具を使う筋トレを自分の裁量で足す。**
  Garmin 側は自重（BODYWEIGHT）のみなので、棲み分けは成立する

> 実データを見た限り A が素直。C を採るなら「足していい日」の条件を決める必要がある。
