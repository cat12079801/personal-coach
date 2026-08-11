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
		run?: Record<string, unknown>;
		strength?: unknown[];
		[key: string]: unknown;
	};
	notified_at: string | null;
};

export type NotificationRow = {
	id: string;
	sent_at: string;
	title: string;
	body: string;
	target_date: string | null;
	read_at: string | null;
};

export type LogKind = 'strength' | 'skating';

/** 種目ごとにテーブル名・日時カラム・詳細カラムが違うのでまとめて持つ。 */
export const LOG_TABLES: Record<LogKind, { table: string; at: string; detail: string; label: string }> = {
	strength: { table: 'strength_logs', at: 'performed_at', detail: 'exercises', label: '筋トレ' },
	skating: { table: 'skating_logs', at: 'practiced_at', detail: 'elements', label: 'スケート' }
};

export type ManualLog = {
	id: string;
	activity_id: string | null;
	rpe: number | null;
	note: string | null;
	created_at: string;
	[key: string]: unknown;
};
