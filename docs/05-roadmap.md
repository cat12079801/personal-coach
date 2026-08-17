# 05. 実装順序とマイルストーン

**この順で進める**。順序には理由がある（下記「順序の根拠」を参照）。

| # | マイルストーン | 状態 | 成果物 |
|---|---|---|---|
| 1 | Garmin 認証 + トークンの Supabase 往復 | ✅ | `garmin/auth.py`, `scripts/bootstrap_garmin_token.py` |
| 2 | Garmin コーチのプラン取得 PoC | ✅ | `scripts/poc_*.py` → [06-poc-notes.md](06-poc-notes.md) |
| 3 | 取り込みバッチ → Supabase | ✅ | `garmin/sync.py`, `garmin/sports.py`, `ingest.py` |
| 4 | PWA | ✅ | `web/` → https://personal-coach-6z2.pages.dev |
| 5 | Web Push | ✅ | `push/sender.py`, `web/src/lib/push.ts`, `web/static/sw.js` |
| 6 | メニュー生成ロジック | ✅ | `menu/rules.py`, `menu/build.py`, `garmin/plan.py` |
| 7 | keepalive と失敗通知 | ✅ | `.github/workflows/` |

**全マイルストーン完了（2026-08-12）。** 03:00 JST の取り込み・生成と 08:00 JST の通知が
GitHub Actions で自動実行される状態にある。

## 現在の運用状態

| | |
|---|---|
| 本番 PWA | https://personal-coach-6z2.pages.dev |
| DB | 既存 Supabase プロジェクトの `coach` スキーマに相乗り（[ADR-0006](adr/0006-share-existing-supabase-project.md)） |
| 取り込み済み | activities 50 件（直近ぶんのみ。全履歴は未） |
| 筋トレプログラム | 3 種目・週 3 回で登録済み（[10-strength-programs.md](10-strength-programs.md)） |
| GitHub Secrets | Supabase 2 つ + VAPID 3 つ。カレンダーと Discord は未登録 |

## 残っている作業

優先度順ではなく、どれも任意。マイグレーションは 0008 まで適用済み（2026-08-13 に確認）。

- **完了記録の UI 調整** — セット数とレップ数／秒数は編集できるが、RPE とメモは
  メニュー画面から入れられない（列はあるので後から足せる）。重量も未対応
- **`GOOGLE_CALENDAR_ICS_URL` の登録** — 入れると当日の予定がメニューに載る。
  未設定でも「予定なし」として動く
- **`DISCORD_WEBHOOK_URL` の登録** — バッチ失敗時の通知。未設定だと失敗に気付けない
- **全履歴のバックフィル** — `BACKFILL_PAGES=5` などで遡る。現在は直近 50 件
- **筋トレの動きの図をアプリに載せる** — 現在は
  [確認用ページ](https://claude.ai/code/artifact/6f7af65b-f244-4b79-b7c9-c8dbf21ebc5b)にしか無く、
  アプリはテキストのみ。段階ごとの SVG を `stages[].figure` に持たせるなどの案がある
- **実際に失敗通知が飛ぶことの確認**
- **PWA の実データ目視確認** — データは入っているが全画面の目視は未

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

- [x] バッチが secret key で `coach` スキーマに読み書きできる
      （`garmin_tokens` の書き込み → 読み戻し → 削除を確認済み）
- [x] ローカルでログインでき、`garmin_tokens` に初期値が入る
- [x] DB のトークンだけで（パスワードなしで）ログインできる
- [x] リフレッシュ後のトークンが DB に書き戻される
      （`Client.dump()` の呼び出しを修正。旧実装は `garth.dump()` を叩いて失敗していた）
- [x] GitHub Actions 上（非対話）で 1 回成功する（2026-08-12）
      DB のトークンだけでログインでき、Garmin 側の bot 検知にもレート制限にも当たらなかった

### 2. Garmin コーチのプラン取得 PoC

- [x] `get_training_plans()` / `get_scheduled_workouts()` /
      `get_adaptive_training_plan_by_id()` の生 JSON をダンプした
- [x] どの API がコーチのプランを返すか特定した
      （`get_adaptive_training_plan_by_id()` の `taskList`）
- [x] 「ポイント練習 / イージー / 休養」をどのフィールドで判定するか決めた
      （`trainingEffectLabel` と `restDay`）
- [x] `get_activity_types()` でボルダリング・フィギュアの `type_key` を確認した
      （ボルダリングは未記録のため未確定。クライミング系 4 つをまとめて扱う）
- [x] PoC-1 の結果を [06-poc-notes.md](06-poc-notes.md) に記録した

### 3. 取り込みバッチ → Supabase

- [x] 差分同期（既知 ID で打ち切り）
- [x] `raw` を保存している
- [x] ラン splits の 2 段目ジョブ
- [x] クライミング系・スケートの詳細（RPE / Feel）を追う 3 段目ジョブ
- [x] 429 を握って指数バックオフする
- [x] 初回バックフィルをページ数で区切れる（`BACKFILL_PAGES`）
- [x] **実データで流した**（activities 50 / running_details 33 / splits 33 / 詳細 20）
- [x] RPE / Feel が入ることを確認した（rpe 4〜9、feel 50/75/100）
- [ ] 初回バックフィルで全履歴を取り込む（現在は直近 50 件のみ）

### 4. PWA

- [x] Supabase を `supabase-js` で直接読んで一覧表示できる
- [x] ~~未紐付けアクティビティ一覧がある~~（0008 で廃止）
- [x] 手動ログ（筋トレ）を登録できる（スケートは 0008 で廃止）
- [x] 「メニュー再生成」ボタンがある（依頼を積む。拾う側は OD-1 で実装済み）
- [ ] 実データで表示を確認した（データは入っている。目視確認が未）
- [x] Cloudflare Pages にデプロイできている（https://personal-coach-6z2.pages.dev）
- [x] SPA の書き戻しが効いている（`/activities` 直開きで 200）
- [x] manifest が `standalone` で配信され、apple-touch-icon が入っている

### 5. Web Push

- [x] `manifest.webmanifest` の `display` が `standalone`
- [x] 許可要求をクリックハンドラから直接呼んでいる
- [x] `userVisibleOnly: true`
- [x] Service Worker が `push` で必ず `showNotification()` を呼ぶ
- [x] 404/410 で購読を削除する処理が入っている
- [x] PWA 起動時の再購読が入っている
- [x] 未読カウンタと通知履歴一覧がある
- [x] **ホーム画面追加 → 許可要求 → 購読登録が iOS 実機で通る**
- [x] **テスト送信が iOS 実機に届く**
- [x] **standalone の PWA から Google OAuth で戻ってこられる**（OD-2 の懸念は解消）

2026-08-12 に iPhone 実機で確認した。診断の結果は次のとおり。

```
standalone: true / permission: granted / vapid: 設定済み(87文字)
serviceWorker: active / subscription: web.push.apple.com / keys: あり / dbRows: 1 件
```

### 実機で見つかった不具合

- `register()` が installing 状態の registration を返し、active になる前に
  `pushManager.subscribe()` を呼んで失敗していた → `navigator.serviceWorker.ready` を待つ
- `persist()` が upsert のエラーを握りつぶしており、保存に失敗しても UI は成功に見えた
  → 例外にした

どちらも「UI 上は成功しているのに `push_subscriptions` が空」という形で出た。
**iOS の Web Push は失敗が見えにくいので、保存の成否を必ず表面化させること。**

### 6. メニュー生成ロジック

- [x] ルール R1〜R4（[01-overview.md](01-overview.md)）を実装した。本人レビュー済み
- [x] `daily_menus.source` に生成根拠を残している（適用ルール・種目ごとの判定理由）
- [x] 当日のカレンダー予定をメニューに載せる（表示用。ルールには使わない）
- [x] PoC の実データ 1 週間ぶんでドライランして配置を目視確認した
- [x] 実データで生成した（2026-08-12: ベース 61 分 + ラン前のアクティベー）
- [x] 独自筋トレの段階を管理する UI（`/programs`）。種目の CRUD、段階の追加・並べ替え、
      現在段階の上げ下げ、週の回数と最短間隔の設定
- [x] 「メニュー再生成」ボタンから手動リカバリできる（OD-1 案 A。15 分おきの
      `regenerate.yml` が拾い、Garmin を引き直して作り直す）

### 7. keepalive と失敗通知

- [x] 41 日経過で日付マーカーをコミットするステップ
- [x] `if: failure()` で Discord Webhook に通知
- [x] `timeout-minutes` 設定
- [ ] 実際に失敗通知が飛ぶことを確認した
