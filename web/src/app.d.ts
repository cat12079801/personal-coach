/**
 * vite.config.ts の define で埋め込まれる定数。参照は build-info.ts 経由で行う。
 * import / export を書くとモジュール扱いになりグローバル宣言が効かなくなる。
 */
declare const __BUILD_TIME__: string;
declare const __COMMIT_SHA__: string;
declare const __BRANCH__: string;
