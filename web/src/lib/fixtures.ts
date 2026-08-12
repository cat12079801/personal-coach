/**
 * デザイン検証用のダミーデータ。**`designMode` のときだけ読まれる**（design.ts を参照）。
 *
 * 中身は実データに寄せてある。空配列や 1 件だけの状態だと崩れが見つからないため、
 * 「ラン + Garmin 補強 + 独自筋トレ 2 種目 + 予定 2 件」のような**込み合った日**を基準にする。
 * 実データを見に行かないので Supabase の設定もログインも要らない。
 */
import type { Session } from '@supabase/supabase-js';
import { todayJst } from './format';
import type {
	Activity,
	DailyMenu,
	ManualLog,
	NotificationRow,
	RunningDetail,
	StrengthProgram
} from './types';

const today = todayJst();

/** 当日からの相対日時を ISO で返す。 */
function at(daysAgo: number, hour: number, minute = 0): string {
	const d = new Date(`${today}T00:00:00+09:00`);
	d.setDate(d.getDate() - daysAgo);
	d.setHours(hour, minute, 0, 0);
	return d.toISOString();
}

/**
 * ログイン済みとみなすための偽のセッション。
 * 設定画面がメールアドレスを表示するだけなので、必要な形だけ満たす。
 */
export const designSession = {
	user: { id: 'design-user', email: 'design@example.invalid' }
} as unknown as Session;

export const designMenu: DailyMenu = {
	date: today,
	generated_at: at(0, 3, 0),
	notified_at: at(0, 8, 0),
	menu: {
		summary: 'ベースラン 45 分 + コアスタビリティ2 + プランシェ + 腕立て伏せ',
		rest_day: false,
		run: {
			sport: 'running',
			name: 'ベースラン',
			duration_sec: 2700,
			intensity: 'AEROBIC_BASE',
			rest_day: false
		},
		garmin_strength: [
			{
				sport: 'strength_training',
				name: 'コアスタビリティ2',
				duration_sec: 900,
				intensity: null,
				rest_day: false
			}
		],
		own_strength: [
			{
				program_id: 'design-planche',
				program: 'プランシェ',
				stage: 5,
				label: 'タックプランシェ 15 秒キープ',
				sets: 3,
				note: '肘を伸ばしたまま。10 秒×3 が安定したら次へ'
			},
			{
				program_id: 'design-pushup',
				program: '腕立て伏せ',
				stage: 2,
				label: 'ダイヤモンドプッシュアップ 12 回',
				sets: 3,
				note: null
			}
		],
		schedule: [
			{ summary: 'スケート教室', start: at(0, 19, 30), end: at(0, 21, 0), all_day: false },
			{ summary: '燃えないゴミ', start: at(0, 0, 0), end: null, all_day: true }
		]
	},
	source: {
		plan: { planId: 'design-plan', planName: 'ハーフマラソン 12 週' },
		readiness: { score: 68, level: 'MODERATE', validSleep: true },
		applied_rules: ['R2:normal_day'],
		program_decisions: [
			{ program: 'プランシェ', placed: true, reason: 'planned' },
			{ program: '腕立て伏せ', placed: true, reason: 'planned' },
			{ program: 'シンピ倒立', placed: false, reason: 'min_gap' }
		]
	}
};

type ActivityRow = Activity & { running_details: RunningDetail | null };

export const designActivities: ActivityRow[] = [
	{
		id: 'design-act-1',
		garmin_activity_id: '10000001',
		sport: 'running',
		started_at: at(0, 6, 15),
		duration_sec: 2748,
		avg_hr: 142,
		max_hr: 165,
		calories: 420,
		raw: {},
		running_details: {
			activity_id: 'design-act-1',
			distance_m: 8120,
			avg_pace: 338,
			elev_gain: 62,
			splits: [{}],
			fetched_at: at(0, 7, 0)
		}
	},
	{
		id: 'design-act-2',
		garmin_activity_id: '10000002',
		sport: 'strength_training',
		started_at: at(1, 21, 10),
		duration_sec: 1980,
		avg_hr: 108,
		max_hr: 131,
		calories: 180,
		raw: {},
		running_details: null
	},
	{
		id: 'design-act-3',
		garmin_activity_id: '10000003',
		sport: 'skating_ws',
		started_at: at(2, 19, 40),
		duration_sec: 5400,
		avg_hr: 116,
		max_hr: 158,
		calories: 390,
		raw: {},
		running_details: null
	},
	{
		id: 'design-act-4',
		garmin_activity_id: '10000004',
		sport: 'running',
		started_at: at(3, 6, 5),
		duration_sec: 4210,
		avg_hr: 158,
		max_hr: 179,
		calories: 690,
		raw: {},
		// スプリット未取得の表示を確認するため splits を null にしてある
		running_details: {
			activity_id: 'design-act-4',
			distance_m: 12480,
			avg_pace: 320,
			elev_gain: 88,
			splits: null,
			fetched_at: null
		}
	}
];

export const designUnlinked: Activity[] = [
	designActivities[2] as Activity,
	designActivities[1] as Activity
];

export const designNotifications: NotificationRow[] = [
	{
		id: 'design-noti-1',
		sent_at: at(0, 8, 0),
		title: '今日のトレーニング',
		body: 'ベースラン 45 分 + コアスタビリティ2 + プランシェ + 腕立て伏せ',
		target_date: today,
		read_at: null
	},
	{
		id: 'design-noti-2',
		sent_at: at(1, 8, 0),
		title: '今日のトレーニング',
		body: '無酸素インターバル 40 分',
		target_date: null,
		read_at: at(1, 8, 30)
	}
];

export const designPrograms: StrengthProgram[] = [
	{
		id: 'design-pushup',
		name: '腕立て伏せ',
		stage: 2,
		stages: [
			{ label: 'ノーマルプッシュアップ 15 回', sets: 3, note: null },
			{ label: 'ダイヤモンドプッシュアップ 12 回', sets: 3, note: '15 回×3 で次へ' },
			{ label: 'アーチャープッシュアップ 左右 8 回', sets: 3, note: null },
			{ label: '擬似プランシェプッシュアップ 8 回', sets: 3, note: null }
		],
		weekly_target: 3,
		min_gap_days: 2,
		sort_order: 0,
		active: true
	},
	{
		id: 'design-planche',
		name: 'プランシェ',
		stage: 5,
		stages: [
			{ label: 'プランシェリーン 20 秒キープ', sets: 3, note: null },
			{ label: 'フロッグスタンド 30 秒キープ', sets: 3, note: null },
			{ label: 'ストレートアームフロッグスタンド 20 秒キープ', sets: 3, note: null },
			{ label: 'ベンチタックプランシェ 15 秒キープ', sets: 3, note: null },
			{ label: 'タックプランシェ 15 秒キープ', sets: 3, note: '肘を伸ばしたまま' },
			{ label: 'アドバンストタックプランシェ 12 秒キープ', sets: 3, note: null },
			{ label: 'ストラドルプランシェ 8 秒キープ', sets: 3, note: null },
			{ label: 'フルプランシェ 5 秒キープ', sets: 3, note: null }
		],
		weekly_target: 3,
		min_gap_days: 2,
		sort_order: 1,
		active: true
	},
	{
		id: 'design-hspu',
		name: 'シンピ倒立',
		stage: 1,
		stages: [
			{ label: '壁倒立キープ 60 秒', sets: 3, note: '腹側を壁へ' },
			{ label: '自立倒立キープ 30 秒', sets: 3, note: null },
			{ label: 'タックプレス 5 回', sets: 3, note: null },
			{ label: 'ストラドルプレス 5 回', sets: 3, note: null },
			{ label: '伸腕伸身プレス 3 回', sets: 3, note: null }
		],
		weekly_target: 3,
		min_gap_days: 2,
		sort_order: 2,
		active: false
	}
];

/** 今日のメニューの完了記録。1 件だけ完了済みにして両方の見た目を出す。 */
export const designCompletions = [
	{
		id: 'design-log-1',
		program_id: 'design-pushup',
		menu_date: today,
		exercises: [
			{
				name: 'ダイヤモンドプッシュアップ 12 回',
				stage: 2,
				unit: 'reps' as const,
				planned_sets: 3,
				sets: [{ value: 12 }, { value: 11 }, { value: 8 }]
			}
		]
	}
];

export const designStrengthLogs: ManualLog[] = [
	{
		id: 'design-log-1',
		activity_id: null,
		rpe: null,
		note: null,
		created_at: at(0, 21, 30),
		performed_at: at(0, 21, 30),
		exercises: designCompletions[0].exercises
	},
	{
		id: 'design-log-2',
		activity_id: 'design-act-2',
		rpe: 7,
		note: 'ベンチは 3 セット目で潰れた',
		created_at: at(1, 22, 0),
		performed_at: at(1, 21, 10),
		exercises: [
			{ name: 'ベンチプレス', sets: [{ reps: 8, weight_kg: 70 }, { reps: 6, weight_kg: 70 }] },
			{ name: '懸垂', sets: [{ reps: 10 }, { reps: 8 }] }
		]
	}
];

export const designSkatingLogs: ManualLog[] = [
	{
		id: 'design-log-3',
		activity_id: 'design-act-3',
		rpe: 6,
		note: null,
		created_at: at(2, 22, 15),
		practiced_at: at(2, 19, 40),
		elements: [{ name: 'シングルアクセル', attempts: 12, success: 5 }]
	}
];
