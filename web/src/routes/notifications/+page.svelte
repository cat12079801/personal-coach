<script lang="ts">
	import { db } from '$lib/supabase';
	import { designMode } from '$lib/design';
	import { designNotifications } from '$lib/fixtures';
	import { formatDateTime } from '$lib/format';
	import type { NotificationRow } from '$lib/types';

	/**
	 * iOS では通知が届かない・消えることがあり、push は要約しか運ばない。
	 * この履歴一覧と未読カウンタは推奨ではなく必須の作りである。
	 * docs/adr/0004-push-payload-minimal.md
	 */
	let rows = $state<NotificationRow[]>([]);
	let loading = $state(true);
	let error = $state('');

	async function load() {
		loading = true;
		error = '';
		if (designMode) {
			// フィクスチャは共有の配列なので、書き換えないようコピーを持つ
			rows = designNotifications.map((row) => ({ ...row }));
			loading = false;
			return;
		}
		try {
			const { data, error: e } = await db()
				.from('notifications')
				.select('*')
				.order('sent_at', { ascending: false })
				.limit(50);
			if (e) throw new Error(e.message);
			rows = (data ?? []) as NotificationRow[];
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		} finally {
			loading = false;
		}
	}

	async function markAllRead() {
		const now = new Date().toISOString();
		if (designMode) {
			rows = rows.map((row) => ({ ...row, read_at: row.read_at ?? now }));
			return;
		}
		const { error: e } = await db().from('notifications').update({ read_at: now }).is('read_at', null);
		if (e) error = e.message;
		else await load();
	}

	$effect(() => {
		void load();
	});
</script>

<svelte:head><title>通知履歴</title></svelte:head>

<div class="page">
	<div class="row">
		<h1>通知履歴</h1>
		{#if rows.some((r) => !r.read_at)}
			<button onclick={markAllRead}>すべて既読</button>
		{/if}
	</div>

	{#if loading}
		<p class="muted">読み込み中…</p>
	{:else if error}
		<p class="error">{error}</p>
	{:else if rows.length === 0}
		<div class="empty">まだ通知がない。</div>
	{:else}
		{#each rows as n (n.id)}
			<div class="card">
				<div class="row">
					<strong>{n.title}{#if !n.read_at}<span class="badge">新</span>{/if}</strong>
					<span class="muted">{formatDateTime(n.sent_at)}</span>
				</div>
				<div>{n.body}</div>
				{#if n.target_date}
					<a href="/">{n.target_date} のメニューを見る →</a>
				{/if}
			</div>
		{/each}
	{/if}
</div>
