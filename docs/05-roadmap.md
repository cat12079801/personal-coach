# 05. 実装順序とマイルストーン

**この順で進める**。順序には理由がある（下記「順序の根拠」を参照）。

| # | マイルストーン | 状態 | 成果物 |
|---|---|---|---|
| 1 | Garmin 認証 + トークンの Supabase 往復 | 🚧 スケルトンあり | `batch/src/personal_coach/garmin/auth.py`, `scripts/bootstrap_garmin_token.py` |
| 2 | Garmin コーチのプラン取得 PoC | ⬜ 未着手 | `batch/scripts/poc_*.py` → [06-poc-notes.md](06-poc-notes.md) |
| 3 | 取り込みバッチ → Supabase | ⬜ 未着手 | `garmin/sync.py`, `ingest.py` |
| 4 | PWA | 🚧 実装済・実データ未検証 | `web/` |
| 5 | Web Push（実機検証まで） | 🚧 コードのみ・実機未検証 | `push/sender.py`, `web/src/lib/push.ts`, `web/static/sw.js` |
| 6 | メニュー生成ロジック | ⬜ 未着手 | `menu/rules.py` |
| 7 | keepalive と失敗通知 | ✅ ワークフローに組込済 | `.github/workflows/` |

## 順序の根拠

### 1 が最初 — ここが動かなければ何も始まらない

Garmin にログインできてトークンが往復しなければ、以降のすべてが成立しない。
非対話環境（GitHub Actions）で MFA を越えられることをここで確認する。

### 2 を 3 より先にやる — 設計が変わりうる唯一の未知だから

Garmin コーチのプランがどの API から、どういう形で取れるかが不明。
この結果で**メニュー生成ロジックの入力が決まる**ため、他より先に潰す。

ここを後回しにすると、3〜6 を作った後に作り直しになる可能性がある。

### 5 を後回しにしない — iOS の制約は実機でしか確認できない

ホーム画面追加 → 許可 → テスト送信までを**最小構成で実機検証**する。
[03-constraints.md](03-constraints.md) の iOS Web Push 制約は、
実機で試すまで本当に踏んでいないか分からない類のもの。

### 6 が最後 — 入力が全部揃ってから書く

メニュー生成は「Garmin コーチのプラン」「training_readiness」「カレンダー」の 3 つを入力にする。
3 つとも揃うまで書かない。推測で書くと必ず作り直しになる。

## 各マイルストーンの完了条件

### 1. Garmin 認証 + トークンの Supabase 往復

- [ ] ローカルで MFA を越えてログインでき、`garmin_tokens` に初期値が入る
- [ ] DB のトークンだけで（パスワードなしで）ログインできる
- [ ] リフレッシュ後のトークンが DB に書き戻される
- [ ] GitHub Actions 上（非対話）で 1 回成功する

### 2. Garmin コーチのプラン取得 PoC

- [ ] `get_training_plans()` / `get_scheduled_workouts()` /
      `get_adaptive_training_plan_by_id()` の生 JSON をダンプした
- [ ] どの API がコーチのプランを返すか特定した
- [ ] 「ポイント練習 / イージー / 休養」をどのフィールドで判定するか決めた
- [ ] `get_activity_types()` でボルダリング・フィギュアの `type_key` を確認した
- [ ] 結果を [06-poc-notes.md](06-poc-notes.md) に記録した

### 3. 取り込みバッチ → Supabase

- [ ] 差分同期（既知 ID で打ち切り）が動く
- [ ] `raw` を保存している
- [ ] ラン splits の 2 段目ジョブが動く
- [ ] 429 を握って指数バックオフする
- [ ] 初回バックフィルが完走する

### 4. PWA

- [x] Supabase を `supabase-js` で直接読んで一覧表示できる
- [x] 未紐付けアクティビティ一覧がある
- [x] 手動ログ（ボルダリング / 筋トレ / スケート）を登録できる
- [x] 「メニュー再生成」ボタンがある（依頼を積むところまで。OD-1 参照）
- [ ] 実データで表示を確認した（Supabase の構築待ち）
- [ ] Cloudflare Pages にデプロイできている

### 5. Web Push

- [x] `manifest.webmanifest` の `display` が `standalone`
- [x] 許可要求をクリックハンドラから直接呼んでいる
- [x] `userVisibleOnly: true`
- [x] Service Worker が `push` で必ず `showNotification()` を呼ぶ
- [x] 404/410 で購読を削除する処理が入っている
- [x] PWA 起動時の再購読が入っている
- [x] 未読カウンタと通知履歴一覧がある
- [ ] **ホーム画面追加 → 許可要求 → 購読登録が iOS 実機で通る**
- [ ] **テスト送信が iOS 実機に届く**

実機検証だけが残っている。iOS の制約は実機でしか確認できないので、
Cloudflare Pages へのデプロイ後すぐにここを潰す。

### 6. メニュー生成ロジック

- [ ] 5 つのルール（[01-overview.md](01-overview.md)）を実装した
- [ ] `daily_menus.source` に生成根拠を残している
- [ ] 「メニュー再生成」ボタンから手動リカバリできる

### 7. keepalive と失敗通知

- [x] 41 日経過で日付マーカーをコミットするステップ
- [x] `if: failure()` で Discord Webhook に通知
- [x] `timeout-minutes` 設定
- [ ] 実際に失敗通知が飛ぶことを確認した
