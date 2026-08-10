<script lang="ts">
	import { session } from '$lib/session.svelte';

	let email = $state('');
	let password = $state('');
	let error = $state('');
	let busy = $state(false);

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		error = '';
		busy = true;
		try {
			await session.signIn(email, password);
		} catch (e) {
			error = e instanceof Error ? e.message : 'ログインに失敗した';
		} finally {
			busy = false;
		}
	}
</script>

<div class="page">
	<h1>ログイン</h1>
	<form class="card" onsubmit={submit}>
		<label>
			<span>メールアドレス</span>
			<input type="email" bind:value={email} autocomplete="username" required />
		</label>
		<label>
			<span>パスワード</span>
			<input type="password" bind:value={password} autocomplete="current-password" required />
		</label>
		{#if error}<p class="error">{error}</p>{/if}
		<button class="button--primary" type="submit" disabled={busy}>
			{busy ? '…' : 'ログイン'}
		</button>
	</form>
	<p class="muted">
		サインアップは無効化してある。アカウントは Supabase ダッシュボードから作成する。
	</p>
</div>
