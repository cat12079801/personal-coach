/**
 * 実機で「今開いているのがどのデプロイか」を確かめるための情報。
 * 値はビルド時に vite の define で差し込まれる（[vite.config.ts](../../vite.config.ts)）。
 */

const JST = 'Asia/Tokyo';

export const buildInfo = {
	/** 短縮コミットハッシュ。取得できなかった場合は 'unknown' */
	commit: __COMMIT_SHA__,
	/** Cloudflare Pages のビルドブランチ。ローカルビルドは 'local' */
	branch: __BRANCH__,
	/** ビルド時刻の ISO 文字列（UTC） */
	builtAt: __BUILD_TIME__
};

/** ビルド時刻を JST の秒まで出す。デプロイの前後を判別できる粒度が要る。 */
export function formatBuiltAt(iso: string = buildInfo.builtAt): string {
	const d = new Date(iso);
	if (Number.isNaN(d.getTime())) return iso;
	return new Intl.DateTimeFormat('ja-JP', {
		timeZone: JST,
		year: 'numeric',
		month: '2-digit',
		day: '2-digit',
		hour: '2-digit',
		minute: '2-digit',
		second: '2-digit'
	}).format(d);
}

/** 1 行で出す短い表記。未ログイン画面のフッタなどで使う。 */
export function buildInfoLine(): string {
	return `${buildInfo.commit} / ${formatBuiltAt()}`;
}
