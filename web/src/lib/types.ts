/** supabase/migrations/ のスキーマに対応する型。 */

export type Activity = {
	id: string;
	garmin_activity_id: string;
	sport: string;
	started_at: string;
	duration_sec: number | null;
	avg_hr: number | null;
	max_hr: number | null;
	calories: number | null;
	raw: unknown;
};

export type RunningDetail = {
	activity_id: string;
	distance_m: number | null;
	avg_pace: number | null;
	elev_gain: number | null;
	splits: unknown | null;
	fetched_at: string | null;
};

export type DailyMenu = {
	date: string;
	generated_at: string;
	source: Record<string, unknown>;
	menu: {
		summary?: string;
		rest_day?: boolean;
		run?: PlanTask | null;
		garmin_strength?: PlanTask[];
		own_strength?: OwnStrength[];
		/** カレンダーの予定。表示専用でメニュー生成のルールには使われない */
		schedule?: CalendarEvent[];
		[key: string]: unknown;
	};
	notified_at: string | null;
};

export type PlanTask = {
	sport: string | null;
	name: string | null;
	duration_sec: number | null;
	intensity: string | null;
	rest_day: boolean;
};

export type OwnStrength = {
	program_id: string;
	program: string;
	stage: number;
	label: string | null;
	sets: number | null;
	note: string | null;
};

export type CalendarEvent = {
	summary: string;
	start: string;
	end: string | null;
	all_day: boolean;
};

/** 独自に足す筋トレのプログラム。段階の中身は本人が定義する（docs/08-open-decisions.md の OD-5）。 */
export type Stage = {
	label: string;
	sets: number | null;
	note: string | null;
};

export type StrengthProgram = {
	id: string;
	name: string;
	/** stages の添字（1 始まり）。手動で上げ下げする */
	stage: number;
	stages: Stage[];
	weekly_target: number;
	/** 前回実施日との日数差の下限。2 なら「中 1 日以上」 */
	min_gap_days: number;
	sort_order: number;
	active: boolean;
};

export type NotificationRow = {
	id: string;
	sent_at: string;
	title: string;
	body: string;
	target_date: string | null;
	read_at: string | null;
};

/**
 * 手動登録は筋トレだけ。
 *
 * スケートは運動時間と消費カロリーが分かれば十分で、要素やトライ数は書かない。
 * ランのウォッチ忘れは Garmin Connect 側で手動記録する。したがってアプリ側で
 * 欠測を埋める仕組みは持たない（migration 0008 で skating_logs ごと落とした）。
 */
export const STRENGTH_LOG = {
	table: 'strength_logs',
	at: 'performed_at',
	detail: 'exercises',
	label: '筋トレ'
} as const;

export type ManualLog = {
	id: string;
	activity_id: string | null;
	rpe: number | null;
	note: string | null;
	created_at: string;
	[key: string]: unknown;
};

/**
 * メニューから「完了」にした独自筋トレ。
 * strength_logs に program_id / menu_date 付きで入る（migration 0007）。
 */
export type StrengthCompletion = {
	id: string;
	program_id: string;
	menu_date: string;
	exercises: StrengthEntry[] | null;
};

/** 実績 1 セット。`value` の意味は `StrengthEntry.unit` が決める。 */
export type StrengthSet = {
	/** レップ数または秒数。未記入は null */
	value: number | null;
};

/**
 * `strength_logs.exercises` の 1 要素。
 *
 * **メニューが提示した内容（`planned_sets`）と実績（`sets`）を分けて持つ。**
 * 完了を押した時点ではメニューのセット数ぶんの空枠が入るだけで、実際のレップ数・
 * セット数はメニューと独立に後から編集する。段階を上げる判断は自分で行うため
 * （OD-5）、実績がメニューと食い違っていても生成側は何も見ない。
 */
export type StrengthEntry = {
	name: string;
	stage?: number;
	/** キープ系（プランシェ・倒立）は秒で数える。UI で切り替えられる */
	unit: 'reps' | 'seconds';
	/** メニューが提示したセット数。実績を変えてもこれは書き換えない */
	planned_sets: number | null;
	/**
	 * メニューの提示どおりに実施したか。完了を押した時点では true。
	 * 数値を 1 つでも入れると false になり、`sets` が実績の正となる。
	 *
	 * 省略されている行（この項目を足す前に記録したもの）は true として扱う。
	 * 「完了を押したがメニューと違うことをした」場合だけ明示的に false が入る。
	 */
	as_planned?: boolean;
	sets: StrengthSet[];
};

/** `as_planned` は省略を true とみなす。 */
export function isAsPlanned(entry: StrengthEntry): boolean {
	return entry.as_planned ?? true;
}
