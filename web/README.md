# web

PWA。SvelteKit（adapter-static）で静的ビルドし、Cloudflare Pages に配信する。

`supabase-js` で Supabase を直接読む。**独自バックエンドは作らない。**

既存プロジェクトに相乗りしているため、クライアントは `coach` スキーマを明示する
（[supabase.ts](src/lib/supabase.ts)）。省くと相手の `public` を見に行って 404 になる。

## 開発

```bash
cd web
npm install
cp .env.example .env.local   # 値を埋める
npm run dev
```

| コマンド | 内容 |
|---|---|
| `npm run dev` | 開発サーバ |
| `npm run build` | `build/` に静的出力 |
| `npm run check` | 型チェック（svelte-check） |

## Cloudflare Pages の設定

| 項目 | 値 |
|---|---|
| Root directory | `web` |
| Build command | `npm ci && npm run build` |
| Build output directory | `build` |

`build` は Root directory からの相対。もし "output directory not found" で失敗したら
`web/build` に変えて試す。

Node のバージョンは [.nvmrc](.nvmrc) で固定している。

ビルド環境変数に `VITE_SUPABASE_URL` / `VITE_SUPABASE_PUBLISHABLE_KEY` / `VITE_VAPID_PUBLIC_KEY`
を設定する。

### SPA の書き戻し

[static/_redirects](static/_redirects) で `/* /index.html 200` を指定している。
**これが無いと `/activities` を直接開いた場合やリロード時に 404 になる。**
クライアントサイドルーティングなので、実在するのは `/` だけである。

### デプロイ後にやること

Supabase の `Authentication > URL Configuration > Redirect URLs` に本番 URL を追加する。
追加しないと Google ログインから戻ってこられない。

publishable key（`sb_publishable_...`）はフロントに埋め込まれる公開値であり、秘密ではない。
データを守っているのは Supabase 側の RLS（`is_owner()`）だけである。

## 画面

| ルート | 内容 |
|---|---|
| `/` | 当日メニュー + 生成根拠 + 「メニュー再生成」ボタン |
| `/activities` | Garmin から取り込んだアクティビティ一覧 |
| `/unlinked` | 未紐付けアクティビティ。ここから手動ログを追記する |
| `/logs` | 手動登録（筋トレ / スケート）+ 最近の記録 |
| `/notifications` | 通知履歴。未読カウンタはタブに出る |
| `/settings` | 通知の有効化・ログアウト |

未ログイン時は [Login.svelte](src/lib/Login.svelte) を出す。ログインは **Google OAuth のみ**
（[docs/08-open-decisions.md](../docs/08-open-decisions.md) の OD-2）。

戻り先は `Authentication > URL Configuration > Redirect URLs` で許可しておく必要がある。
開発は `http://localhost:5173/**`、本番は Cloudflare Pages の URL。

## iOS 対応で外せない箇所

[docs/03-constraints.md](../docs/03-constraints.md) の 3・4 に対応する実装。触るときは必ず読むこと。

| 箇所 | 内容 |
|---|---|
| [manifest.webmanifest](static/manifest.webmanifest) | `display` は `standalone`。`browser` だと通知不可 |
| [push.ts](src/lib/push.ts) `enablePush()` | `Notification.requestPermission()` をクリックハンドラから直接呼ぶ |
| [push.ts](src/lib/push.ts) | `userVisibleOnly: true` は必須 |
| [push.ts](src/lib/push.ts) `syncSubscription()` | 起動時に再購読する。iOS は勝手に購読を解除する |
| [sw.js](static/sw.js) | `push` で必ず `showNotification()` を呼ぶ。silent push は不可 |
| [settings/+page.svelte](src/routes/settings/+page.svelte) | ホーム画面未追加なら許可要求を出さず案内する |
| [notifications/+page.svelte](src/routes/notifications/+page.svelte) | 通知履歴。push は要約しか運ばないので必須 |

## 未実装

- **実機での Web Push 検証**（マイルストーン 5）。iOS の制約は実機でしか確認できない
- 「メニュー再生成」は `regenerate_requests` に行を入れるだけ。処理する側が未実装
  （[docs/08-open-decisions.md](../docs/08-open-decisions.md) の OD-1）
