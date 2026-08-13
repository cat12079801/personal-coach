<script lang="ts">
	import { db } from '$lib/supabase';
	import { designMode } from '$lib/design';
	import { designCompletions, designMenu } from '$lib/fixtures';
	import {
		todayJst,
		formatDateTime,
		formatDayShort,
		formatEventTime,
		toMinutes
	} from '$lib/format';
	import { isAsPlanned } from '$lib/types';
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
		if (designMode) {
			menu = designMenu;
			loading = false;
			return;
		}
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
	 * 完了を押した時点の実績。**「メニューどおり実施した」として記録する。**
	 *
	 * 目標値を数値欄に写すことはしない。メニューの「15 秒キープ」は目標であって実績であり、
	 * 写してしまうと「実際にやった数」と区別が付かなくなる。代わりに `as_planned` を立て、
	 * セット数ぶんの空枠だけ作る。メニューと違うことをしたときだけ数値を入れて上書きする。
	 */
	function initialEntry(item: OwnStrength): StrengthEntry {
		return {
			// 種目が消えても何をやったか残るよう、段階の内容をここに写す
			name: item.label ?? item.program,
			stage: item.stage,
			// キープ系は秒で数える。ラベルから当たりを付けるだけなので UI で変えられる
			unit: /秒/.test(item.label ?? '') ? 'seconds' : 'reps',
			planned_sets: item.sets,
			as_planned: true,
			sets: Array.from({ length: item.sets ?? 0 }, () => ({ value: null }))
		};
	}

	function unitLabel(entry: StrengthEntry): string {
		return entry.unit === 'seconds' ? '秒' : '回';
	}

	function actualSummary(entry: StrengthEntry): string {
		const count = `${entry.sets.length} セット`;
		const blank = entry.sets.every((set) => set.value == null);
		if (blank && isAsPlanned(entry)) return `メニューどおり・${count}`;
		if (blank) return `${count}・数値は未記入`;
		return `${count}・${entry.sets.map((set) => set.value ?? '—').join(' / ')} ${unitLabel(entry)}`;
	}

	/**
	 * 当日ぶんの完了記録を読む。
	 * program_id が入っている行だけがメニュー由来（/logs の自由入力は null）。
	 */
	async function loadDone() {
		if (designMode) {
			done = Object.fromEntries(
				designCompletions.map((row) => [row.program_id, { logId: row.id, entry: row.exercises[0] }])
			);
			return;
		}
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

		// デザイン検証モードでは DB に書かず、見た目だけ切り替える
		if (designMode) {
			const next = { ...done };
			if (record) delete next[item.program_id];
			else next[item.program_id] = { logId: 'design-log-new', entry: initialEntry(item) };
			done = next;
			toggling = '';
			return;
		}

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

	/**
	 * 実績の書き換えは**必ず新しいオブジェクトを作って `done` に代入する**。
	 *
	 * `{#each ... as set}` のアイテムに `bind:value` する書き方では書き戻りが起きず、
	 * 入力しても値が反映されなかった（画面で確認済み）。イミュータブルに差し替える。
	 */
	function updateEntry(programId: string, change: Partial<StrengthEntry>) {
		const record = done[programId];
		if (!record) return;
		done = { ...done, [programId]: { ...record, entry: { ...record.entry, ...change } } };
		savedActual = '';
	}

	function setSetValue(programId: string, index: number, raw: string) {
		const sets = done[programId]?.entry.sets;
		if (!sets) return;
		updateEntry(programId, {
			// 数値を入れた時点で「メニューどおり」ではなくなる
			as_planned: false,
			sets: sets.map((set, i) => (i === index ? { value: raw === '' ? null : Number(raw) } : set))
		});
	}

	/** 「メニューどおり」に戻す。入れた数値は破棄する（提示どおりの意味と矛盾するため）。 */
	function setAsPlanned(programId: string, value: boolean) {
		const sets = done[programId]?.entry.sets;
		if (!sets) return;
		updateEntry(programId, {
			as_planned: value,
			sets: value ? sets.map(() => ({ value: null })) : sets
		});
	}

	function addSet(programId: string) {
		const sets = done[programId]?.entry.sets;
		if (!sets) return;
		updateEntry(programId, { sets: [...sets, { value: null }] });
	}

	function removeSet(programId: string) {
		const sets = done[programId]?.entry.sets;
		if (!sets) return;
		updateEntry(programId, { sets: sets.slice(0, -1) });
	}

	/** 実績の保存。メニュー側は一切書き換えない。 */
	async function saveActual(programId: string) {
		const record = done[programId];
		if (!record) return;
		savingActual = programId;
		savedActual = '';
		error = '';
		if (designMode) {
			savedActual = programId;
			savingActual = '';
			return;
		}
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
		if (designMode) {
			requested = true;
			requesting = false;
			return;
		}
		const { error: e } = await db().from('regenerate_requests').insert({ target_date: today });
		if (e) error = e.message;
		else requested = true;
		requesting = false;
	}

	/** 生成根拠に入っている readiness。無い日は出さない（無い数字は作らない）。 */
	const readiness = $derived(
		(menu?.source?.readiness as { score?: number } | null | undefined)?.score ?? null
	);

	$effect(() => {
		void load();
		void loadDone();
	});
</script>

<svelte:head><title>今日のトレーニング</title></svelte:head>

<!--
	Hallmark · macrostructure: Stat-Led · theme: Sport（競技）
	一日の量を数字で先に出し、種目はその下に台帳の行として並べる。
	囲い（カード）は使わない。区切りは罫線だけ。
-->
<div class="page">
	{#if loading}
		<p class="muted">読み込み中…</p>
	{:else if loadError}
		<div class="panel">
			<p class="error">{loadError}</p>
			<button onclick={load}>再読み込み</button>
		</div>
	{:else if !menu}
		<div class="empty">
			<p>{today} のメニューはまだ生成されていない。</p>
			<p class="muted">03:00 JST のバッチで生成される。</p>
		</div>
	{:else}
		<header class="board">
			<h1 class="board__date num">{formatDayShort(today)}</h1>
			{#if readiness != null}
				<!-- 無い日は出さない。数字の穴は正直だが、作った数字は嘘になる -->
				<span class="board__rdy lab num">Readiness {readiness}</span>
			{/if}
		</header>
		<p class="board__summary">{menu.menu.summary ?? '（要約なし）'}</p>

		<!-- ラン。Garmin コーチのプランは改変しない。取得したまま表示する -->
		<section class="entry">
			<div class="entry__lab lab">
				{menu.menu.run?.intensity ? `Run — ${menu.menu.run.intensity}` : 'Run'}
			</div>
			{#if menu.menu.rest_day}
				<div class="entry__line">
					<div class="entry__title muted">休養日</div>
				</div>
			{:else if menu.menu.run}
				<div class="entry__line">
					<div class="entry__title">{menu.menu.run.name ?? 'ラン'}</div>
					{#if toMinutes(menu.menu.run.duration_sec) != null}
						<div class="figure num">
							{toMinutes(menu.menu.run.duration_sec)}<span class="figure__unit">min</span>
						</div>
					{/if}
				</div>
			{:else}
				<div class="entry__line"><div class="entry__title muted">なし</div></div>
			{/if}
		</section>

		{#each menu.menu.garmin_strength ?? [] as item, i (i)}
			<section class="entry">
				<div class="entry__lab lab">Strength — Garmin</div>
				<div class="entry__line">
					<div class="entry__title">{item.name ?? '補強'}</div>
					{#if toMinutes(item.duration_sec) != null}
						<div class="figure num">
							{toMinutes(item.duration_sec)}<span class="figure__unit">min</span>
						</div>
					{/if}
				</div>
			</section>
		{/each}

		{#each menu.menu.own_strength ?? [] as item (item.program_id)}
			<section class="entry">
				<div class="entry__lab lab">Skill — Stage {item.stage}</div>
				<div class="entry__line">
					<div>
						<div class="entry__title">{item.program}</div>
						{#if item.label}<div class="entry__sub">{item.label}</div>{/if}
						{#if item.note}<div class="entry__note muted">{item.note}</div>{/if}
					</div>
					{#if item.sets}
						<div class="figure num">{item.sets}<span class="figure__unit">sets</span></div>
					{/if}
				</div>

				<button
					class="do"
					class:button--ink={!done[item.program_id]}
					class:do--done={done[item.program_id]}
					data-state={toggling === item.program_id ? 'loading' : undefined}
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
					<details class="actual">
						<summary class="actual__summary muted">実績 {actualSummary(record.entry)}</summary>

						<!--
							ふだんはメニューどおりに実施して完了を押すだけなので、それを既定にする。
							違うことをしたときだけチェックを外して数値を入れる。
						-->
						<label class="actual__check">
							<input
								type="checkbox"
								checked={isAsPlanned(record.entry)}
								onchange={(e) => setAsPlanned(item.program_id, e.currentTarget.checked)}
							/>
							<span>メニューどおり実施した</span>
						</label>

						<label>
							<span>数え方</span>
							<select
								value={record.entry.unit}
								onchange={(e) =>
									updateEntry(item.program_id, {
										unit: e.currentTarget.value as StrengthEntry['unit']
									})}
							>
								<option value="reps">レップ</option>
								<option value="seconds">秒</option>
							</select>
						</label>

						<div class="actual__sets">
							{#each record.entry.sets as set, i (i)}
								<label>
									<span>{i + 1} セット目（{unitLabel(record.entry)}）</span>
									<input
										type="number"
										min="0"
										value={set.value ?? ''}
										oninput={(e) => setSetValue(item.program_id, i, e.currentTarget.value)}
									/>
								</label>
							{/each}
						</div>

						<div class="actual__actions">
							<button type="button" class="button--quiet" onclick={() => addSet(item.program_id)}>
								セットを足す
							</button>
							<button
								type="button"
								class="button--quiet"
								disabled={record.entry.sets.length === 0}
								onclick={() => removeSet(item.program_id)}
							>
								減らす
							</button>
						</div>

						{#if record.entry.planned_sets}
							<p class="muted">メニューの提示は {record.entry.planned_sets} セット。</p>
						{/if}

						<button
							class="button--primary"
							data-state={savingActual === item.program_id ? 'loading' : undefined}
							disabled={savingActual === item.program_id}
							onclick={() => saveActual(item.program_id)}
						>
							{savingActual === item.program_id ? '保存中…' : '実績を保存'}
						</button>
						{#if savedActual === item.program_id}
							<span class="actual__saved num">保存した</span>
						{/if}
					</details>
				{/if}
			</section>
		{/each}

		<!--
			カレンダーの予定。メニュー生成のルールには使われず、表示専用。
			「今日やることを 1 画面で確認する」ためのもの。
		-->
		{#each menu.menu.schedule ?? [] as event, i (i)}
			<section class="entry entry--quiet">
				<div class="entry__lab lab">Calendar</div>
				<div class="entry__line">
					<div class="entry__title">{event.summary || '(無題)'}</div>
					<div class="figure figure--sm num">{formatEventTime(event.start, event.all_day)}</div>
				</div>
			</section>
		{/each}

		<footer class="foot">
			<p class="muted">生成 {formatDateTime(menu.generated_at)}</p>

			<details>
				<summary class="muted">生成根拠（source）</summary>
				<pre class="foot__pre">{JSON.stringify(menu.source, null, 2)}</pre>
			</details>

			<p class="muted">
				カレンダーの反映が遅れて予定を拾えていない場合は再生成する。
			</p>
			<button
				class="button--quiet"
				data-state={requesting ? 'loading' : undefined}
				onclick={requestRegenerate}
				disabled={requesting || requested}
			>
				{requested ? '再生成をリクエスト済み' : 'メニューを再生成'}
			</button>

			{#if error}<p class="error">{error}</p>{/if}
		</footer>
	{/if}
</div>

<style>
	/* --- 見出し（スコアボード） --------------------------------------------- */
	.board {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		gap: var(--space-sm);
		border-bottom: var(--rule-heavy) solid var(--color-ink);
		padding-bottom: var(--space-2xs);
	}

	.board__date {
		font-size: var(--text-xl);
		margin: 0;
	}

	.board__rdy {
		color: var(--color-accent);
		white-space: nowrap;
	}

	.board__summary {
		margin: var(--space-sm) 0 var(--space-lg);
		font-size: var(--text-base);
		max-width: 40ch;
	}

	/* --- 台帳の行 ------------------------------------------------------------ */
	.entry {
		padding: var(--space-md) 0;
		border-bottom: var(--rule-hair) solid var(--color-rule);
	}

	.entry--quiet .entry__title {
		color: var(--color-muted);
	}

	.entry__lab {
		display: block;
		margin-bottom: var(--space-2xs);
	}

	.entry__line {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		gap: var(--space-sm);
	}

	.entry__title {
		font-size: var(--text-md);
		font-weight: 600;
		line-height: 1.3;
	}

	.entry__sub {
		font-size: var(--text-sm);
		margin-top: var(--space-2xs);
	}

	.entry__note {
		margin-top: var(--space-2xs);
	}

	/* 数字が主役。単位は小さく添えるだけ */
	.figure {
		font-family: var(--font-display);
		font-size: var(--text-2xl);
		font-weight: 700;
		line-height: 1;
		white-space: nowrap;
	}

	.figure--sm {
		font-size: var(--text-md);
	}

	.figure__unit {
		font-size: var(--text-sm);
		font-weight: 400;
		color: var(--color-muted);
		margin-left: 0.15em;
	}

	.do {
		margin-top: var(--space-sm);
	}

	.do--done {
		border-color: var(--color-good);
		color: var(--color-good);
	}

	/* --- 実績 ---------------------------------------------------------------- */
	.actual {
		margin-top: var(--space-sm);
	}

	.actual__summary {
		cursor: pointer;
		min-height: var(--hit);
		display: flex;
		align-items: center;
	}

	.actual__check {
		display: flex;
		align-items: center;
		gap: var(--space-xs);
		margin-top: var(--space-xs);
	}

	.actual__check input {
		width: auto;
	}

	.actual__check span {
		margin: 0;
		color: var(--color-ink);
		font-size: var(--text-base);
	}

	.actual__sets {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(6.5rem, 1fr));
		gap: var(--space-xs);
	}

	.actual__actions {
		display: flex;
		gap: var(--space-xs);
		margin-bottom: var(--space-sm);
	}

	.actual__saved {
		margin-left: var(--space-xs);
		color: var(--color-good);
		font-size: var(--text-sm);
	}

	/* --- 末尾（運用のための領域。主役ではない） ----------------------------- */
	.foot {
		margin-top: var(--space-2xl);
		padding-top: var(--space-md);
		border-top: var(--rule-hair) solid var(--color-rule);
	}

	.foot__pre {
		white-space: pre-wrap;
		font-size: var(--text-xs);
		overflow-x: auto;
	}
</style>
