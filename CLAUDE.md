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
- **ライブラリのバージョンやメソッド名は 2026-08-10 時点の確認結果。**
  着手時に `demo.py` および README で最新を確認する

## public リポジトリであることの制約

- `pull_request_target` を使わない
- ログにトークン、Supabase の service_role key、カレンダーの非公開 URL を出力しない
- `workflow_dispatch` の入力を無検証でシェルに渡さない
- PoC の出力（`batch/.poc-out/`）は個人データなのでコミットしない

## 実装順序

[docs/05-roadmap.md](docs/05-roadmap.md) の順で進める。順序には理由がある。
特に「PoC-1（Garmin コーチのプラン取得）を取り込みバッチより先にやる」を崩さないこと。

## 文体

- ドキュメント・commit message・PR description は**である調**で端的に書く
- 提示するシェルコマンドは fish で動く形式にする（CI 内のスクリプトは bash でよい）
