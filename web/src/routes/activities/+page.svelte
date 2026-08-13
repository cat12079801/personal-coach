<script lang="ts">
	import { db } from '$lib/supabase';
	import { designMode } from '$lib/design';
	import { designActivities } from '$lib/fixtures';
	import { formatDateTime, formatDuration, formatPace, toMinutes } from '$lib/format';
	import type { Activity, RunningDetail } from '$lib/types';

	type Row = Activity & { running_details: RunningDetail | null };

	/**
	 * Garmin の typeKey を英字ラベルにするだけ。**和訳しない。**
	 * 生のキーのまま見せる方が Garmin 側と突き合わせやすい（design.md）。
	 */
	const SPORT_LABEL: Record<string, string> = {
		running: 'Run',
		strength_training: 'Strength',
		skating_ws: 'Skate',
		bouldering: 'Boulder'
	};

	function sportLabel(sport: string): string {
		return SPORT_LABEL[sport] ?? sport.replace(/_/g, ' ');
	}

	let rows = $state<Row[]>([]);
	let loading = $state(true);
	let error = $state('');

	async function load() {
		loading = true;
		error = '';
		if (designMode) {
			rows = designActivities;
			loading = false;
			return;
		}
		try {
			const { data, error: e } = await db()
				.from('activities')
				.select('*, running_details(*)')
				.order('started_at', { ascending: false })
				.limit(50);
			if (e) throw new Error(e.message);
			rows = (data ?? []) as Row[];
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		} finally {
			loading = false;
		}
	}

	/** ランは距離、それ以外は時間が主役の数字になる。 */
	function figure(a: Row): { value: string; unit: string } | null {
		const km = a.running_details?.distance_m;
		if (km != null) return { value: (km / 1000).toFixed(1), unit: 'km' };
		const min = toMinutes(a.duration_sec);
		return min == null ? null : { value: String(min), unit: 'min' };
	}

	/**
	 * 数字の脇に添える内訳。無い値は出さない。
	 * 3 つまでに抑える。375px で 4 つ並べると折り返して数字の下へ回り込む。
	 */
	function detail(a: Row): string {
		const isRun = a.running_details?.distance_m != null;
		const parts: string[] = [];
		if (isRun) parts.push(formatDuration(a.duration_sec));
		if (a.running_details?.avg_pace != null) parts.push(formatPace(a.running_details.avg_pace));
		if (a.avg_hr) parts.push(`平均 ${a.avg_hr} bpm`);
		if (!isRun && a.calories) parts.push(`${a.calories} kcal`);
		return parts.join(' ・ ');
	}

	$effect(() => {
		void load();
	});
</script>

<svelte:head><title>アクティビティ</title></svelte:head>

<div class="page">
	<h1>アクティビティ</h1>

	{#if loading}
		<p class="muted">読み込み中…</p>
	{:else if error}
		<div class="panel">
			<p class="error">{error}</p>
			<button onclick={load}>再読み込み</button>
		</div>
	{:else if rows.length === 0}
		<div class="empty">
			<p>まだ取り込まれていない。</p>
			<p class="muted">03:00 JST のバッチが Garmin から取り込む。</p>
		</div>
	{:else}
		{#each rows as a (a.id)}
			{@const fig = figure(a)}
			<section class="entry">
				<div class="entry__lab lab">
					{sportLabel(a.sport)} — <span class="num">{formatDateTime(a.started_at)}</span>
				</div>
				<div class="entry__line">
					<div>
						<div class="entry__sub num">{detail(a)}</div>
						{#if a.running_details && !a.running_details.splits}
							<!-- 2 段目ジョブがまだ拾っていない。取り込みの状態が見えるようにしておく -->
							<div class="entry__note muted">スプリット未取得</div>
						{/if}
					</div>
					{#if fig}
						<div class="figure">{fig.value}<span class="figure__unit">{fig.unit}</span></div>
					{/if}
				</div>
			</section>
		{/each}
	{/if}
</div>
