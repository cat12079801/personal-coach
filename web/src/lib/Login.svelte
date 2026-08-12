<script lang="ts">
	import { session } from '$lib/session.svelte';
	import { buildInfoLine } from '$lib/build-info';

	let error = $state('');
	let busy = $state(false);

	async function signIn() {
		error = '';
		busy = true;
		try {
			await session.signInWithGoogle();
			// 成功すると Google へリダイレクトするので、ここには戻ってこない
		} catch (e) {
			error = e instanceof Error ? e.message : 'ログインに失敗した';
			busy = false;
		}
	}
</script>

<div class="page login">
	<h1>personal-coach</h1>
	<p class="muted">Garmin の記録と手動ログを集約し、日々のメニューを提案する。</p>

	<button class="google" onclick={signIn} disabled={busy}>
		<svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
			<path
				fill="#4285F4"
				d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.92c1.7-1.57 2.68-3.88 2.68-6.62z"
			/>
			<path
				fill="#34A853"
				d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.92-2.26c-.8.54-1.84.86-3.04.86-2.34 0-4.32-1.58-5.03-3.7H.96v2.33A9 9 0 0 0 9 18z"
			/>
			<path fill="#FBBC05" d="M3.97 10.72a5.4 5.4 0 0 1 0-3.44V4.95H.96a9 9 0 0 0 0 8.1l3.01-2.33z" />
			<path
				fill="#EA4335"
				d="M9 3.58c1.32 0 2.5.45 3.44 1.35l2.58-2.59C13.46.9 11.43 0 9 0A9 9 0 0 0 .96 4.95l3.01 2.33C4.68 5.16 6.66 3.58 9 3.58z"
			/>
		</svg>
		{busy ? 'リダイレクト中…' : 'Google でログイン'}
	</button>

	{#if error}<p class="error">{error}</p>{/if}

	<!--
		対象アカウントは count-upper の Google SSO で作られた auth.users の行であり、
		パスワードを持たない。ログイン後に coach.app_owner に登録されている必要がある。
		docs/adr/0006-share-existing-supabase-project.md
	-->
	<p class="muted note">
		count-upper と同じ Google アカウントでログインする。
	</p>

	<!-- ログイン前でもどのデプロイを開いているか分かるようにする -->
	<p class="muted build">{buildInfoLine()}</p>
</div>

<style>
	.login {
		display: flex;
		flex-direction: column;
		justify-content: center;
		min-height: 100dvh;
		text-align: center;
		gap: 0.5rem;
	}

	.google {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.75rem;
		margin: 1.5rem auto 0;
		padding: 0.75rem 1.5rem;
		border-radius: 999px;
		background: #fff;
		color: #16191d;
		font-weight: 600;
	}

	.note {
		margin-top: 1.5rem;
		font-size: 0.8rem;
	}

	.build {
		margin: 0.25rem 0 0;
		font-size: 0.7rem;
		font-variant-numeric: tabular-nums;
	}
</style>
