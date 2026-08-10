/**
 * Web Push の購読まわり。iOS の制約は docs/03-constraints.md の 3 を参照。
 *
 *  - ホーム画面追加が必須。Safari のタブでは許可要求すらできない
 *  - Notification.requestPermission() はクリックハンドラから直接呼ぶ
 *  - userVisibleOnly: true は必須
 *  - 予期しない購読解除が起こるので、起動時に必ず再購読する
 */
import { db } from './supabase';

const vapidPublicKey = import.meta.env.VITE_VAPID_PUBLIC_KEY as string | undefined;

export const pushSupported =
	typeof window !== 'undefined' && 'serviceWorker' in navigator && 'PushManager' in window;

/** iOS はホーム画面に追加されていないと通知を扱えない。 */
export function isStandalone(): boolean {
	if (typeof window === 'undefined') return false;
	return (
		window.matchMedia('(display-mode: standalone)').matches ||
		// iOS Safari 独自
		(window.navigator as unknown as { standalone?: boolean }).standalone === true
	);
}

/** VAPID 公開鍵は base64url。applicationServerKey は BufferSource で渡す。 */
function urlBase64ToArrayBuffer(base64: string): ArrayBuffer {
	const padded = (base64 + '='.repeat((4 - (base64.length % 4)) % 4))
		.replace(/-/g, '+')
		.replace(/_/g, '/');
	const raw = atob(padded);
	const buffer = new ArrayBuffer(raw.length);
	const view = new Uint8Array(buffer);
	for (let i = 0; i < raw.length; i++) view[i] = raw.charCodeAt(i);
	return buffer;
}

async function registration(): Promise<ServiceWorkerRegistration> {
	return navigator.serviceWorker.register('/sw.js', { scope: '/' });
}

async function persist(sub: PushSubscription): Promise<void> {
	const json = sub.toJSON();
	await db()
		.from('push_subscriptions')
		.upsert(
			{ endpoint: sub.endpoint, p256dh: json.keys?.p256dh, auth: json.keys?.auth },
			{ onConflict: 'endpoint' }
		);
}

/**
 * 通知を有効化する。**クリックハンドラから直接呼ぶこと。**
 * setTimeout や別の await を挟んだ後に呼ぶと iOS は許可要求を無視する。
 */
export async function enablePush(): Promise<'granted' | 'denied' | 'default'> {
	const permission = await Notification.requestPermission();
	if (permission !== 'granted') return permission;

	const reg = await registration();
	const sub = await reg.pushManager.subscribe({
		userVisibleOnly: true, // iOS では必須。silent push は不可
		applicationServerKey: urlBase64ToArrayBuffer(vapidPublicKey ?? '')
	});
	await persist(sub);
	return 'granted';
}

/**
 * 起動時に呼ぶ。iOS は端末再起動などで購読を勝手に解除するため、
 * 既存の購読があれば DB に入れ直し、無ければ黙って作り直す。
 */
export async function syncSubscription(): Promise<void> {
	if (!pushSupported || !vapidPublicKey) return;
	if (Notification.permission !== 'granted') return;

	const reg = await registration();
	let sub = await reg.pushManager.getSubscription();
	if (!sub) {
		sub = await reg.pushManager.subscribe({
			userVisibleOnly: true,
			applicationServerKey: urlBase64ToArrayBuffer(vapidPublicKey)
		});
	}
	await persist(sub);
}

export function vapidConfigured(): boolean {
	return Boolean(vapidPublicKey);
}
