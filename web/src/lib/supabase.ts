import { createClient, type SupabaseClient } from '@supabase/supabase-js';

const url = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;

/**
 * anon キーはフロントに埋め込まれる公開値。これ自体は秘密ではない。
 * データを守っているのは Supabase 側の RLS（is_owner()）だけである。
 * 詳細は docs/04-data-model.md の「RLS 方針」を参照。
 */
export const isConfigured = Boolean(url && anonKey);

export const supabase: SupabaseClient | null = isConfigured
	? createClient(url!, anonKey!, {
			auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true }
		})
	: null;

/** 設定済みであることを前提に client を取り出す。未設定なら呼び出し側のバグ。 */
export function db(): SupabaseClient {
	if (!supabase) throw new Error('Supabase が未設定である（VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY）');
	return supabase;
}
