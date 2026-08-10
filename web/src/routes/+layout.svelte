<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { isConfigured, db } from '$lib/supabase';
	import { session } from '$lib/session.svelte';
	import { syncSubscription } from '$lib/push';
	import Login from '$lib/Login.svelte';

	let { children } = $props();

	let unread = $state(0);

	onMount(async () => {
		await session.init();
		if (session.session) {
			// iOS は端末再起動などで購読を勝手に解除する。起動のたびに入れ直す
			await syncSubscription().catch(() => {});
		}
	});

	// ログイン後・画面遷移ごとに未読数を取り直す
	$effect(() => {
		void page.url.pathname;
		if (!session.session) {
			unread = 0;
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
		{ href: '/', label: '今日' },
		{ href: '/activities', label: '記録' },
		{ href: '/logs', label: '手動登録' },
		{ href: '/notifications', label: '通知' },
		{ href: '/settings', label: '設定' }
	];
</script>

{#if !isConfigured}
	<div class="page">
		<h1>設定が足りない</h1>
		<div class="card">
			<p>
				<code>VITE_SUPABASE_URL</code> と <code>VITE_SUPABASE_ANON_KEY</code> が設定されていない。
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
	{@render children()}

	<nav class="nav">
		{#each tabs as tab (tab.href)}
			<a
				href={tab.href}
				aria-current={page.url.pathname === tab.href ? 'page' : undefined}
			>
				{tab.label}{#if tab.href === '/notifications' && unread > 0}
					<span class="badge">{unread}</span>
				{/if}
			</a>
		{/each}
	</nav>
{/if}
