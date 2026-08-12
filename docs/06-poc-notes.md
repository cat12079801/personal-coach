# 06. 未確定事項 / PoC 記録

**推測で実装しない。** API のレスポンス形状は必ず実データをダンプして確認してから正規化を書く。
確認できた内容はこのファイルに追記していく。

---

## PoC-1: Garmin コーチのプランはどの API から取得できるか

**状態:** ✅ 完了（2026-08-12 実施）
**スクリプト:** `batch/scripts/poc_dump_training_plans.py`

### 結論

```
get_training_plans()                       → 有効なプランの ID を得る
get_adaptive_training_plan_by_id(plan_id)  → 日別ワークアウト（taskList）を得る  ★これが本命
```

`get_training_plan_by_id()` は **使えない**。アダプティブプランに対しては
`400 Not a phased plan.` を返す。フェーズ制の旧プラン用。

`get_scheduled_workouts(year, month)` は月カレンダーのビューで、ほとんどのフィールドが
`None`（`trainingEffectLabel` も `restDay` も無い）。月レンジで引ける利点はあるが、
日次のメニュー生成には情報が足りない。**使わない。**

### プランの特定方法

`get_training_plans()` → `trainingPlanList[]` から選ぶ。

```jsonc
{
  "trainingPlanId": 45225415,
  "trainingPlanCategory": "FBT_ADAPTIVE",              // アダプティブプラン
  "trainingSubType": { "subTypeKey": "GarminRunningCoachEventBased" },
  "trainingStatus":  { "statusKey": "Scheduled" },     // 有効
  "name": "福岡マラソンプラン",
  "startDate": "2026-04-23T00:00:00.0",
  "endDate":   "2026-11-08T00:00:00.0",
  "durationInWeeks": 28,
  "avgWeeklyWorkouts": 6,
  "supplementalSports": ["STRENGTH_TRAINING_BODYWEIGHT"],
  "parentPlanId": 39305042
}
```

`parentPlanId` のほうを引いても中身は薄い。**`trainingPlanCategory == "FBT_ADAPTIVE"` かつ
`trainingStatus.statusKey == "Scheduled"` の `trainingPlanId` を使う。**

### taskList の形状

`get_adaptive_training_plan_by_id(45225415)` の `taskList`。
**当日から 7 日ぶん**が返る（1 日に複数ワークアウトがあるので件数は 9 件だった）。

```jsonc
{
  "calendarDate": "2026-08-12",
  "weekId": 16, "dayOfWeekId": 3, "workoutOrder": 1,
  "priority": 1, "longWkt": false, "grouped": true,
  "taskWorkout": {
    "sportType": { "sportTypeKey": "running" },       // running / strength_training
    "workoutName": "ベース",
    "estimatedDurationInSecs": 3660,
    "trainingEffectLabel": "AEROBIC_BASE",
    "restDay": false,
    "priorityType": "REQUIRED",
    "workoutPhrase": "STRENGTH_PRE_RUN_ACTIVATION_7_1_RUNNING_BODYWEIGHT",
    "workoutUuid": "fcdb7703-...",
    "workoutId": null,
    "adaptiveCoachingWorkoutStatus": "NOT_COMPLETE"
  }
}
```

実際に返ってきた 1 週間（2026-08-12 〜 08-18）:

| date | sportTypeKey | workoutName | 秒 | trainingEffectLabel | restDay |
|---|---|---|---|---|---|
| 08-12 | strength_training | ラン前のアクティベー | 1200 | INVALID | false |
| 08-12 | running | ベース | 3660 | AEROBIC_BASE | false |
| 08-13 | (null) | (null) | (null) | INVALID | **true** |
| 08-14 | running | 無酸素 | 2760 | ANAEROBIC_CAPACITY | false |
| 08-15 | running | ベース | 2340 | AEROBIC_BASE | false |
| 08-15 | strength_training | コアスタビリティ2 | 1500 | INVALID | false |
| 08-16 | running | ベース | 2400 | AEROBIC_BASE | false |
| 08-17 | running | 乳酸閾値 | 2520 | LACTATE_THRESHOLD | false |
| 08-18 | running | ベース | 3660 | AEROBIC_BASE | false |

### 「ポイント練習 / イージー / 休養」の判定

**`trainingEffectLabel` を使う。**

| 値 | 扱い |
|---|---|
| `ANAEROBIC_CAPACITY` | ポイント練習 |
| `LACTATE_THRESHOLD` | ポイント練習 |
| `AEROBIC_BASE` | イージー |
| `INVALID` | 筋トレ（ランではない）。判定に使わない |

休養日は `restDay: true`。このとき `taskWorkout` の中身はほぼ `null` になる。

### フェーズ

`adaptivePlanPhases[]` に `currentPhase: true` が 1 つある。

```
2026-04-23〜05-10 TRANSITION
2026-05-11〜07-12 BASE
2026-07-13〜09-13 BUILD          ← 現在
2026-09-14〜10-25 PEAK
2026-10-26〜11-07 TAPER
2026-11-08        TARGET_EVENT_DAY
```

`daily_menus.source` に残しておくと後から解釈しやすい。

### 取れなかったもの

**ワークアウトのステップ詳細（ウォームアップ / インターバル / クールダウン）は取れない。**
アダプティブプランのワークアウトは `workoutId` が `null` で `workoutUuid` しか無く、
`taskList` にも `scheduled_workouts` にもステップの配列は含まれていない。

→ アプリで表示するのは **種目・ワークアウト名・推定時間・強度ラベル**まで。
実際のインターバル指示はウォッチ側で見る前提とする。

### training_readiness

**戻り値は要素 1 個のリスト**（dict ではない）。

```jsonc
[{
  "calendarDate": "2026-08-12",
  "level": "HIGH",                     // 判定に使う
  "score": 75,                         // 0-100
  "feedbackShort": "WELL_RECOVERED",
  "recoveryTime": 332,                 // 分
  "acuteLoad": 494,
  "hrvWeeklyAverage": 96,
  "sleepScore": 78,
  "validSleep": true
}]
```

ルール 5（readiness が低い日は強度を 1 段下げる）は `level` か `score` で判定する。
閾値は運用しながら決める。初期値は `score < 50` または `level in (LOW, VERY_LOW)` とする。

`validSleep: false` の日は `score` が当てにならないので、その場合は強度を下げない。

### training_status

`trainingStatus` は数値（4）。デバイス ID をキーにした入れ子になっている点に注意。

```
mostRecentTrainingStatus.latestTrainingStatusData.<deviceId>.trainingStatus            = 4
mostRecentTrainingStatus.latestTrainingStatusData.<deviceId>.trainingStatusFeedbackPhrase = MAINTAINING_2
mostRecentTrainingStatus.latestTrainingStatusData.<deviceId>.acuteTrainingLoadDTO.acwrStatus = OPTIMAL
mostRecentVO2Max.generic.vo2MaxValue = 58.0
```

**`<deviceId>` は固定ではない**ので、キーを決め打ちせず dict の最初の値を取るか、
`activities` 側の deviceId と突き合わせる。メニュー生成には必須ではないので、
`daily_menus.source` に丸ごと入れておく程度でよい。

### race_predictions

単純な dict。秒。

```jsonc
{ "calendarDate": "2026-08-12", "time5K": 1178, "time10K": 2513,
  "timeHalfMarathon": 5704, "timeMarathon": 12646 }
```

---

## PoC-2: 種目の `type_key` と主観強度

**状態:** ✅ 完了（2026-08-12 実施）
**スクリプト:** `batch/scripts/poc_dump_activity_types.py`

### `type_key`

直近 30 件の実アクティビティで確認した。

| 種目 | `type_key` | typeId | 確認 |
|---|---|---|---|
| ランニング | `running` | 1 | 実データ 22 件 |
| フィギュアスケート | `skating_ws` | 168 | 実データ 5 件 |
| 筋トレ | `strength_training` | 13 | 実データ 3 件 |
| ボルダリング | `bouldering` | 174 | 実データ 1 件（2026-08-07） |

型一覧には近いものが 4 つある。ウォッチのプロファイル次第で変わりうるので、
正規化側は 4 つすべてを「クライミング系」として扱う（`garmin/sports.py`）。

```
139 rock_climbing     150 floor_climbing
173 indoor_climbing   174 bouldering
```

### 注意: Garmin Connect で手動追加したアクティビティは中身が空

2026-08-07 のボルダリング（手動追加）を確認したところ、以下がすべて `null` だった。

```
averageHR / maxHR            → null（計測していないので当然）
activityTrainingLoad         → null
aerobicTrainingEffect        → null
anaerobicTrainingEffect      → null
trainingEffectLabel          → null
directWorkoutRpe / Feel      → null（未入力）
```

入っていたのは `duration`（3600）と `calories`（500）と `activityName` だけ。

**RPE は自動では入らない。** Garmin Connect 側でアクティビティを編集して
「主観的運動強度」を入れないと `directWorkoutRpe` は `null` のままになる。
負荷判定に RPE を使う設計（OD-4）は、この入力を前提にしている。

正規化は `null` を許容するので取り込み自体は問題なく通る。

### 主観強度（OD-4 の答え）

**`get_activities()`（一覧）には主観系のフィールドが一切無い。**
110 個のキーを見たが `feel` / `rpe` / `effort` は無し。

**`get_activity(activity_id)`（詳細）には入っている。**

```jsonc
{ "summaryDTO": { "directWorkoutFeel": 50, "directWorkoutRpe": 40 } }
```

いずれも 0-100 のスケール。`directWorkoutRpe: 40` は RPE 4/10 に相当する。

→ **詳細を取りに行くのはランのみ**（[OD-4](08-open-decisions.md)）。
ラン splits の 2 段ジョブと同じ枠組みで実装した。

### 種目ごとの使えるフィールド

```
running           : distance, averageHR, maxHR, activityTrainingLoad,
                    aerobicTrainingEffect, anaerobicTrainingEffect,
                    trainingEffectLabel, elevationGain, averageSpeed, lapCount, hasSplits
skating_ws        : distance は 0。averageHR は出るが低めに出る（滑走と休憩の繰り返し）
strength_training : distance は 0。totalSets / totalReps が入る
```

---

## 検討事項: 手動登録した種目を Garmin 側に書き戻すか

**状態:** ⬜ 当面は書き戻さない方針

技術的には `create_manual_activity()` / `set_activity_exercise_sets()` で可能。

しかし Garmin の Training Load 計算に手動アクティビティがどう反映されるかは**仕様非公開**であり、
ランのトレーニングステータス判定が意図せず振れる恐れがある。

再検討するなら、テスト用に 1 件だけ書き戻して Training Status の変化を観測してから判断する。

---

## 検討事項: 非対話環境での MFA

**状態:** ✅ 解消（DB のトークンで運用する）

`bootstrap_garmin_token.py` でトークンを投入済み。以降は DB のトークンだけでログインでき、
リフレッシュ後の値も書き戻される（`Client.dump()`）。

トークンが完全に失効した場合は GitHub Actions では復旧できないので、
Discord 通知を受けてローカルで `bootstrap_garmin_token.py` を再実行する。

### 注意: Garmin のレート制限

初回実行時、モバイル向けログイン経路が **429（IP 単位のレート制限）** で 2 回弾かれてから
別経路で成功した。短時間に `bootstrap` を繰り返さないこと。
