/* Service Worker。ビルド対象外の静的ファイルとして配信する。 */

self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (event) => event.waitUntil(self.clients.claim()));

/**
 * push を受けたら必ず showNotification() を呼ぶ。
 * 呼ばない push が数回続くと iOS はサブスクリプションを解除する（silent push は不可）。
 * ペイロードは要約のみ。本体は PWA 起動時に Supabase から読む。
 */
self.addEventListener('push', (event) => {
	let payload = {};
	try {
		payload = event.data ? event.data.json() : {};
	} catch {
		payload = {};
	}

	const title = payload.title || 'personal-coach';
	const options = {
		body: payload.body || '今日のメニューが更新された',
		data: { date: payload.date || null },
		tag: payload.date ? `menu-${payload.date}` : 'menu'
	};

	event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', (event) => {
	event.notification.close();
	event.waitUntil(
		self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clients) => {
			for (const client of clients) {
				if ('focus' in client) return client.focus();
			}
			return self.clients.openWindow('/');
		})
	);
});
