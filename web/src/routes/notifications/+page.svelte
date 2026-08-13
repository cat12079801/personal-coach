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
	 *
	 * なお「今日」を開いた時点で全既読になる（+layout.svelte）。ここは読み返す場所であり、
	 * 既読にするための場所ではない。
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

	$effect(() => {
		void load();
	});
</script>

<svelte:head><title>通知履歴</title></svelte:head>

<div class="page">
	<h1>通知履歴</h1>

	{#if loading}
		<p class="muted">読み込み中…</p>
	{:else if error}
		<div class="panel">
			<p class="error">{error}</p>
			<button onclick={load}>再読み込み</button>
		</div>
	{:else if rows.length === 0}
		<div class="empty">まだ通知がない。</div>
	{:else}
		{#each rows as n (n.id)}
			<section class="entry" class:entry--unread={!n.read_at}>
				<div class="entry__lab lab">
					<!-- 未読は色の点だけで示す。「新」の字は要らない -->
					{#if !n.read_at}<span class="dot" aria-label="未読"></span>{/if}
					<span class="num">{formatDateTime(n.sent_at)}</span>
				</div>
				<div class="entry__title">{n.title}</div>
				<div class="entry__sub">{n.body}</div>
				{#if n.target_date}
					<a class="entry__link" href="/">{n.target_date} のメニューを見る →</a>
				{/if}
			</section>
		{/each}
	{/if}
</div>

<style>
	.dot {
		display: inline-block;
		width: 0.5rem;
		height: 0.5rem;
		margin-right: var(--space-2xs);
		background: var(--color-accent);
		vertical-align: baseline;
	}

	.entry--unread .entry__title {
		color: var(--color-ink);
	}

	.entry__link {
		display: inline-block;
		margin-top: var(--space-xs);
		font-size: var(--text-sm);
	}
</style>
