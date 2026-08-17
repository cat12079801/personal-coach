# 開発時の姿勢

このリポジトリで作業する前に必ず [docs/03-constraints.md](docs/03-constraints.md) を読むこと。

## 守ること

- **推測で実装しない。** API のレスポンス形状は必ず実データをダンプして確認してから正規化を書く。
  確認結果は [docs/06-poc-notes.md](docs/06-poc-notes.md) に記録する
- **制約リストに反する提案は採用しない。** 以下はすべて検討済みで却下されている
  - Cloudflare Workers / Supabase Edge Functions で Garmin を叩く
  - 素の fetch で Garmin API を叩き直す
  - silent push（`showNotification()` を呼ばない push）
  - OAuth / サービスアカウントで Google カレンダーを読む
  - GitHub Secrets を API で更新してトークンを永続化する
  - `actions: write` で 60 日タイマーをリセットする
  - メニュー生成に LLM を使う
  - 独自筋トレを Garmin のワークアウトとして登録する／実績を Garmin に書き戻す
  - マイグレーションを CI から自動適用する（手で流す。docs/09-setup-supabase.md）
  - display 書体を自前配信する／Service Worker でアプリシェルをキャッシュする
    （docs/11-design-audit.md）
- **ライブラリのバージョンやメソッド名は 2026-08-10 時点の確認結果。**
  着手時に `demo.py` および README で最新を確認する

## public リポジトリであることの制約

- `pull_request_target` を使わない
- ログにトークン、Supabase の service_role key、カレンダーの非公開 URL を出力しない
- `workflow_dispatch` の入力を無検証でシェルに渡さない
- PoC の出力（`batch/.poc-out/`）は個人データなのでコミットしない
- `VITE_DESIGN_MODE` を本番（Cloudflare Pages）のビルド環境変数に入れない。
  ローカルのデザイン検証専用である（`web/src/lib/design.ts`）

## 現在地（2026-08-12）

**全マイルストーン完了。** 毎日 03:00 JST に取り込みとメニュー生成、08:00 JST に通知が
GitHub Actions で自動実行される。加えて 15 分おきに再生成リクエストを拾い、
Garmin を引き直してメニューを作り直す。残作業と運用状態は
[docs/05-roadmap.md](docs/05-roadmap.md)。

| | |
|---|---|
| 本番 PWA | https://personal-coach-6z2.pages.dev |
| DB | 既存 Supabase プロジェクトの `coach` スキーマに相乗り |
| ローカル実行 | `cd batch && uv run pc-ingest` / `uv run pc-notify` / `uv run pc-regenerate` |
| 設定 | リポジトリ直下の `.env`（`config.py` が読む。gitignore 済み） |

## 一度踏んだ罠

同じところを二度踏まないための一覧。詳細は各ドキュメントにある。

- **`garminconnect` のトークン書き出しは `Client.dump()`。** `garth.dump()` ではない。
  書き戻せないとトークンが失効し、再取得には MFA 対話と IP レート制限との戦いが要る
- **supabase-js は例外を投げず `{ error }` を返す。** 握りつぶすと「UI は成功、DB は空」になる。
  Web Push の購読でこれを踏んだ
- **Service Worker は `navigator.serviceWorker.ready` を待つ。**
  `register()` は installing 状態の registration を返すことがあり、購読が失敗する
- **差分同期は過去に遡れない。** 既知 ID で打ち切るため。バックフィルは `BACKFILL_PAGES` を使う
- **RPE は `get_activities()` に入らない。** `get_activity()` の
  `summaryDTO.directWorkoutRpe`（0-100 スケール）にある
- **Supabase は RLS だけでは足りない。** 明示的な GRANT が無いと PostgREST が
  permission denied を返す
- **Cloudflare Pages のビルドコマンドに `&&` を書かない。** 解釈されず引数として渡る。
  依存インストールは Cloudflare 側が自動で行うので `npm run build` だけでよい。
  Root directory（`web`）の指定と `static/_redirects` も必須
- **`astral-sh/setup-uv` に浮動 major タグは無い。** `@v9.0.0` のようにフル固定する
- **SVG のプレゼンテーション属性で `var()` は解決されない。** 色は CSS 側で指定する
- **Svelte 5 で `{#each}` のアイテムに `bind:value` しても書き戻らないことがある。**
  完了記録のセット入力で踏んだ。入力しても state が変わらず、保存すると空のまま入る。
  状態を作り直して代入する（`done = { ...done, [id]: ... }`）形に直すこと

## 実装順序

[docs/05-roadmap.md](docs/05-roadmap.md) の順で進める。順序には理由がある。
特に「PoC-1（Garmin コーチのプラン取得）を取り込みバッチより先にやる」を崩さないこと。

## 文体

- ドキュメント・commit message・PR description は**である調**で端的に書く
- 提示するシェルコマンドは fish で動く形式にする（CI 内のスクリプトは bash でよい）

### Markdown の強調記法

**閉じの `**` の直前に句読点を置かない。** GitHub（CommonMark）は
「閉じ `**` の直前が約物、かつ直後が空白でも約物でもない」場合に強調を閉じないため、
`**である。**次に` は崩れる。`**である**。次に` と書く。

確認方法:

```bash
jq -n --rawfile t README.md '{text:$t, mode:"gfm"}' | gh api -X POST /markdown --input - | grep '\*\*'
```

出力に `**` が残っていたら崩れている。
