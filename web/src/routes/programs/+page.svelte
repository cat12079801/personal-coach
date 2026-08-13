<script lang="ts">
	import { db } from '$lib/supabase';
	import { designMode } from '$lib/design';
	import { designPrograms } from '$lib/fixtures';
	import ProgramCard from '$lib/ProgramCard.svelte';
	import type { StrengthProgram } from '$lib/types';

	let programs = $state<StrengthProgram[]>([]);
	let loading = $state(true);
	let error = $state('');

	/**
	 * デザイン検証モードの編集はメモリ上だけで完結させる。
	 * load() で読み直すと編集が消えるので、フィクスチャは初回だけ複製して持つ。
	 */
	let designLoaded = false;

	async function load() {
		loading = true;
		error = '';
		if (designMode) {
			if (!designLoaded) {
				programs = designPrograms.map((p) => ({ ...p, stages: p.stages.map((s) => ({ ...s })) }));
				designLoaded = true;
			}
			loading = false;
			return;
		}
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
		if (designMode) {
			programs = programs.map((p) => (p.id === program.id ? { ...program } : p));
			return;
		}
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
		if (designMode) {
			programs = programs.filter((p) => p.id !== id);
			return;
		}
		const { error: e } = await db().from('strength_programs').delete().eq('id', id);
		if (e) error = e.message;
		await load();
	}

	async function add() {
		error = '';
		if (designMode) {
			programs = [
				...programs,
				{
					id: `design-new-${programs.length}`,
					name: '新しい種目',
					stage: 1,
					stages: [],
					weekly_target: 2,
					min_gap_days: 2,
					sort_order: programs.length,
					active: true
				}
			];
			return;
		}
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
	<a class="back" href="/settings">← 設定</a>
	<h1>筋トレプログラム</h1>

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
