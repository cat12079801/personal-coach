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

<section class="entry">
	<!-- 和文なので lab（大文字化・トラッキング）は掛けない。design.md「書体」を参照 -->
	<div class="entry__lab muted">
		{#if !draft.active}<span class="off">停止中</span> ・{/if}
		週 {draft.weekly_target} 回 ・ 中 {draft.min_gap_days - 1} 日
	</div>

	<div class="entry__line">
		<div>
			<div class="entry__title">{draft.name || '(名称未設定)'}</div>
			{#if draft.stages.length === 0}
				<div class="entry__sub muted">段階が未定義。編集して追加する。</div>
			{:else}
				<div class="entry__sub">
					{current?.label || '(ラベルなし)'}{#if current?.sets} ・{current.sets} セット{/if}
				</div>
				{#if current?.note}<div class="entry__note muted">{current.note}</div>{/if}
			{/if}
		</div>
		{#if draft.stages.length > 0}
			<div class="figure">
				{draft.stage}<span class="figure__unit">/ {draft.stages.length}</span>
			</div>
		{/if}
	</div>

	<div class="actions">
		{#if draft.stages.length > 0}
			<!-- 段階は自動で上がらない。できるようになったら自分で上げる（OD-5） -->
			<button
				class="button--quiet"
				onclick={() => bump(-1)}
				disabled={busy || draft.stage <= 1}
			>
				下げる
			</button>
			<button
				class="button--quiet"
				onclick={() => bump(1)}
				disabled={busy || draft.stage >= draft.stages.length}
			>
				上げる
			</button>
		{/if}
		<button class="linkish" onclick={() => (open = !open)}>
			{open ? '閉じる' : '編集'}
		</button>
	</div>

	{#if open}
		<div class="editor">
			<label>
				<span>名前</span>
				<input type="text" bind:value={draft.name} />
			</label>

			<div class="two">
				<label>
					<span>週の回数</span>
					<input type="number" min="1" max="7" inputmode="numeric" bind:value={draft.weekly_target} />
				</label>
				<label>
					<!-- min_gap_days は日付差。2 なら中 1 日 -->
					<span>最短間隔（日数差）</span>
					<input type="number" min="1" inputmode="numeric" bind:value={draft.min_gap_days} />
				</label>
			</div>

			<div class="two">
				<label>
					<span>表示順</span>
					<input type="number" inputmode="numeric" bind:value={draft.sort_order} />
				</label>
				<label class="checkbox">
					<input type="checkbox" bind:checked={draft.active} />
					<span>メニューに出す</span>
				</label>
			</div>

			<h3>段階</h3>
			<p class="muted">上から順に 1、2、3… となる。内容は自分で決める。</p>

			{#each draft.stages as stage, i (i)}
				<div class="stage" class:stage--current={i === draft.stage - 1}>
					<div class="stage__head">
						<span class="lab">
							{#if i === draft.stage - 1}<span class="mark"></span>{/if}Stage {i + 1}
						</span>
						<span class="stage__ops">
							<button class="linkish" onclick={() => moveStage(i, -1)} disabled={i === 0}>上へ</button>
							<button
								class="linkish"
								onclick={() => moveStage(i, 1)}
								disabled={i === draft.stages.length - 1}
							>
								下へ
							</button>
							<button class="linkish" onclick={() => removeStage(i)}>消す</button>
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
								inputmode="numeric"
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

			<button class="button--quiet" onclick={addStage}>段階を足す</button>

			<div class="actions actions--editor">
				<button
					class="button--ink"
					onclick={save}
					data-state={busy ? 'loading' : undefined}
					disabled={busy || !dirty}
				>
					{busy ? '保存中…' : '保存'}
				</button>
				<button class="button--quiet" onclick={reset} disabled={busy || !dirty}>取り消し</button>
				{#if confirmingDelete}
					<button
						class="button--danger"
						onclick={async () => {
							busy = true;
							await ondelete(draft.id);
						}}
					>
						本当に消す
					</button>
					<button class="button--quiet" onclick={() => (confirmingDelete = false)}>やめる</button>
				{:else}
					<button class="linkish" onclick={() => (confirmingDelete = true)}>この種目を消す</button>
				{/if}
			</div>
		</div>
	{/if}
</section>

<style>
	.off {
		color: var(--color-danger);
	}

	.actions {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--space-xs);
		margin-top: var(--space-sm);
	}

	.actions--editor {
		margin-top: var(--space-md);
	}

	.editor {
		margin-top: var(--space-md);
		padding-top: var(--space-md);
		border-top: var(--rule-hair) solid var(--color-rule);
	}

	.two {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: var(--space-xs);
	}

	/* 箱の中に箱を作らない。段階は罫線で区切った行にする */
	.stage {
		padding: var(--space-sm) 0;
		border-top: var(--rule-hair) solid var(--color-rule);
	}

	.stage__head {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: var(--space-xs);
		margin-bottom: var(--space-2xs);
	}

	.stage__ops {
		display: flex;
		gap: var(--space-sm);
	}

	/* 現在の段階は色の四角だけで示す。縁を太くすると箱に見える */
	.stage--current .lab {
		color: var(--color-accent);
	}

	.mark {
		display: inline-block;
		width: 0.5rem;
		height: 0.5rem;
		margin-right: var(--space-2xs);
		background: var(--color-accent);
	}

	.checkbox {
		display: flex;
		align-items: center;
		gap: var(--space-xs);
	}

	.checkbox input {
		width: auto;
	}

	.checkbox span {
		margin: 0;
	}

	h3 {
		font-family: var(--font-display);
		font-size: var(--text-sm);
		font-weight: 700;
		letter-spacing: 0.14em;
		text-transform: uppercase;
		color: var(--color-ink-2);
		margin: var(--space-lg) 0 var(--space-2xs);
	}
</style>
