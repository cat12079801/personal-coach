import { execSync } from 'node:child_process';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

/**
 * ビルド時のコミットを埋め込む。実機で「今見ているのがどのデプロイか」を判別するため。
 * Cloudflare Pages は CF_PAGES_COMMIT_SHA を渡してくる。ローカルは git から取る。
 */
function commitSha(): string {
	const fromPages = process.env.CF_PAGES_COMMIT_SHA;
	if (fromPages) return fromPages.slice(0, 7);
	try {
		return execSync('git rev-parse --short=7 HEAD', { encoding: 'utf8' }).trim();
	} catch {
		// 浅い clone や git の無い環境でもビルドは通す
		return 'unknown';
	}
}

export default defineConfig({
	plugins: [sveltekit()],
	define: {
		__BUILD_TIME__: JSON.stringify(new Date().toISOString()),
		__COMMIT_SHA__: JSON.stringify(commitSha()),
		__BRANCH__: JSON.stringify(process.env.CF_PAGES_BRANCH ?? 'local')
	}
});
