<script lang="ts">
	import { session } from '$lib/session.svelte';
	import { designMode } from '$lib/design';
	import { diagnose, enablePush, isStandalone, pushSupported, vapidConfigured } from '$lib/push';
	import { buildInfo, formatBuiltAt } from '$lib/build-info';

	let permission = $state(
		typeof Notification !== 'undefined' ? Notification.permission : 'default'
	);
	let error = $state('');
	let busy = $state(false);

	/**
	 * デザイン検証モードではホーム画面 PWA でも VAPID の設定でもないので、
	 * そのままだと「ホーム画面に追加してから開くこと」しか見えない。
	 * 通知セクションの本体を見るために両方を満たしているものとして扱う。
	 */
	const standalone = designMode || isStandalone();
	const configured = designMode || vapidConfigured();

	let saved = $state(false);
	let info = $state<Record<string, string> | null>(null);

	// クリックハンドラから直接 enablePush() を呼ぶ。手前に await を挟まないこと
	async function onEnableClick() {
		busy = true;
		error = '';
		saved = false;
		if (designMode) {
			permission = 'granted';
			saved = true;
			busy = false;
			return;
		}
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
		if (designMode) {
			info = {
				standalone: 'true',
				permission,
				serviceWorker: 'activated',
				subscription: 'design-mode（DB には保存しない）'
			};
			return;
		}
		info = await diagnose();
	}
</script>

<svelte:head><title>設定</title></svelte:head>

<div class="page">
	<h1>設定</h1>

	<h2>通知</h2>
	<div class="panel">
		{#if !pushSupported && !designMode}
			<p>この環境では Web Push を扱えない。</p>
		{:else if !configured}
			<p><code>VITE_VAPID_PUBLIC_KEY</code> が未設定である。</p>
		{:else if !standalone}
			<p>ホーム画面に追加してから開くこと。</p>
			<p class="muted">
				iOS では Safari のタブから通知の許可を求めることができない。共有メニューの
				「ホーム画面に追加」から追加し、追加されたアイコンから起動する。
			</p>
		{:else if permission === 'granted'}
			<p class="ok">通知は有効である。</p>
			<p class="muted">08:00 JST に当日のメニューが届く。</p>
			{#if saved}<p class="muted">購読を保存した。</p>{/if}
		{:else}
			<button class="button--ink" onclick={onEnableClick} data-state={busy ? 'loading' : undefined} disabled={busy}>
				{busy ? '…' : '通知を有効にする'}
			</button>
		{/if}
		{#if error}<p class="error">{error}</p>{/if}

		<details class="diag">
			<summary class="muted">診断</summary>
			<!-- 実機で詰まったときの切り分け用。購読が DB に入らない事象があった -->
			<button class="button--quiet" onclick={onDiagnoseClick}>いま調べる</button>
			{#if info}
				<dl class="kv">
					{#each Object.entries(info) as [k, v] (k)}
						<dt class="lab">{k}</dt>
						<dd class="num">{v}</dd>
					{/each}
				</dl>
			{/if}
		</details>
	</div>

	<h2>筋トレプログラム</h2>
	<div class="panel">
		<p class="muted" style:margin-top="0">
			上半身・スキル系の種目と段階を管理する。ここが空だとメニューに筋トレが出ない。
		</p>
		<a class="button" href="/programs">プログラムを編集</a>
	</div>

	<h2>アカウント</h2>
	<div class="panel">
		<p class="muted">{session.session?.user.email}</p>
		<button onclick={() => session.signOut()}>ログアウト</button>
	</div>

	<h2>ビルド</h2>
	<div class="panel">
		<!-- 実機の PWA はキャッシュが残る。表示が古いときここで見ているデプロイを確かめる -->
		<dl class="kv">
			<dt class="lab">Commit</dt>
			<dd class="num">{buildInfo.commit}</dd>
			<dt class="lab">Built</dt>
			<dd class="num">{formatBuiltAt()}</dd>
			<dt class="lab">Branch</dt>
			<dd class="num">{buildInfo.branch}</dd>
		</dl>
	</div>
</div>

<style>
	.ok {
		color: var(--color-good);
	}

	/* 名前と値の対。値は等幅数字で右に落とす */
	.kv {
		display: grid;
		grid-template-columns: auto 1fr;
		gap: var(--space-2xs) var(--space-sm);
		margin: var(--space-xs) 0 0;
	}

	.kv dt {
		align-self: baseline;
	}

	.kv dd {
		margin: 0;
		text-align: right;
		font-size: var(--text-sm);
		overflow-wrap: anywhere;
	}

	.diag {
		margin-top: var(--space-xs);
	}

	.button {
		display: inline-block;
	}
</style>
