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
	await navigator.serviceWorker.register('/sw.js', { scope: '/' });
	// register() は installing 状態の registration を返すことがある。
	// active になる前に pushManager.subscribe() を呼ぶと失敗するので、ready を待つ。
	return navigator.serviceWorker.ready;
}

async function persist(sub: PushSubscription): Promise<void> {
	const json = sub.toJSON();
	const p256dh = json.keys?.p256dh;
	const auth = json.keys?.auth;
	if (!p256dh || !auth) {
		throw new Error('購読キーを取り出せなかった（p256dh / auth が空）');
	}
	const { error } = await db()
		.from('push_subscriptions')
		.upsert({ endpoint: sub.endpoint, p256dh, auth }, { onConflict: 'endpoint' });
	// 保存できていなければ通知は届かない。黙って握りつぶさない
	if (error) throw new Error(`購読の保存に失敗した: ${error.message}`);
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

/** 設定画面に出す診断情報。実機で詰まったときの切り分け用。 */
export async function diagnose(): Promise<Record<string, string>> {
	const out: Record<string, string> = {
		standalone: String(isStandalone()),
		permission: typeof Notification === 'undefined' ? 'なし' : Notification.permission,
		vapid: vapidPublicKey ? `設定済み(${vapidPublicKey.length}文字)` : '未設定'
	};
	if (!pushSupported) {
		out.serviceWorker = '非対応';
		return out;
	}
	try {
		const reg = await registration();
		out.serviceWorker = reg.active ? 'active' : '未 active';
		const sub = await reg.pushManager.getSubscription();
		out.subscription = sub ? new URL(sub.endpoint).host : 'なし';
		if (sub) {
			const json = sub.toJSON();
			out.keys = json.keys?.p256dh && json.keys?.auth ? 'あり' : '欠落';
		}
	} catch (e) {
		out.serviceWorker = `エラー: ${e instanceof Error ? e.message : String(e)}`;
	}
	try {
		const { count, error } = await db()
			.from('push_subscriptions')
			.select('id', { count: 'exact', head: true });
		out.dbRows = error ? `エラー: ${error.message}` : `${count} 件`;
	} catch (e) {
		out.dbRows = `エラー: ${e instanceof Error ? e.message : String(e)}`;
	}
	return out;
}

export function vapidConfigured(): boolean {
	return Boolean(vapidPublicKey);
}
