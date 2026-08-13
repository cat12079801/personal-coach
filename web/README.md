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
| `npm run dev:design` | 開発サーバ（デザイン検証モード。下記） |
| `npm run build` | `build/` に静的出力 |
| `npm run check` | 型チェック（svelte-check） |

### デザイン検証モード

画面デザインを直すとき、Google ログインを通さずに全画面を見るためのモード。

```bash
npm run dev:design --prefix web
```

- **ログインを素通しするのではなく、DB を触らずフィクスチャを描く。**
  UI のゲートだけ外しても `anon` にはテーブルの GRANT が無く、空の画面しか見られない
- 表示するデータは [fixtures.ts](src/lib/fixtures.ts)。保存操作は DB に書かず画面上だけで完結する
- 上部に赤いバナーを常時出す。実データと見間違えないため
- 有効化の条件は `dev`（`vite build` で `false` に静的置換される）かつ `VITE_DESIGN_MODE=1` の
  両方。**本番のビルド環境変数には絶対に入れない**（理由は [design.ts](src/lib/design.ts)）

本番ビルドにバナー文字列もフィクスチャも残らないことは `grep` で確認できる。

本番: <https://personal-coach-6z2.pages.dev>

## ビルド情報の確認

実機の PWA はホーム画面から起動するとキャッシュが残り、**どのデプロイを見ているのか
判別できない**。そのためコミットハッシュとビルド時刻を画面に埋め込んでいる。

| 見る場所 | 内容 |
|---|---|
| `/settings` の「ビルド」 | コミット・ビルド時刻（JST 秒まで）・ブランチ |
| 未ログイン画面の最下部 | `<短縮ハッシュ> / <ビルド時刻>` の 1 行 |

値は [vite.config.ts](vite.config.ts) の `define` でビルド時に埋め込み、
[build-info.ts](src/lib/build-info.ts) から参照する。ハッシュは Cloudflare Pages が渡す
`CF_PAGES_COMMIT_SHA`（ローカルは `git rev-parse`）、ブランチは `CF_PAGES_BRANCH`
（ローカルは `local`）である。`npm run dev` ではビルド時刻が dev サーバの起動時刻になる。

表示が更新されないときは、ホーム画面のアイコンから起動したまま**アプリを一度終了して
再起動する**。それでも古い場合は Cloudflare のデプロイ自体が終わっていない。

## Cloudflare Pages の設定

| 項目 | 値 |
|---|---|
| Root directory | `web` |
| Build command | `npm run build` |
| Build output directory | `build` |

**依存インストールは Cloudflare 側が自動で行う**ので、ビルドコマンドに `npm ci` を含めない。
含めると `npm ci && npm run build` の `&&` が解釈されず、`npm ci` が
`&& npm run build` を引数として受け取って usage を吐いて失敗する。

`build` は Root directory からの相対。もし "output directory not found" で失敗したら
`web/build` に変えて試す。

依存が入らず `vite: not found` で落ちる場合は、`package.json` に
`"cf-build": "npm ci && npm run build"` を足してビルドコマンドを `npm run cf-build` にする。
`&&` を package.json 側に置けばシェルが解釈するので通る。

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
| `/logs` | 手動登録（筋トレのみ）+ 最近の記録 |
| `/notifications` | 通知履歴。未読カウンタはタブに出る |
| `/settings` | 通知の有効化・筋トレプログラムへの導線・ログアウト・ビルド情報 |
| `/programs` | 独自筋トレの種目と段階を管理する。**ここが空だとメニューに筋トレが出ない** |

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
