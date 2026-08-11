import type { Session } from '@supabase/supabase-js';
import { db, isConfigured } from './supabase';

/**
 * ログインは Google OAuth のみ。
 *
 * 相乗り先の count-upper が Google SSO を使っており、対象アカウント（auth.users の行）は
 * Google の identity に紐づくだけでパスワードを持たない。したがってメール + パスワードは
 * そもそも成立しない。Google provider はプロジェクト側で既に有効になっている。
 *
 * count-upper は Next.js のサーバルート（/auth/callback）で認可コードを交換しているが、
 * こちらは静的配信の SPA でサーバを持たない。supabase-js の detectSessionInUrl に任せ、
 * リダイレクトで戻ってきた URL の code をブラウザ側（PKCE）で交換する。
 */
class SessionStore {
	session = $state<Session | null>(null);
	loading = $state(true);

	async init() {
		if (!isConfigured) {
			this.loading = false;
			return;
		}
		const { data } = await db().auth.getSession();
		this.session = data.session;
		this.loading = false;
		db().auth.onAuthStateChange((_event, session) => {
			this.session = session;
		});
	}

	async signInWithGoogle() {
		const { error } = await db().auth.signInWithOAuth({
			provider: 'google',
			// 戻り先はダッシュボードの Authentication > URL Configuration で
			// 許可しておく必要がある（未許可だと Site URL に飛ばされる）
			options: { redirectTo: `${window.location.origin}/` }
		});
		if (error) throw error;
	}

	async signOut() {
		await db().auth.signOut();
	}
}

export const session = new SessionStore();
