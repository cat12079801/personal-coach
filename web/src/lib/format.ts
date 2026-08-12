/** 表示は常に JST で行う。バッチの 03:00 / 08:00 も JST 基準である。 */

const JST = 'Asia/Tokyo';

export function todayJst(): string {
	// en-CA は YYYY-MM-DD を返す
	return new Intl.DateTimeFormat('en-CA', { timeZone: JST }).format(new Date());
}

export function formatDate(iso: string): string {
	return new Intl.DateTimeFormat('ja-JP', {
		timeZone: JST,
		month: 'numeric',
		day: 'numeric',
		weekday: 'short'
	}).format(new Date(iso));
}

export function formatDateTime(iso: string): string {
	return new Intl.DateTimeFormat('ja-JP', {
		timeZone: JST,
		month: 'numeric',
		day: 'numeric',
		hour: '2-digit',
		minute: '2-digit'
	}).format(new Date(iso));
}

export function formatDuration(sec: number | null): string {
	if (sec == null) return '—';
	const h = Math.floor(sec / 3600);
	const m = Math.floor((sec % 3600) / 60);
	return h > 0 ? `${h}:${String(m).padStart(2, '0')}` : `${m} 分`;
}

export function formatDistance(meters: number | null): string {
	if (meters == null) return '—';
	return `${(meters / 1000).toFixed(2)} km`;
}

/** avg_pace は sec/km。 */
export function formatPace(secPerKm: number | null): string {
	if (secPerKm == null) return '—';
	const m = Math.floor(secPerKm / 60);
	const s = Math.round(secPerKm % 60);
	return `${m}'${String(s).padStart(2, '0')}"/km`;
}

/** カレンダーの予定の時刻表示。終日予定は時刻を出さない。 */
export function formatEventTime(start: string, allDay: boolean): string {
	if (allDay) return '終日';
	return new Intl.DateTimeFormat('ja-JP', {
		timeZone: JST,
		hour: '2-digit',
		minute: '2-digit'
	}).format(new Date(start));
}

/** datetime-local の値を ISO に直す。ブラウザのローカル時刻として解釈される。 */
export function localInputToIso(value: string): string {
	return new Date(value).toISOString();
}

export function nowForInput(): string {
	const now = new Date();
	const offset = now.getTimezoneOffset() * 60_000;
	return new Date(now.getTime() - offset).toISOString().slice(0, 16);
}
