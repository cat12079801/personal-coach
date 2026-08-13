<script lang="ts">
	/**
	 * 下部ナビの図。**外部のアイコン集は入れない。**
	 * 5 つを同じ骨格で手で引く（24 グリッド・線幅 1.75・角は留める）。
	 * 複数のライブラリを混ぜると線の声が混ざる（design.md「やらないこと」）。
	 */
	type Props = { name: 'today' | 'activities' | 'logs' | 'notifications' | 'settings' };
	let { name }: Props = $props();
</script>

<svg
	viewBox="0 0 24 24"
	fill="none"
	stroke="currentColor"
	stroke-width="1.75"
	stroke-linecap="square"
	stroke-linejoin="miter"
	aria-hidden="true"
>
	{#if name === 'today'}
		<!-- 今日: 見出しの罫線が引かれた一枚 -->
		<rect x="3.5" y="4.5" width="17" height="15" />
		<path d="M3.5 9.5h17" />
		<path d="M7.5 13.5h6" />
	{:else if name === 'activities'}
		<!-- 記録: 棒の並び -->
		<path d="M5.5 19.5v-5" />
		<path d="M12 19.5V6.5" />
		<path d="M18.5 19.5v-8" />
	{:else if name === 'logs'}
		<!-- 手動登録: 枠に足す -->
		<rect x="3.5" y="3.5" width="17" height="17" />
		<path d="M12 8v8" />
		<path d="M8 12h8" />
	{:else if name === 'notifications'}
		<!-- 通知: 鐘 -->
		<path d="M6.5 17.5h11l-2-2.5v-4a3.5 3.5 0 0 0-7 0v4z" />
		<path d="M10.5 20h3" />
	{:else}
		<!-- 設定: つまみ -->
		<path d="M4 9h16" />
		<path d="M4 15h16" />
		<rect x="8" y="6.75" width="4.5" height="4.5" />
		<rect x="13" y="12.75" width="4.5" height="4.5" />
	{/if}
</svg>
