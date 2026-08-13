<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { isConfigured, db } from '$lib/supabase';
	import { session } from '$lib/session.svelte';
	import { syncSubscription } from '$lib/push';
	import { designMode } from '$lib/design';
	import { designNotifications } from '$lib/fixtures';
	import Login from '$lib/Login.svelte';
	import NavIcon from '$lib/NavIcon.svelte';

	let { children } = $props();

	let unread = $state(0);

	onMount(async () => {
		await session.init();
		// デザイン検証モードでは購読も通知も DB を触らない（design.ts）
		if (session.session && !designMode) {
			// iOS は端末再起動などで購読を勝手に解除する。起動のたびに入れ直す
			await syncSubscription().catch(() => {});
		}
	});

	/**
	 * 「今日」を開いたら通知は用済みとみなして既読にする。
	 *
	 * push は要約しか運ばず、本体はこの画面にある（ADR-0004）。つまり当日のメニューを
	 * 開いた時点で通知の役目は終わっている。履歴は残るので消えるわけではない。
	 */
	// デザイン検証モードでも既読の見え方を再現する（DB は触らない）
	let designRead = $state(false);

	async function markAllRead() {
		if (designMode) {
			designRead = true;
			unread = 0;
			return;
		}
		const { error } = await db()
			.from('notifications')
			.update({ read_at: new Date().toISOString() })
			.is('read_at', null);
		if (!error) unread = 0;
	}

	// ログイン後・画面遷移ごとに未読数を取り直す
	$effect(() => {
		const path = page.url.pathname;
		if (!session.session) {
			unread = 0;
			return;
		}
		if (path === '/') {
			void markAllRead();
			return;
		}
		if (designMode) {
			unread = designRead ? 0 : designNotifications.filter((n) => !n.read_at).length;
			return;
		}
		db()
			.from('notifications')
			.select('id', { count: 'exact', head: true })
			.is('read_at', null)
			.then(({ count }) => {
				unread = count ?? 0;
			});
	});

	const tabs = [
		{ href: '/', label: '今日', icon: 'today' },
		{ href: '/activities', label: '記録', icon: 'activities' },
		{ href: '/logs', label: '手動登録', icon: 'logs' },
		{ href: '/notifications', label: '通知', icon: 'notifications' },
		{ href: '/settings', label: '設定', icon: 'settings' }
	] as const;
</script>

<!-- デザイン検証モードは Supabase の設定が無くても動く（フィクスチャしか読まないため） -->
{#if !isConfigured && !designMode}
	<div class="page">
		<h1>設定が足りない</h1>
		<div class="card">
			<p>
				<code>VITE_SUPABASE_URL</code> と <code>VITE_SUPABASE_PUBLISHABLE_KEY</code> が設定されていない。
			</p>
			<p class="muted">
				ローカルでは <code>web/.env.local</code> に、Cloudflare Pages ではビルド環境変数に設定する。
			</p>
		</div>
	</div>
{:else if session.loading}
	<div class="page"><p class="muted">読み込み中…</p></div>
{:else if !session.session}
	<Login />
{:else}
	{#if designMode}
		<!-- 実データと見間違えないよう常に出す。本番ビルドではこの分岐ごと消える -->
		<div class="design-banner">デザイン検証モード（ダミーデータ・保存しない）</div>
	{/if}

	{@render children()}

	<nav class="nav">
		{#each tabs as tab (tab.href)}
			<a href={tab.href} aria-current={page.url.pathname === tab.href ? 'page' : undefined}>
				<NavIcon name={tab.icon} />
				{tab.label}
				{#if tab.href === '/notifications' && unread > 0}
					<span class="badge">{unread}</span>
				{/if}
			</a>
		{/each}
	</nav>
{/if}
