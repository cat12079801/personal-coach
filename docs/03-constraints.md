# 03. 踏んではいけない制約

以下はすべて調査・検証済みの事実。ここを外すと設計が破綻するので厳守すること。
（特記なき場合、2026-08-10 時点の確認結果）

**この一覧に反する提案は採用しない。**「Workers で Garmin を叩く」「silent push を使う」
「OAuth でカレンダーを読む」等はすべて検討済みで却下されている。

---

## 1. Garmin 取り込みを Cloudflare / Supabase Edge Functions で動かすことはできない

`garminconnect` は `curl_cffi`（TLS フィンガープリント偽装のためのネイティブ C 拡張）に依存する。
Cloudflare Workers（JS/WASM）、Python Workers（Pyodide）、Supabase Edge Functions（Deno）の
いずれでも動作しない。

> **Garmin にアクセスする処理は必ず GitHub Actions 上の Python で実行する。**

素の fetch で Garmin API を叩き直す実装は行わないこと（bot 検知で弾かれる）。

→ [ADR-0001](adr/0001-batch-on-github-actions.md)

## 2. Garmin 公式 API は使えない

Garmin Connect Developer Program は法人限定で、個人利用の申請は却下される。
非公式ライブラリ以外の選択肢はない。

規約上グレーなので、**自分のアカウントの自分のデータを個人利用で取得する範囲に限定**し、
他人の資格情報を扱う設計にはしない。

2026 年 3 月に Garmin 側の認証変更でエコシステムが一斉に壊れた前例がある。
ライブラリの破壊的変更は起こる前提で、取り込み層を疎結合に保つこと。

→ [ADR-0002](adr/0002-no-garmin-official-api.md)

## 3. iOS の Web Push 制約

- **ホーム画面追加が必須。** Safari のタブでは通知の許可要求すらできない
- `manifest.json` の `display` は `standalone` にする（`browser` だと通知不可）
- `Notification.requestPermission()` は**クリックハンドラから直接**呼ぶ。
  `setTimeout` 経由は無視される
- `userVisibleOnly: true` は必須
- **silent push は不可。** `push` イベントで `showNotification()` を呼ばない push が数回続くと
  iOS はサブスクリプションを解除する。「裏でキャッシュだけ更新する」設計は取れない
- push でバックグラウンドコードを起動することはできない
- 端末再起動後にリスナーが発火しない、予期しない購読解除が起こる等の不安定さがある。
  送信時に **404/410 が返ったら DB から購読を削除**し、**PWA 起動時に再購読**する処理を必ず入れる
- Apple のプッシュサービスは VAPID の subject が不正な形式だと 403 を返す。
  `vapid_claims` の `sub` は `mailto:...` または `https://...` を正しく設定する

## 4. push ペイロードに本体を載せない

メニュー本体は 03:00 のバッチで Supabase に保存済み。push は**トリガーと短い要約のみ**を運ぶ。
PWA は起動時に必ず Supabase から当日のメニューを読む。

これにより「通知を消した」「通知が届かなかった」場合でも PWA を開けば同じ内容が見える。

**アプリ内に未読カウンタと通知履歴一覧を持たせること。**（iOS では推奨ではなく必須の作り）

→ [ADR-0004](adr/0004-push-payload-minimal.md)

## 5. GitHub Actions の 60 日自動無効化

public リポジトリでは、60 日間リポジトリ活動がないとスケジュールワークフローが自動無効化される。
（実行時間は public なので無料無制限）

> **コミット方式の keepalive を入れる。**
> 日次バッチの最後に「最終コミットから 41 日以上経過していれば `.github` 配下の
> 日付マーカーファイルを更新してコミットする」ステップを追加する。

`actions: write` 権限で API から再有効化する方式は、60 日タイマーがリセットされるか
確証がないため採用しない。

### public リポジトリなので Secrets の扱いに注意する

- `pull_request_target` は使わない
- ログにトークン、Supabase の service_role key、カレンダーの非公開 URL を出力しない
- `workflow_dispatch` の入力を無検証でシェルに渡さない

## 6. Google カレンダーは OAuth を使わない

個人 Google アカウントに対してサービスアカウントは使えず、通常の OAuth はテスト中ステータスだと
リフレッシュトークンが 7 日で失効し、本番公開にはカレンダースコープの審査が必要になる。

> **カレンダー設定の「非公開 URL（iCal 形式）」を fetch して `icalendar` でパースする。**
> 認証不要、失効なし。

この URL は実質的な認証情報なので GitHub Secrets に入れ、リポジトリには置かない。

**注意:** この .ics は Google 側でキャッシュされ反映が数時間遅れることがある。
前夜遅くに追加された予定を 03:00 のバッチが拾えない可能性があるため、
アプリ側に「**メニュー再生成**」ボタンを置いて手動リカバリできるようにする。

→ [ADR-0003](adr/0003-ical-instead-of-oauth.md)

## 7. Garmin トークンの永続化

トークンは自動リフレッシュされるので、リフレッシュ後の値を書き戻す先が必要。

> **Supabase に 1 行のテーブルを作って読み書きする**（GitHub Secrets を API 更新する方式は取らない）。

初回ログインは MFA の対話が必要なのでローカルで実施し、生成された
`~/.garminconnect/` 配下のトークンファイルの内容を初期値として DB に投入する。

→ [ADR-0005](adr/0005-garmin-token-in-supabase.md)
