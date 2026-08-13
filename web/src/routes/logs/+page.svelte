<script lang="ts">
	import { page } from '$app/state';
	import { db } from '$lib/supabase';
	import { designMode } from '$lib/design';
	import { designSkatingLogs, designStrengthLogs } from '$lib/fixtures';
	import { formatDateTime, localInputToIso, nowForInput } from '$lib/format';
	import { LOG_TABLES, type LogKind, type ManualLog } from '$lib/types';

	/** 種目ごとの詳細フィールド。jsonb にそのまま入る。 */
	const FIELDS: Record<LogKind, { key: string; label: string; type: 'text' | 'number' | 'check' }[]> =
		{
			strength: [
				{ key: 'name', label: '種目', type: 'text' },
				{ key: 'reps', label: 'レップ', type: 'number' },
				{ key: 'weight_kg', label: '重量 (kg)', type: 'number' },
				{ key: 'sets', label: 'セット', type: 'number' }
			],
			skating: [
				{ key: 'name', label: '要素', type: 'text' },
				{ key: 'attempts', label: 'トライ数', type: 'number' },
				{ key: 'success', label: '成功', type: 'number' }
			]
		};

	let kind = $state<LogKind>('strength');
	let at = $state(nowForInput());
	let rpe = $state<number | null>(null);
	let note = $state('');
	let items = $state<Record<string, unknown>[]>([{}]);
	let saving = $state(false);
	let error = $state('');
	let saved = $state(false);
	type RecentLog = ManualLog & { kind: LogKind };

	let recent = $state<RecentLog[]>([]);

	// 未紐付け一覧から遷移してきた場合に紐付ける
	const activityId = $derived(page.url.searchParams.get('activity'));

	function addItem() {
		items = [...items, {}];
	}

	function removeItem(index: number) {
		items = items.filter((_, i) => i !== index);
	}

	async function loadRecent() {
		if (designMode) {
			// スプレッドは index signature を落とすので明示的に付け直す
			recent = [
				...designStrengthLogs.map((row) => ({ ...row, kind: 'strength' }) as RecentLog),
				...designSkatingLogs.map((row) => ({ ...row, kind: 'skating' }) as RecentLog)
			].sort(
				(a, b) =>
					new Date(b[LOG_TABLES[b.kind].at] as string).getTime() -
					new Date(a[LOG_TABLES[a.kind].at] as string).getTime()
			);
			return;
		}
		try {
			const results = await Promise.all(
				(Object.keys(LOG_TABLES) as LogKind[]).map(async (k) => {
					const { data } = await db()
						.from(LOG_TABLES[k].table)
						.select('*')
						.order(LOG_TABLES[k].at, { ascending: false })
						.limit(10);
					// スプレッドは index signature を落とすので明示的に付け直す
					return (data ?? []).map((row) => ({ ...(row as ManualLog), kind: k }) as RecentLog);
				})
			);
			recent = results
				.flat()
				.sort(
					(a, b) =>
						new Date(b[LOG_TABLES[b.kind].at] as string).getTime() -
						new Date(a[LOG_TABLES[a.kind].at] as string).getTime()
				)
				.slice(0, 20);
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		}
	}

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		saving = true;
		error = '';
		saved = false;

		const spec = LOG_TABLES[kind];
		const payload: Record<string, unknown> = {
			// 付け忘れ・充電切れの回があるので activity_id は NULL 許容。無理に紐付けない
			activity_id: activityId,
			[spec.at]: localInputToIso(at),
			[spec.detail]: items.filter((item) => Object.keys(item).length > 0),
			rpe,
			note: note || null
		};

		if (designMode) {
			// 保存はせず、一覧の先頭に足して見た目だけ確認できるようにする
			recent = [{ ...(payload as unknown as ManualLog), id: `design-new-${recent.length}`, kind }, ...recent];
			saved = true;
			items = [{}];
			note = '';
			rpe = null;
			saving = false;
			return;
		}

		const { error: e } = await db().from(spec.table).insert(payload);
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
	{#if activityId}
		<!-- 未紐付け一覧から来た場合。PWA には戻るボタンが無いので必ず導線を置く -->
		<a class="back" href="/unlinked">← 未紐付け</a>
	{/if}
	<h1>手動登録</h1>

	<!--
		縦に伸びると入力が終わらないので、数値は 1 行に畳み、
		RPE とメモは畳んでおく（既定では触らせない）。
	-->
	<form onsubmit={submit}>
		<div class="seg">
			{#each Object.entries(LOG_TABLES) as [key, spec] (key)}
				<button
					type="button"
					class="seg__btn"
					class:seg__btn--on={kind === key}
					aria-pressed={kind === key}
					onclick={() => (kind = key as LogKind)}
				>
					{spec.label}
				</button>
			{/each}
		</div>

		<label>
			<span>日時</span>
			<input type="datetime-local" bind:value={at} required />
		</label>

		{#each items as item, i (i)}
			{@const fields = FIELDS[kind]}
			<div class="item">
				<div class="item__head">
					<span class="lab">{kind === 'strength' ? `Exercise ${i + 1}` : `Element ${i + 1}`}</span>
					{#if items.length > 1}
						<button type="button" class="linkish" onclick={() => removeItem(i)}>この行を消す</button>
					{/if}
				</div>

				<label>
					<span>{fields[0].label}</span>
					<input
						type="text"
						value={(item[fields[0].key] as string) ?? ''}
						onchange={(e) => (item[fields[0].key] = e.currentTarget.value || undefined)}
					/>
				</label>

				<div class="item__nums">
					{#each fields.slice(1) as field (field.key)}
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

		{#if activityId}
			<p class="muted">Garmin アクティビティに紐付けて保存する。</p>
		{/if}
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
		{#each recent as log (log.kind + log.id)}
			<div class="card">
				<div class="row">
					<strong>{LOG_TABLES[log.kind].label}</strong>
					<span class="muted">
						{formatDateTime(log[LOG_TABLES[log.kind].at] as string)}
					</span>
				</div>
				<div class="muted">
					{(log[LOG_TABLES[log.kind].detail] as unknown[])?.length ?? 0} 件
					{#if log.rpe}・RPE {log.rpe}{/if}
					{#if !log.activity_id}・未紐付け{/if}
				</div>
				{#if log.note}<div>{log.note}</div>{/if}
			</div>
		{/each}
	{/if}
</div>

<style>
	/* 種目の切り替え。select だと開いて選ぶ 2 手になるので、2 択は並べて 1 手にする */
	.seg {
		display: flex;
		margin-bottom: var(--space-sm);
	}

	.seg__btn {
		flex: 1;
		border-right-width: 0;
	}

	.seg__btn:last-child {
		border-right-width: var(--rule-bold);
	}

	.seg__btn--on {
		background: var(--color-ink);
		color: var(--color-paper);
	}

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
