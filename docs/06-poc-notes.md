# 06. 未確定事項 / PoC 記録

**推測で実装しない。** API のレスポンス形状は必ず実データをダンプして確認してから正規化を書く。
確認できた内容はこのファイルに追記していく。

---

## PoC-1: Garmin コーチのプランはどの API から取得できるか

**状態:** ⬜ 未実施
**優先度:** 最高（この結果でメニュー生成ロジックの入力が決まる）

### やること

`batch/scripts/poc_dump_training_plans.py` を実行し、以下の生 JSON をダンプして目視で確認する。

```
get_training_plans()
get_training_plan_by_id(...)
get_adaptive_training_plan_by_id(...)
get_scheduled_workouts(year, month)
get_training_status(cdate)
get_training_readiness(cdate)
```

### 確認したいこと

- [ ] Garmin コーチ（アダプティブプラン）の当日ワークアウトはどれで取れるか
- [ ] ワークアウトの構造（ウォームアップ / インターバル / クールダウンの表現）
- [ ] 「ポイント練習 / イージー / 休養」を判定できるフィールドはどれか
- [ ] `training_readiness` のスコア範囲と、「低い」と判定する閾値
- [ ] 当日分は前日 03:00 の時点で確定しているか（プランが当日朝に変わらないか）

### 結果

> _（未記入）ダンプ結果の要点と、採用するフィールドをここに書く。_
> _生 JSON は `batch/.poc-out/`（gitignore 済み）に出力される。個人データなのでコミットしない。_

---

## PoC-2: ボルダリング / フィギュアスケートの `type_key`

**状態:** ⬜ 未実施

`batch/scripts/poc_dump_activity_types.py` を実行し、`get_activity_types()` の結果から
該当する `type_key` を特定する。**機種と設定に依存する**ので実機で確認する。

### 結果

| 種目 | `type_key` | 備考 |
|---|---|---|
| ランニング | _（未記入）_ | |
| フィギュアスケート | _（未記入）_ | |
| ボルダリング | _（未記入）_ | Garmin で計測するかどうかも含めて要判断 |

---

## 検討事項: 手動登録した種目を Garmin 側に書き戻すか

**状態:** ⬜ 当面は書き戻さない方針

技術的には `create_manual_activity()` / `set_activity_exercise_sets()` で可能。

しかし Garmin の Training Load 計算に手動アクティビティがどう反映されるかは**仕様非公開**であり、
ランのトレーニングステータス判定が意図せず振れる恐れがある。

再検討するなら、テスト用に 1 件だけ書き戻して Training Status の変化を観測してから判断する。

---

## 検討事項: 非対話環境での MFA

**状態:** 🚧 設計済み・未検証

DB のトークンが有効な限り MFA は要求されない。トークンが完全に失効した場合、
GitHub Actions では MFA コードを入力できないためバッチが落ちる。

- 失敗時は Discord に通知が飛ぶ → ローカルで `bootstrap_garmin_token.py` を再実行して復旧する
- これを許容する（自動復旧は作らない）

`Garmin(..., return_on_mfa=True)` → `login()` が client_state を返す →
`resume_login(client_state, mfa_code)` という非対話フローは存在するが、
結局どこかで人間がコードを入力する必要があるため、GitHub Actions 上では使えない。
