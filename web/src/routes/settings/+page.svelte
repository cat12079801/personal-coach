<script lang="ts">
	import { session } from '$lib/session.svelte';
	import { diagnose, enablePush, isStandalone, pushSupported, vapidConfigured } from '$lib/push';

	let permission = $state(
		typeof Notification !== 'undefined' ? Notification.permission : 'default'
	);
	let error = $state('');
	let busy = $state(false);

	const standalone = isStandalone();

	let saved = $state(false);
	let info = $state<Record<string, string> | null>(null);

	// クリックハンドラから直接 enablePush() を呼ぶ。手前に await を挟まないこと
	async function onEnableClick() {
		busy = true;
		error = '';
		saved = false;
		try {
			permission = await enablePush();
			if (permission === 'denied') {
				error = '通知が拒否された。iOS の設定アプリから許可し直す必要がある。';
			} else if (permission === 'granted') {
				// ここまで来ていれば DB への保存も成功している（失敗時は例外になる）
				saved = true;
			}
		} catch (e) {
			error = e instanceof Error ? e.message : '購読に失敗した';
		} finally {
			busy = false;
		}
	}

	async function onDiagnoseClick() {
		info = null;
		info = await diagnose();
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
			{#if saved}<p class="muted">購読を保存した。</p>{/if}
		{:else}
			<button class="button--primary" onclick={onEnableClick} disabled={busy}>
				{busy ? '…' : '通知を有効にする'}
			</button>
		{/if}
		{#if error}<p class="error">{error}</p>{/if}

		<button onclick={onDiagnoseClick} style="margin-top: 0.5rem;">診断</button>
		{#if info}
			<!-- 実機で詰まったときの切り分け用。購読が DB に入らない事象があった -->
			<pre style="white-space: pre-wrap; font-size: 0.75rem; margin-bottom: 0;">{Object.entries(
					info
				)
					.map(([k, v]) => `${k}: ${v}`)
					.join('\n')}</pre>
		{/if}
	</div>

	<h2>筋トレプログラム</h2>
	<div class="card">
		<p class="muted" style="margin-top: 0;">
			上半身・スキル系の種目と段階を管理する。ここが空だとメニューに筋トレが出ない。
		</p>
		<a class="button" href="/programs" style="display: inline-block;">プログラムを編集</a>
	</div>

	<h2>アカウント</h2>
	<div class="card">
		<p class="muted">{session.session?.user.email}</p>
		<button onclick={() => session.signOut()}>ログアウト</button>
	</div>
</div>
