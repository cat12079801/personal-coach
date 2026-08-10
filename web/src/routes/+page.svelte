<script lang="ts">
	import { db } from '$lib/supabase';
	import { todayJst, formatDateTime } from '$lib/format';
	import type { DailyMenu } from '$lib/types';

	const today = todayJst();

	let menu = $state<DailyMenu | null>(null);
	let loading = $state(true);
	let requesting = $state(false);
	let requested = $state(false);
	let loadError = $state('');
	let error = $state('');

	async function load() {
		loading = true;
		loadError = '';
		try {
			const { data, error: e } = await db()
				.from('daily_menus')
				.select('*')
				.eq('date', today)
				.maybeSingle();
			if (e) throw new Error(e.message);
			menu = data as DailyMenu | null;
		} catch (e) {
			loadError = e instanceof Error ? e.message : String(e);
		} finally {
			loading = false;
		}
	}

	/**
	 * .ics は Google 側でキャッシュされ反映が数時間遅れることがある。
	 * 前夜遅くに入れた予定を 03:00 のバッチが拾えないため、手動リカバリの導線を必ず置く。
	 * 詳細は docs/adr/0003-ical-instead-of-oauth.md。
	 */
	async function requestRegenerate() {
		requesting = true;
		error = '';
		const { error: e } = await db().from('regenerate_requests').insert({ target_date: today });
		if (e) error = e.message;
		else requested = true;
		requesting = false;
	}

	$effect(() => {
		void load();
	});
</script>

<svelte:head><title>今日のトレーニング</title></svelte:head>

<div class="page">
	<h1>今日のトレーニング</h1>

	{#if loading}
		<p class="muted">読み込み中…</p>
	{:else if loadError}
		<div class="card">
			<p class="error">{loadError}</p>
			<button onclick={load}>再読み込み</button>
		</div>
	{:else if !menu}
		<div class="empty">
			<p>{today} のメニューはまだ生成されていない。</p>
			<p class="muted">03:00 JST のバッチで生成される。</p>
		</div>
	{:else}
		<div class="card">
			<p style="margin-top: 0; font-size: 1.05rem;">{menu.menu.summary ?? '（要約なし）'}</p>
			<p class="muted">生成 {formatDateTime(menu.generated_at)}</p>
		</div>

		{#if menu.menu.run}
			<h2>ラン</h2>
			<div class="card">
				<!-- Garmin コーチのプランは改変しない。そのまま表示する -->
				<pre style="margin: 0; white-space: pre-wrap; font-size: 0.85rem;">{JSON.stringify(
						menu.menu.run,
						null,
						2
					)}</pre>
			</div>
		{/if}

		{#if menu.menu.strength?.length}
			<h2>筋トレ</h2>
			{#each menu.menu.strength as item, i (i)}
				<div class="card">
					<pre style="margin: 0; white-space: pre-wrap; font-size: 0.85rem;">{JSON.stringify(
							item,
							null,
							2
						)}</pre>
				</div>
			{/each}
		{/if}

		<h2>生成根拠</h2>
		<details class="card">
			<summary class="muted">source を表示</summary>
			<pre style="white-space: pre-wrap; font-size: 0.75rem;">{JSON.stringify(
					menu.source,
					null,
					2
				)}</pre>
		</details>
	{/if}

	<h2>手動リカバリ</h2>
	<div class="card">
		<p class="muted" style="margin-top: 0;">
			カレンダーの反映が遅れて予定を拾えていない場合に再生成する。
		</p>
		<button onclick={requestRegenerate} disabled={requesting || requested}>
			{requested ? '再生成をリクエスト済み' : 'メニューを再生成'}
		</button>
	</div>

	{#if error}<p class="error">{error}</p>{/if}
</div>
