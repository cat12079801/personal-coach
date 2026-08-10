import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
export default {
	preprocess: vitePreprocess(),
	kit: {
		// Cloudflare Pages に静的配信する。API サーバは持たない
		adapter: adapter({ fallback: 'index.html', strict: false }),
		serviceWorker: {
			// static/sw.js を自前で登録する。Kit の自動登録は使わない
			register: false
		}
	}
};
