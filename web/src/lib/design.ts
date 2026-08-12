/**
 * デザイン検証用のモード。**ローカルの dev server でしか有効にならない。**
 *
 * ログインを偽装して素通しするのではなく、**DB を触らずフィクスチャを描く**モードである。
 * データを守っているのは Supabase の RLS だけなので（[04-data-model.md] の RLS 方針）、
 * そこには一切手を触れない。UI のゲートだけ外しても `anon` にはテーブルの GRANT が無く、
 * 1 行も読めない空の画面しか見られない。デザインの検討にはフィクスチャが要る。
 *
 * 二重ガード:
 *
 *  - `dev` … `vite build` で `false` に静的置換されるため、本番バンドルからは分岐ごと消える
 *  - `VITE_DESIGN_MODE=1` … `web/.env.local` にだけ書く。本番（Cloudflare Pages）の
 *    ビルド環境変数には**入れない**
 *
 * したがって本番で有効化する経路は無い。secret key をフロントに置く、RLS を緩める、
 * といった方向には決して倒さないこと。
 */
import { dev } from '$app/environment';

export const designMode = dev && (import.meta.env.VITE_DESIGN_MODE as string | undefined) === '1';
