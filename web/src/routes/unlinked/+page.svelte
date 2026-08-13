<script lang="ts">
	import { db } from '$lib/supabase';
	import { designMode } from '$lib/design';
	import { designUnlinked } from '$lib/fixtures';
	import { formatDateTime, formatDuration } from '$lib/format';
	import type { Activity } from '$lib/types';

	let rows = $state<Activity[]>([]);
	let loading = $state(true);
	let error = $state('');

	async function load() {
		loading = true;
		error = '';
		if (designMode) {
			rows = designUnlinked;
			loading = false;
			return;
		}
		try {
			// unlinked_activities は security_invoker のビュー（supabase/migrations/0001_init.sql）
			const { data, error: e } = await db()
				.from('unlinked_activities')
				.select('*')
				.order('started_at', { ascending: false })
				.limit(50);
			if (e) throw new Error(e.message);
			rows = (data ?? []) as Activity[];
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

<svelte:head><title>未紐付けアクティビティ</title></svelte:head>

<div class="page">
	<a class="back" href="/activities">← 記録</a>
	<h1>未紐付けアクティビティ</h1>
	<p class="muted">
		Garmin で計測したが手動ログを書いていないもの。ここから詳細を追記する。
	</p>

	{#if loading}
		<p class="muted">読み込み中…</p>
	{:else if error}
		<div class="card">
			<p class="error">{error}</p>
			<button onclick={load}>再読み込み</button>
		</div>
	{:else if rows.length === 0}
		<div class="empty">すべて紐付け済み。</div>
	{:else}
		{#each rows as a (a.id)}
			<a class="card card--tappable" style="display: block;" href="/logs?activity={a.id}">
				<div class="row">
					<strong>{a.sport}</strong>
					<span class="muted">{formatDateTime(a.started_at)}</span>
				</div>
				<div class="muted">{formatDuration(a.duration_sec)} ・ 詳細を追記する →</div>
			</a>
		{/each}
	{/if}
</div>
