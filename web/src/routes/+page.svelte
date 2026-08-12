<script lang="ts">
	import { db } from '$lib/supabase';
	import { todayJst, formatDateTime, formatDuration, formatEventTime } from '$lib/format';
	import type {
		DailyMenu,
		OwnStrength,
		StrengthCompletion,
		StrengthEntry
	} from '$lib/types';

	const today = todayJst();

	let menu = $state<DailyMenu | null>(null);
	let loading = $state(true);
	let requesting = $state(false);
	let requested = $state(false);
	let loadError = $state('');
	let error = $state('');
	/** 完了済みの独自筋トレ。program_id → 記録した行と実績 */
	let done = $state<Record<string, { logId: string; entry: StrengthEntry }>>({});
	let toggling = $state('');
	let savingActual = $state('');
	let savedActual = $state('');

	async function load() {
		loading = true;
		loadError = '';
		try {
			const { data, error: e } = await db()
				.from('daily_menus')
				.select('*')
				.eq('date', today)
				.maybeSingle();
			if (e) throw new Error(e.message);
			menu = data as DailyMenu | null;
		} catch (e) {
			loadError = e instanceof Error ? e.message : String(e);
		} finally {
			loading = false;
		}
	}

	/**
	 * 完了を押した時点の実績。**メニューのセット数ぶんの空枠だけを作る。**
	 *
	 * レップ数・秒数は入れない。メニューは「15 秒キープ」等の目標であって実績ではなく、
	 * 目標値を初期値に入れると「やった数」と区別が付かなくなるため。
	 * 数値と セット数は後から編集する。
	 */
	function initialEntry(item: OwnStrength): StrengthEntry {
		return {
			// 種目が消えても何をやったか残るよう、段階の内容をここに写す
			name: item.label ?? item.program,
			stage: item.stage,
			// キープ系は秒で数える。ラベルから当たりを付けるだけなので UI で変えられる
			unit: /秒/.test(item.label ?? '') ? 'seconds' : 'reps',
			planned_sets: item.sets,
			sets: Array.from({ length: item.sets ?? 0 }, () => ({ value: null }))
		};
	}

	function unitLabel(entry: StrengthEntry): string {
		return entry.unit === 'seconds' ? '秒' : '回';
	}

	function actualSummary(entry: StrengthEntry): string {
		const count = `${entry.sets.length} セット`;
		if (entry.sets.every((set) => set.value == null)) return `${count}・数値は未記入`;
		return `${count}・${entry.sets.map((set) => set.value ?? '—').join(' / ')} ${unitLabel(entry)}`;
	}

	/**
	 * 当日ぶんの完了記録を読む。
	 * program_id が入っている行だけがメニュー由来（/logs の自由入力は null）。
	 */
	async function loadDone() {
		// supabase-js は例外を投げず { error } を返す。握りつぶすと「UI は成功、DB は空」になる
		const { data, error: e } = await db()
			.from('strength_logs')
			.select('id, program_id, menu_date, exercises')
			.eq('menu_date', today)
			.not('program_id', 'is', null);
		if (e) {
			error = e.message;
			return;
		}
		done = Object.fromEntries(
			(data as StrengthCompletion[]).map((row) => [
				row.program_id,
				{
					logId: row.id,
					entry: row.exercises?.[0] ?? {
						name: '',
						unit: 'reps' as const,
						planned_sets: null,
						sets: []
					}
				}
			])
		);
	}

	/**
	 * 完了のトグル。押し間違いを戻せるよう取り消しも同じボタンで行う。
	 *
	 * この記録はメニュー生成のルールには影響しない。実施回数と間隔は
	 * 過去の daily_menus で数える（batch/src/personal_coach/menu/rules.py）。
	 */
	async function toggleDone(item: OwnStrength) {
		toggling = item.program_id;
		error = '';
		const record = done[item.program_id];

		if (record) {
			const { error: e } = await db().from('strength_logs').delete().eq('id', record.logId);
			if (e) error = e.message;
			else {
				const next = { ...done };
				delete next[item.program_id];
				done = next;
			}
		} else {
			const entry = initialEntry(item);
			const { data, error: e } = await db()
				.from('strength_logs')
				.insert({
					performed_at: new Date().toISOString(),
					menu_date: today,
					program_id: item.program_id,
					exercises: [entry]
				})
				.select('id')
				.single();
			if (e) error = e.message;
			else done = { ...done, [item.program_id]: { logId: (data as { id: string }).id, entry } };
		}
		toggling = '';
	}

	function addSet(programId: string) {
		done[programId]?.entry.sets.push({ value: null });
		savedActual = '';
	}

	function removeSet(programId: string) {
		done[programId]?.entry.sets.pop();
		savedActual = '';
	}

	/** 実績の保存。メニュー側は一切書き換えない。 */
	async function saveActual(programId: string) {
		const record = done[programId];
		if (!record) return;
		savingActual = programId;
		savedActual = '';
		error = '';
		const { error: e } = await db()
			.from('strength_logs')
			// $state のプロキシをそのまま渡さない
			.update({ exercises: [$state.snapshot(record.entry)] })
			.eq('id', record.logId);
		if (e) error = e.message;
		else savedActual = programId;
		savingActual = '';
	}

	/**
	 * .ics は Google 側でキャッシュされ反映が数時間遅れることがある。
	 * 前夜遅くに入れた予定を 03:00 のバッチが拾えないため、手動リカバリの導線を必ず置く。
	 * 詳細は docs/adr/0003-ical-instead-of-oauth.md。
	 */
	async function requestRegenerate() {
		requesting = true;
		error = '';
		const { error: e } = await db().from('regenerate_requests').insert({ target_date: today });
		if (e) error = e.message;
		else requested = true;
		requesting = false;
	}

	$effect(() => {
		void load();
		void loadDone();
	});
</script>

<svelte:head><title>今日のトレーニング</title></svelte:head>

<div class="page">
	<h1>今日のトレーニング</h1>

	{#if loading}
		<p class="muted">読み込み中…</p>
	{:else if loadError}
		<div class="card">
			<p class="error">{loadError}</p>
			<button onclick={load}>再読み込み</button>
		</div>
	{:else if !menu}
		<div class="empty">
			<p>{today} のメニューはまだ生成されていない。</p>
			<p class="muted">03:00 JST のバッチで生成される。</p>
		</div>
	{:else}
		<div class="card">
			<p style="margin-top: 0; font-size: 1.05rem;">{menu.menu.summary ?? '（要約なし）'}</p>
			<p class="muted">生成 {formatDateTime(menu.generated_at)}</p>
		</div>

		<h2>ラン</h2>
		{#if menu.menu.rest_day}
			<div class="card muted">休養日</div>
		{:else if menu.menu.run}
			<!-- Garmin コーチのプランは改変しない。取得したまま表示する -->
			<div class="card">
				<div class="row">
					<strong>{menu.menu.run.name ?? 'ラン'}</strong>
					<span class="muted">{formatDuration(menu.menu.run.duration_sec)}</span>
				</div>
				{#if menu.menu.run.intensity}
					<div class="muted">{menu.menu.run.intensity}</div>
				{/if}
			</div>
		{:else}
			<div class="card muted">なし</div>
		{/if}

		{#if menu.menu.garmin_strength?.length}
			<h2>補強（Garmin）</h2>
			{#each menu.menu.garmin_strength as item, i (i)}
				<div class="card">
					<div class="row">
						<strong>{item.name ?? '補強'}</strong>
						<span class="muted">{formatDuration(item.duration_sec)}</span>
					</div>
				</div>
			{/each}
		{/if}

		{#if menu.menu.own_strength?.length}
			<h2>筋トレ</h2>
			{#each menu.menu.own_strength as item (item.program_id)}
				<div class="card">
					<div class="row">
						<strong>{item.program}</strong>
						<span class="muted">段階 {item.stage}</span>
					</div>
					<div>{item.label ?? ''}{#if item.sets} ・{item.sets} セット{/if}</div>
					{#if item.note}<div class="muted">{item.note}</div>{/if}
					<button
						style="margin-top: 0.75rem;"
						class:button--primary={!done[item.program_id]}
						disabled={toggling === item.program_id}
						onclick={() => toggleDone(item)}
					>
						{done[item.program_id] ? '✓ 完了済み（取り消す）' : '完了にする'}
					</button>

					<!--
						実績はメニューと独立に持つ。メニューは目標であって実績ではないので、
						セット数もレップ数もここで自由に変えられる。
					-->
					{#if done[item.program_id]}
						{@const record = done[item.program_id]}
						<details style="margin-top: 0.75rem;">
							<summary class="muted">実績 {actualSummary(record.entry)}</summary>

							<label style="margin-top: 0.75rem;">
								<span>数え方</span>
								<select bind:value={record.entry.unit}>
									<option value="reps">レップ</option>
									<option value="seconds">秒</option>
								</select>
							</label>

							{#each record.entry.sets as set, i (i)}
								<label>
									<span>{i + 1} セット目（{unitLabel(record.entry)}）</span>
									<input type="number" min="0" bind:value={set.value} />
								</label>
							{/each}

							<div class="row" style="justify-content: flex-start;">
								<button type="button" onclick={() => addSet(item.program_id)}>＋ セット</button>
								<button
									type="button"
									disabled={record.entry.sets.length === 0}
									onclick={() => removeSet(item.program_id)}
								>
									− セット
								</button>
							</div>

							{#if record.entry.planned_sets}
								<p class="muted">メニューの提示は {record.entry.planned_sets} セット。</p>
							{/if}

							<button
								class="button--primary"
								style="margin-top: 0.5rem;"
								disabled={savingActual === item.program_id}
								onclick={() => saveActual(item.program_id)}
							>
								{savingActual === item.program_id ? '…' : '実績を保存'}
							</button>
							{#if savedActual === item.program_id}<span class="muted"> 保存した。</span>{/if}
						</details>
					{/if}
				</div>
			{/each}
		{/if}

		<!--
			カレンダーの予定。メニュー生成のルールには使われず、表示専用。
			「今日やることを 1 画面で確認する」ためのもの。
		-->
		<h2>今日の予定</h2>
		{#if menu.menu.schedule?.length}
			{#each menu.menu.schedule as event, i (i)}
				<div class="card">
					<div class="row">
						<strong>{event.summary || '(無題)'}</strong>
						<span class="muted">{formatEventTime(event.start, event.all_day)}</span>
					</div>
				</div>
			{/each}
		{:else}
			<div class="card muted">予定なし</div>
		{/if}

		<h2>生成根拠</h2>
		<details class="card">
			<summary class="muted">source を表示</summary>
			<pre style="white-space: pre-wrap; font-size: 0.75rem;">{JSON.stringify(
					menu.source,
					null,
					2
				)}</pre>
		</details>
	{/if}

	<h2>手動リカバリ</h2>
	<div class="card">
		<p class="muted" style="margin-top: 0;">
			カレンダーの反映が遅れて予定を拾えていない場合に再生成する。
		</p>
		<button onclick={requestRegenerate} disabled={requesting || requested}>
			{requested ? '再生成をリクエスト済み' : 'メニューを再生成'}
		</button>
	</div>

	{#if error}<p class="error">{error}</p>{/if}
</div>
