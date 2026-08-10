# ADR-0005: Garmin トークンは Supabase に永続化する

- 状態: 採用
- 日付: 2026-08-10

## 背景

Garmin のトークンは自動リフレッシュされる。GitHub Actions のランナーは実行ごとに破棄されるため、
リフレッシュ後の値を書き戻す先が必要になる。

## 決定

**Supabase に 1 行のテーブル（`garmin_tokens`）を作って読み書きする。**

初回ログインは MFA の対話が必要なのでローカルで実施し、生成されたトークンファイルの内容を
初期値として DB に投入する（`batch/scripts/bootstrap_garmin_token.py`）。

## 却下した選択肢

### GitHub Secrets を API で更新する

- `actions: write` 相当の権限をワークフローに与えることになる
- public リポジトリで書き込み権限を持つワークフローは攻撃面が増える
- Secrets は本来「人間が設定する値」であり、バッチが書き換える置き場ではない

### ランナーのキャッシュ（`actions/cache`）に置く

キャッシュは 7 日で evict される。認証情報の置き場としても不適切。

## 保存形式

トークンディレクトリ配下の**ファイル名 → 内容**の dict を丸ごと `token_json` に保存する。

```jsonc
{
  "oauth1_token.json": { /* ... */ },
  "oauth2_token.json": { /* ... */ }
}
```

個々のファイル名や構造を前提にしない。`garth` 側のトークン配置が変わっても、
ディレクトリを丸ごと往復させる方式なら実装を直す必要がない。

## 帰結

- `garmin_tokens` は **RLS ポリシーを一つも作らない**。クライアントからは一切触れない
- バッチは `service_role` キーでアクセスする
- トークンが完全に失効した場合、GitHub Actions では MFA を越えられずバッチが落ちる。
  Discord 通知を受けてローカルで `bootstrap_garmin_token.py` を再実行して復旧する。
  自動復旧は作らない
