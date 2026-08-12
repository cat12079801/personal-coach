<script lang="ts">
	import { db } from '$lib/supabase';
	import { todayJst, formatDateTime, formatDuration, formatEventTime } from '$lib/format';
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

		<h2>ラン</h2>
		{#if menu.menu.rest_day}
			<div class="card muted">休養日</div>
		{:else if menu.menu.run}
			<!-- Garmin コーチのプランは改変しない。取得したまま表示する -->
			<div class="card">
				<div class="row">
					<strong>{menu.menu.run.name ?? 'ラン'}</strong>
					<span class="muted">{formatDuration(menu.menu.run.duration_sec)}</span>
				</div>
				{#if menu.menu.run.intensity}
					<div class="muted">{menu.menu.run.intensity}</div>
				{/if}
			</div>
		{:else}
			<div class="card muted">なし</div>
		{/if}

		{#if menu.menu.garmin_strength?.length}
			<h2>補強（Garmin）</h2>
			{#each menu.menu.garmin_strength as item, i (i)}
				<div class="card">
					<div class="row">
						<strong>{item.name ?? '補強'}</strong>
						<span class="muted">{formatDuration(item.duration_sec)}</span>
					</div>
				</div>
			{/each}
		{/if}

		{#if menu.menu.own_strength?.length}
			<h2>筋トレ</h2>
			{#each menu.menu.own_strength as item (item.program_id)}
				<div class="card">
					<div class="row">
						<strong>{item.program}</strong>
						<span class="muted">段階 {item.stage}</span>
					</div>
					<div>{item.label ?? ''}{#if item.sets} ・{item.sets} セット{/if}</div>
					{#if item.note}<div class="muted">{item.note}</div>{/if}
				</div>
			{/each}
		{/if}

		<!--
			カレンダーの予定。メニュー生成のルールには使われず、表示専用。
			「今日やることを 1 画面で確認する」ためのもの。
		-->
		<h2>今日の予定</h2>
		{#if menu.menu.schedule?.length}
			{#each menu.menu.schedule as event, i (i)}
				<div class="card">
					<div class="row">
						<strong>{event.summary || '(無題)'}</strong>
						<span class="muted">{formatEventTime(event.start, event.all_day)}</span>
					</div>
				</div>
			{/each}
		{:else}
			<div class="card muted">予定なし</div>
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
