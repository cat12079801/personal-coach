<script lang="ts">
	import { db } from '$lib/supabase';
	import ProgramCard from '$lib/ProgramCard.svelte';
	import type { StrengthProgram } from '$lib/types';

	let programs = $state<StrengthProgram[]>([]);
	let loading = $state(true);
	let error = $state('');

	async function load() {
		loading = true;
		error = '';
		try {
			const { data, error: e } = await db()
				.from('strength_programs')
				.select('*')
				.order('sort_order')
				.order('name');
			if (e) throw new Error(e.message);
			programs = (data ?? []) as StrengthProgram[];
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		} finally {
			loading = false;
		}
	}

	async function save(program: StrengthProgram) {
		error = '';
		const { error: e } = await db().from('strength_programs').update({
			name: program.name,
			stage: program.stage,
			stages: program.stages,
			weekly_target: program.weekly_target,
			min_gap_days: program.min_gap_days,
			sort_order: program.sort_order,
			active: program.active
		}).eq('id', program.id);
		if (e) error = e.message;
		await load();
	}

	async function remove(id: string) {
		error = '';
		const { error: e } = await db().from('strength_programs').delete().eq('id', id);
		if (e) error = e.message;
		await load();
	}

	async function add() {
		error = '';
		const { error: e } = await db()
			.from('strength_programs')
			.insert({ name: '新しい種目', sort_order: programs.length });
		if (e) error = e.message;
		await load();
	}

	$effect(() => {
		void load();
	});
</script>

<svelte:head><title>筋トレプログラム</title></svelte:head>

<div class="page">
	<div class="row">
		<h1>筋トレプログラム</h1>
		<a href="/settings">← 設定</a>
	</div>

	<!--
		Garmin コーチの筋トレはランの補強に閉じているので、上半身とスキル系をここで足す。
		段階の中身はアプリ側では持たず、本人が定義する（docs/08-open-decisions.md の OD-5）。
	-->
	<p class="muted">
		ここに登録した種目が、休養日やポイント練習でない日のメニューに載る。
		段階は自動では上がらない。できるようになったら自分で上げる。
	</p>

	{#if error}<p class="error">{error}</p>{/if}

	{#if loading}
		<p class="muted">読み込み中…</p>
	{:else if programs.length === 0}
		<div class="empty">
			<p>まだ登録がない。</p>
			<p class="muted">登録するまで、メニューに筋トレは出ない。</p>
		</div>
	{:else}
		{#each programs as program (program.id)}
			<ProgramCard {program} onsave={save} ondelete={remove} />
		{/each}
	{/if}

	<button class="button--primary" onclick={add} style="margin-top: 0.5rem;">＋ 種目を追加</button>
</div>
