<script lang="ts">
	import { db } from '$lib/supabase';
	import { designMode } from '$lib/design';
	import { designStrengthLogs } from '$lib/fixtures';
	import { formatDateTime, localInputToIso, nowForInput } from '$lib/format';
	import { STRENGTH_LOG, type ManualLog } from '$lib/types';

	/**
	 * 詳細フィールド。jsonb にそのまま入る（OD-3）。
	 * 手動登録は筋トレだけ。スケートの手動ログは 0008 で廃止した。
	 */
	const FIELDS: { key: string; label: string; type: 'text' | 'number' }[] = [
		{ key: 'name', label: '種目', type: 'text' },
		{ key: 'reps', label: 'レップ', type: 'number' },
		{ key: 'weight_kg', label: '重量 (kg)', type: 'number' },
		{ key: 'sets', label: 'セット', type: 'number' }
	];

	let at = $state(nowForInput());
	let rpe = $state<number | null>(null);
	let note = $state('');
	let items = $state<Record<string, unknown>[]>([{}]);
	let saving = $state(false);
	let error = $state('');
	let saved = $state(false);

	let recent = $state<ManualLog[]>([]);

	function addItem() {
		items = [...items, {}];
	}

	function removeItem(index: number) {
		items = items.filter((_, i) => i !== index);
	}

	async function loadRecent() {
		if (designMode) {
			recent = designStrengthLogs;
			return;
		}
		const { data, error: e } = await db()
			.from(STRENGTH_LOG.table)
			.select('*')
			.order(STRENGTH_LOG.at, { ascending: false })
			.limit(20);
		if (e) error = e.message;
		else recent = (data ?? []) as ManualLog[];
	}

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		saving = true;
		error = '';
		saved = false;

		const payload: Record<string, unknown> = {
			// 付け忘れ・充電切れの回があるので activity_id は NULL 許容。無理に紐付けない
			[STRENGTH_LOG.at]: localInputToIso(at),
			[STRENGTH_LOG.detail]: items.filter((item) => Object.keys(item).length > 0),
			rpe,
			note: note || null
		};

		if (designMode) {
			// 保存はせず、一覧の先頭に足して見た目だけ確認できるようにする
			recent = [{ ...(payload as unknown as ManualLog), id: `design-new-${recent.length}` }, ...recent];
			saved = true;
			items = [{}];
			note = '';
			rpe = null;
			saving = false;
			return;
		}

		const { error: e } = await db().from(STRENGTH_LOG.table).insert(payload);
		if (e) {
			error = e.message;
		} else {
			saved = true;
			items = [{}];
			note = '';
			rpe = null;
			await loadRecent();
		}
		saving = false;
	}

	$effect(() => {
		void loadRecent();
	});
</script>

<svelte:head><title>手動登録</title></svelte:head>

<div class="page">
	<h1>手動登録</h1>

	<!--
		メニューに無い筋トレを書き足すための画面。
		縦に伸びると入力が終わらないので、数値は 1 行に畳み、RPE とメモは畳んでおく。
	-->
	<form onsubmit={submit}>
		<label>
			<span>日時</span>
			<input type="datetime-local" bind:value={at} required />
		</label>

		{#each items as item, i (i)}
			<div class="item">
				<div class="item__head">
					<span class="lab">Exercise {i + 1}</span>
					{#if items.length > 1}
						<button type="button" class="linkish" onclick={() => removeItem(i)}>この行を消す</button>
					{/if}
				</div>

				<label>
					<span>{FIELDS[0].label}</span>
					<input
						type="text"
						value={(item[FIELDS[0].key] as string) ?? ''}
						onchange={(e) => (item[FIELDS[0].key] = e.currentTarget.value || undefined)}
					/>
				</label>

				<div class="item__nums">
					{#each FIELDS.slice(1) as field (field.key)}
						<label>
							<span>{field.label}</span>
							<input
								type="number"
								inputmode="numeric"
								value={(item[field.key] as number) ?? ''}
								onchange={(e) =>
									(item[field.key] = e.currentTarget.value === ''
										? undefined
										: Number(e.currentTarget.value))}
							/>
						</label>
					{/each}
				</div>
			</div>
		{/each}

		<button type="button" class="button--quiet" onclick={addItem}>行を足す</button>

		<details class="extra">
			<summary class="muted">RPE・メモ</summary>
			<label>
				<!-- 心拍が当てにならない種目があるため RPE で補正する（docs/01-overview.md） -->
				<span>RPE（主観強度 1-10）</span>
				<input type="number" min="1" max="10" inputmode="numeric" bind:value={rpe} />
			</label>

			<label>
				<span>メモ</span>
				<textarea rows="2" bind:value={note}></textarea>
			</label>
		</details>

		{#if error}<p class="error">{error}</p>{/if}
		{#if saved}<p class="muted">保存した。</p>{/if}

		<button
			class="button--ink"
			type="submit"
			data-state={saving ? 'loading' : undefined}
			disabled={saving}
		>
			{saving ? '保存中…' : '保存'}
		</button>
	</form>

	<h2>最近の記録</h2>
	{#if recent.length === 0}
		<div class="empty">まだ記録がない。</div>
	{:else}
		{#each recent as log (log.id)}
			{@const exercises = (log[STRENGTH_LOG.detail] as { name?: string }[]) ?? []}
			<section class="entry">
				<div class="entry__lab lab">
					<span class="num">{formatDateTime(log[STRENGTH_LOG.at] as string)}</span>
					{#if log.rpe}— RPE {log.rpe}{/if}
				</div>
				<div class="entry__line">
					<div>
						<div class="entry__title">{exercises[0]?.name ?? '筋トレ'}</div>
						{#if exercises.length > 1}
							<div class="entry__sub muted">
								ほか {exercises.slice(1).map((e) => e.name).filter(Boolean).join('、')}
							</div>
						{/if}
						{#if log.note}<div class="entry__note muted">{log.note}</div>{/if}
					</div>
					<div class="figure figure--sm">
						{exercises.length}<span class="figure__unit">種目</span>
					</div>
				</div>
			</section>
		{/each}
	{/if}
</div>

<style>
	.item {
		padding: var(--space-sm) 0;
		border-bottom: var(--rule-hair) solid var(--color-rule);
	}

	.item__head {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: var(--space-xs);
	}

	/* 数値は 1 行に畳む。3 つ縦に並べると入力が終わらない */
	.item__nums {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(5.5rem, 1fr));
		gap: var(--space-xs);
	}

	.extra {
		margin: var(--space-md) 0;
	}
</style>
