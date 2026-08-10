import type { Session } from '@supabase/supabase-js';
import { db, isConfigured } from './supabase';

/**
 * ログイン方式は暫定でメール + パスワードにしてある。
 *
 * Supabase ダッシュボードでサインアップを無効化する運用なので、
 * アカウントはダッシュボードから手で 1 つ作る。メール配信に依存しないため
 * 設定が最も少なくて済む。マジックリンクや OAuth に替える場合も
 * 差し替えはこのファイルの signIn() だけで済む。
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

	async signIn(email: string, password: string) {
		const { error } = await db().auth.signInWithPassword({ email, password });
		if (error) throw error;
	}

	async signOut() {
		await db().auth.signOut();
	}
}

export const session = new SessionStore();
