import { createClient } from '@supabase/supabase-js';

const url = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const publishableKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY as string | undefined;

/**
 * publishable key（sb_publishable_...）はフロントに埋め込まれる公開値。これ自体は秘密ではない。
 * Postgres の anon / authenticated ロールで動くので RLS が効く。
 * データを守っているのは RLS（coach.is_owner()）だけである。
 * 詳細は docs/04-data-model.md の「RLS 方針」を参照。
 */
export const isConfigured = Boolean(url && publishableKey);

/**
 * 無料プランのプロジェクト数上限のため既存プロジェクトに相乗りしている。
 * 相手の public スキーマと混ざらないよう、専用スキーマを明示する。
 * これを忘れると相手のスキーマを見に行って 404 になる。
 * 詳細は docs/adr/0006-share-existing-supabase-project.md。
 */
const SCHEMA = 'coach';

function makeClient() {
	return createClient(url!, publishableKey!, {
		db: { schema: SCHEMA },
		auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true }
	});
}

export type CoachClient = ReturnType<typeof makeClient>;

export const supabase: CoachClient | null = isConfigured ? makeClient() : null;

/** 設定済みであることを前提に client を取り出す。未設定なら呼び出し側のバグ。 */
export function db(): CoachClient {
	if (!supabase)
		throw new Error('Supabase が未設定である（VITE_SUPABASE_URL / VITE_SUPABASE_PUBLISHABLE_KEY）');
	return supabase;
}
