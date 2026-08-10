# web

PWA。Cloudflare Pages に静的配信する。**マイルストーン 4・未着手。**

フレームワークは任意（SvelteKit / React + Vite 等）。着手時に決める。

## 方針

- `supabase-js` で Supabase を直接読む。**独自バックエンドは作らない**
- 認証は Supabase Auth。利用者は 1 人
- 書き込みは手動ログ（ボルダリング / 筋トレ / スケート）と `push_subscriptions` のみ

## 実装必須の要件

[docs/03-constraints.md](../docs/03-constraints.md) の 3・4 に対応するもの。省略できない。

### manifest.json

```jsonc
{
  "display": "standalone"   // "browser" だと iOS で通知不可
}
```

### 通知の許可要求

```js
// クリックハンドラから直接呼ぶ。setTimeout 経由は iOS に無視される
button.addEventListener('click', async () => {
  const permission = await Notification.requestPermission()
  if (permission !== 'granted') return
  const sub = await registration.pushManager.subscribe({
    userVisibleOnly: true,          // iOS では必須
    applicationServerKey: VAPID_PUBLIC_KEY,
  })
  await supabase.from('push_subscriptions').upsert(toRow(sub))
})
```

**ホーム画面追加が必須。** Safari のタブでは許可要求すらできない。
その旨を案内する UI を用意する。

### Service Worker

```js
self.addEventListener('push', (event) => {
  const data = event.data.json()
  // showNotification を呼ばない push が数回続くと iOS は購読を解除する。
  // silent push は不可
  event.waitUntil(self.registration.showNotification(data.title, { body: data.body }))
})
```

### 起動時の再購読

iOS は端末再起動後などに予期せず購読を解除する。**PWA 起動時に必ず再購読する。**

### 画面

| 画面 | 内容 |
|---|---|
| 当日メニュー | `daily_menus` から読む。push は本体を運ばないのでここが正 |
| 「メニュー再生成」ボタン | .ics のキャッシュ遅延に対する手動リカバリ。省略不可 |
| アクティビティ一覧 | `activities` + `running_details` |
| 未紐付けアクティビティ | `unlinked_activities` ビュー。ここから手動ログを追記する |
| 手動ログ登録 | ボルダリング / 筋トレ / スケート。RPE も入力する |
| 通知履歴 + 未読カウンタ | `notifications`。iOS では推奨ではなく必須 |
