<script lang="ts">
	import { page } from '$app/state';
	import { db } from '$lib/supabase';
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
	<h1>手動登録</h1>

	<form class="card" onsubmit={submit}>
		<label>
			<span>種目</span>
			<select bind:value={kind}>
				{#each Object.entries(LOG_TABLES) as [key, spec] (key)}
					<option value={key}>{spec.label}</option>
				{/each}
			</select>
		</label>

		<label>
			<span>日時</span>
			<input type="datetime-local" bind:value={at} required />
		</label>


		<span class="muted">{kind === 'strength' ? 'エクササイズ' : '要素'}</span>
		{#each items as item, i (i)}
			<div class="card" style="background: transparent;">
				{#each FIELDS[kind] as field (field.key)}
					<label>
						<span>{field.label}</span>
						{#if field.type === 'check'}
							<input
								type="checkbox"
								style="width: auto;"
								checked={Boolean(item[field.key])}
								onchange={(e) => (item[field.key] = e.currentTarget.checked)}
							/>
						{:else if field.type === 'number'}
							<input
								type="number"
								value={(item[field.key] as number) ?? ''}
								onchange={(e) =>
									(item[field.key] = e.currentTarget.value === ''
										? undefined
										: Number(e.currentTarget.value))}
							/>
						{:else}
							<input
								type="text"
								value={(item[field.key] as string) ?? ''}
								onchange={(e) => (item[field.key] = e.currentTarget.value || undefined)}
							/>
						{/if}
					</label>
				{/each}
				{#if items.length > 1}
					<button type="button" onclick={() => removeItem(i)}>削除</button>
				{/if}
			</div>
		{/each}
		<button type="button" onclick={addItem}>＋ 追加</button>

		<label style="margin-top: 1rem;">
			<!-- 心拍が当てにならない種目があるため RPE で補正する（docs/01-overview.md） -->
			<span>RPE（主観強度 1-10）</span>
			<input type="number" min="1" max="10" bind:value={rpe} />
		</label>

		<label>
			<span>メモ</span>
			<textarea rows="2" bind:value={note}></textarea>
		</label>

		{#if activityId}
			<p class="muted">Garmin アクティビティに紐付けて保存する。</p>
		{/if}
		{#if error}<p class="error">{error}</p>{/if}
		{#if saved}<p class="muted">保存した。</p>{/if}

		<button class="button--primary" type="submit" disabled={saving}>
			{saving ? '…' : '保存'}
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
