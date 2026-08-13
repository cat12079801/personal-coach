<script lang="ts">
	import { db } from '$lib/supabase';
	import { designMode } from '$lib/design';
	import { designActivities } from '$lib/fixtures';
	import { formatDateTime, formatDuration, formatDistance, formatPace } from '$lib/format';
	import type { Activity, RunningDetail } from '$lib/types';

	type Row = Activity & { running_details: RunningDetail | null };

	let rows = $state<Row[]>([]);
	let loading = $state(true);
	let error = $state('');

	async function load() {
		loading = true;
		error = '';
		if (designMode) {
			rows = designActivities;
			loading = false;
			return;
		}
		try {
			const { data, error: e } = await db()
				.from('activities')
				.select('*, running_details(*)')
				.order('started_at', { ascending: false })
				.limit(50);
			if (e) throw new Error(e.message);
			rows = (data ?? []) as Row[];
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		void load();
	});
</script>

<svelte:head><title>アクティビティ</title></svelte:head>

<div class="page">
	<h1>アクティビティ</h1>

	{#if loading}
		<p class="muted">読み込み中…</p>
	{:else if error}
		<div class="card">
			<p class="error">{error}</p>
			<button onclick={load}>再読み込み</button>
		</div>
	{:else if rows.length === 0}
		<div class="empty">
			<p>まだ取り込まれていない。</p>
			<p class="muted">03:00 JST のバッチが Garmin から取り込む。</p>
		</div>
	{:else}
		{#each rows as a (a.id)}
			<div class="card">
				<div class="row">
					<strong>{a.sport}</strong>
					<span class="muted">{formatDateTime(a.started_at)}</span>
				</div>
				<div class="muted">
					{formatDuration(a.duration_sec)}
					{#if a.running_details}
						・{formatDistance(a.running_details.distance_m)}
						・{formatPace(a.running_details.avg_pace)}
					{/if}
					{#if a.avg_hr}・平均 {a.avg_hr} bpm{/if}
				</div>
				{#if a.running_details && !a.running_details.splits}
					<div class="muted">スプリット未取得</div>
				{/if}
			</div>
		{/each}
	{/if}
</div>
