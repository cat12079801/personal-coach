# 07. 検証済み Garmin API

`garminconnect` 0.3.9 で実際に確認した内容（2026-08-10 時点）。

> **着手時に `demo.py` および README で最新を確認すること。**
> ライブラリのバージョンやメソッド名はこの時点の確認結果でしかない。

## ログイン

```python
from garminconnect import Garmin

client = Garmin(email, password, prompt_mfa=lambda: input("MFA code: "))
client.login("~/.garminconnect")
```

非対話環境で MFA を扱う場合:

```python
client = Garmin(email, password, return_on_mfa=True)
result = client.login()          # client_state を返す
client.resume_login(client_state, mfa_code)
```

ただし GitHub Actions ではコード入力ができないため、実運用では
DB に保存済みのトークンでログインする（[03-constraints.md](03-constraints.md) の 7）。

## 取得系

```
get_activities(start=0, limit=20, activitytype=None)
get_activities_by_date(startdate, enddate=None, activitytype=None, sortorder=None)
get_activity(activity_id)
get_activity_splits(activity_id)
get_activity_typed_splits(activity_id)
get_activity_details(activity_id, maxchart=2000, maxpoly=4000)
get_activity_hr_in_timezones(activity_id)
get_activity_types()
download_activity(activity_id, dl_fmt=Garmin.ActivityDownloadFormat.ORIGINAL)
    # ORIGINAL / TCX / GPX / KML / CSV
```

## トレーニングプラン系（PoC 対象）

```
get_training_plans()
get_training_plan_by_id(...)
get_adaptive_training_plan_by_id(...)
get_scheduled_workouts(year, month)
get_training_status(cdate)
get_training_readiness(cdate)
get_race_predictions(startdate=None, enddate=None, _type=None)
```

## 書き込み系（今回は使わない可能性が高い。参考）

```
create_manual_activity(start_datetime, time_zone, type_key, distance_km, duration_min, activity_name)
create_manual_activity_from_json(payload)
set_activity_exercise_sets(activity_id, payload)   # replace-all セマンティクス
get_activity_exercise_sets(activity_id)
upload_activity(path)   # FIT / GPX / TCX
import_activity(path)   # 同上。ただし Strava 等へ再エクスポートされないインポート扱い
upload_running_workout(workout)
schedule_workout(workout_id, date_str)
```

`set_activity_exercise_sets()` は **replace-all セマンティクス**である点に注意。

## 例外

```
GarminConnectAuthenticationError
GarminConnectConnectionError
GarminConnectTooManyRequestsError
GarminConnectNotFoundError
```

## 取り込み方針

### 差分同期

新しい順に取得し、既知の `activityId` に当たったら打ち切る。

```python
def sync(client, known_ids: set[str]) -> list[dict]:
    fetched, start = [], 0
    while True:
        batch = client.get_activities(start=start, limit=50)
        if not batch:
            break
        for a in batch:
            if str(a["activityId"]) in known_ids:
                return fetched
            fetched.append(a)
        start += 50
```

### そのほか

- ランの splits は「サマリ取り込み後に未取得のものだけ追う」**2 段ジョブ**にする
- `GarminConnectTooManyRequestsError`（429）は必ず握って**指数バックオフ**する。
  初回バックフィルでは自前でスリープを入れる
- ジョブには `timeout-minutes` を必ず設定する
- `if: failure()` で Discord Webhook に通知する（GitHub の失敗メールは見落とすため）
