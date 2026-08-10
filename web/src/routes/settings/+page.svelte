<script lang="ts">
	import { session } from '$lib/session.svelte';
	import { enablePush, isStandalone, pushSupported, vapidConfigured } from '$lib/push';

	let permission = $state(
		typeof Notification !== 'undefined' ? Notification.permission : 'default'
	);
	let error = $state('');
	let busy = $state(false);

	const standalone = isStandalone();

	// クリックハンドラから直接 enablePush() を呼ぶ。手前に await を挟まないこと
	async function onEnableClick() {
		busy = true;
		error = '';
		try {
			permission = await enablePush();
			if (permission === 'denied') {
				error = '通知が拒否された。iOS の設定アプリから許可し直す必要がある。';
			}
		} catch (e) {
			error = e instanceof Error ? e.message : '購読に失敗した';
		} finally {
			busy = false;
		}
	}
</script>

<svelte:head><title>設定</title></svelte:head>

<div class="page">
	<h1>設定</h1>

	<h2>通知</h2>
	<div class="card">
		{#if !pushSupported}
			<p>この環境では Web Push を扱えない。</p>
		{:else if !vapidConfigured()}
			<p><code>VITE_VAPID_PUBLIC_KEY</code> が未設定である。</p>
		{:else if !standalone}
			<p>ホーム画面に追加してから開くこと。</p>
			<p class="muted">
				iOS では Safari のタブから通知の許可を求めることができない。共有メニューの
				「ホーム画面に追加」から追加し、追加されたアイコンから起動する。
			</p>
		{:else if permission === 'granted'}
			<p>通知は有効である。</p>
			<p class="muted">08:00 JST に当日のメニューが届く。</p>
		{:else}
			<button class="button--primary" onclick={onEnableClick} disabled={busy}>
				{busy ? '…' : '通知を有効にする'}
			</button>
		{/if}
		{#if error}<p class="error">{error}</p>{/if}
	</div>

	<h2>アカウント</h2>
	<div class="card">
		<p class="muted">{session.session?.user.email}</p>
		<button onclick={() => session.signOut()}>ログアウト</button>
	</div>
</div>
