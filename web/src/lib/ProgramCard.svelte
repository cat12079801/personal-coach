<script lang="ts">
	import { untrack } from 'svelte';
	import type { Stage, StrengthProgram } from '$lib/types';

	type Props = {
		program: StrengthProgram;
		onsave: (program: StrengthProgram) => Promise<void>;
		ondelete: (id: string) => Promise<void>;
	};

	let { program, onsave, ondelete }: Props = $props();

	// 編集用の複製。保存するまで元には触らない。
	// 初期値だけを取り込みたいので untrack で明示する（追従は下の $effect が担う）
	let draft = $state<StrengthProgram>(untrack(() => JSON.parse(JSON.stringify(program))));
	// 親が再取得したかを判定するための、最後に同期した内容
	let synced = $state(untrack(() => JSON.stringify(program)));
	let open = $state(false);
	let busy = $state(false);
	let confirmingDelete = $state(false);

	const current = $derived(draft.stages[draft.stage - 1]);
	const dirty = $derived(JSON.stringify(draft) !== JSON.stringify(program));

	// 親が再読み込みすると program が差し替わる。保存直後の値を反映させたい一方で、
	// 別カードの保存に巻き込まれて編集中の内容を失わないよう、未保存なら上書きしない
	$effect(() => {
		const incoming = JSON.stringify(program);
		if (incoming === synced) return;
		if (JSON.stringify(draft) === synced) draft = JSON.parse(incoming);
		synced = incoming;
	});

	function addStage() {
		draft.stages = [...draft.stages, { label: '', sets: 3, note: null }];
	}

	function removeStage(index: number) {
		draft.stages = draft.stages.filter((_, i) => i !== index);
		// 段階を消したら現在段階が範囲外になりうる
		draft.stage = Math.min(draft.stage, Math.max(draft.stages.length, 1));
	}

	function moveStage(index: number, delta: number) {
		const to = index + delta;
		if (to < 0 || to >= draft.stages.length) return;
		const next = [...draft.stages];
		[next[index], next[to]] = [next[to], next[index]];
		draft.stages = next;
	}

	/** 段階の上げ下げ。自動進行は採らず手動で操作する（OD-5） */
	async function bump(delta: number) {
		const next = draft.stage + delta;
		if (next < 1 || next > draft.stages.length) return;
		draft.stage = next;
		busy = true;
		await onsave($state.snapshot(draft));
		busy = false;
	}

	async function save() {
		busy = true;
		await onsave($state.snapshot(draft));
		busy = false;
	}

	function reset() {
		draft = JSON.parse(JSON.stringify(program));
	}

	function stageNumber(value: string): number | null {
		return value === '' ? null : Number(value);
	}
</script>

<div class="card">
	<div class="row">
		<strong>{draft.name || '(名称未設定)'}</strong>
		<span class="muted">
			{#if !draft.active}停止中 ・ {/if}週 {draft.weekly_target} 回 ・ 中 {draft.min_gap_days - 1} 日
		</span>
	</div>

	{#if draft.stages.length === 0}
		<p class="muted">段階が未定義。編集して追加する。</p>
	{:else}
		<div class="muted">段階 {draft.stage} / {draft.stages.length}</div>
		<div>
			{current?.label || '(ラベルなし)'}{#if current?.sets} ・{current.sets} セット{/if}
		</div>
		{#if current?.note}<div class="muted">{current.note}</div>{/if}

		<div class="stage-buttons">
			<button onclick={() => bump(-1)} disabled={busy || draft.stage <= 1}>← 下げる</button>
			<button onclick={() => bump(1)} disabled={busy || draft.stage >= draft.stages.length}>
				上げる →
			</button>
		</div>
	{/if}

	<button onclick={() => (open = !open)} style="margin-top: 0.75rem;">
		{open ? '閉じる' : '編集'}
	</button>

	{#if open}
		<div class="editor">
			<label>
				<span>名前</span>
				<input type="text" bind:value={draft.name} />
			</label>

			<div class="two">
				<label>
					<span>週の回数</span>
					<input type="number" min="1" max="7" bind:value={draft.weekly_target} />
				</label>
				<label>
					<!-- min_gap_days は日付差。2 なら中 1 日 -->
					<span>最短間隔（日数差）</span>
					<input type="number" min="1" bind:value={draft.min_gap_days} />
				</label>
			</div>

			<label>
				<span>表示順</span>
				<input type="number" bind:value={draft.sort_order} />
			</label>

			<label class="checkbox">
				<input type="checkbox" bind:checked={draft.active} />
				<span>有効にする（外すとメニューに出さない）</span>
			</label>

			<h3>段階</h3>
			<p class="muted">上から順に 1、2、3… となる。内容は自分で決める。</p>

			{#each draft.stages as stage, i (i)}
				<div class="stage" class:stage--current={i === draft.stage - 1}>
					<div class="row">
						<strong class="muted">段階 {i + 1}</strong>
						<span>
							<button onclick={() => moveStage(i, -1)} disabled={i === 0}>↑</button>
							<button onclick={() => moveStage(i, 1)} disabled={i === draft.stages.length - 1}>
								↓
							</button>
							<button onclick={() => removeStage(i)}>削除</button>
						</span>
					</div>
					<label>
						<span>内容</span>
						<input type="text" bind:value={stage.label} placeholder="タックプランシェ 10 秒" />
					</label>
					<div class="two">
						<label>
							<span>セット数</span>
							<input
								type="number"
								min="1"
								value={stage.sets ?? ''}
								onchange={(e) => (stage.sets = stageNumber(e.currentTarget.value))}
							/>
						</label>
						<label>
							<span>メモ</span>
							<input
								type="text"
								value={stage.note ?? ''}
								onchange={(e) => (stage.note = e.currentTarget.value || null)}
							/>
						</label>
					</div>
				</div>
			{/each}

			<button onclick={addStage}>＋ 段階を追加</button>

			<div class="actions">
				<button class="button--primary" onclick={save} disabled={busy || !dirty}>
					{busy ? '…' : '保存'}
				</button>
				<button onclick={reset} disabled={busy || !dirty}>取り消し</button>
				{#if confirmingDelete}
					<button
						class="danger"
						onclick={async () => {
							busy = true;
							await ondelete(draft.id);
						}}
					>
						本当に削除する
					</button>
					<button onclick={() => (confirmingDelete = false)}>やめる</button>
				{:else}
					<button onclick={() => (confirmingDelete = true)}>削除</button>
				{/if}
			</div>
		</div>
	{/if}
</div>

<style>
	.stage-buttons {
		display: flex;
		gap: 0.5rem;
		margin-top: 0.75rem;
	}

	.editor {
		margin-top: 1rem;
		padding-top: 1rem;
		border-top: 1px solid var(--border);
	}

	.two {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 0.5rem;
	}

	.stage {
		border: 1px solid var(--border);
		border-radius: 0.5rem;
		padding: 0.75rem;
		margin-bottom: 0.5rem;
	}

	.stage--current {
		border-color: var(--accent);
	}

	.checkbox {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.checkbox input {
		width: auto;
	}

	.checkbox span {
		margin: 0;
	}

	h3 {
		font-size: 0.9rem;
		margin: 1.25rem 0 0.25rem;
	}

	.actions {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
		margin-top: 1rem;
	}

	.danger {
		background: var(--danger);
		border-color: var(--danger);
		color: #fff;
	}
</style>
