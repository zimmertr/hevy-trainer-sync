# 0009. This job sends each new Garmin workout to the watch, using hevy2garmin's Garmin session

- Status: Accepted. Send to Device turned off by 0040
- Date: 2026-11-04 (conversation); shipped in #17 and #20, merged 2026-11-05
- Decider: TJ ("I'd rather do everything on our side for now")
- Issues and PRs: #7, #13, #17, #20, KM#1822
- Cited in code as: none
- Guide: [`CLAUDE.md`](../../CLAUDE.md), Rules, the Garmin bullet

## Context

hevy2garmin deletes and recreates the Garmin workout whenever a routine changes. The new workout is not on the watch until Send to Device is pressed in Garmin Connect, and with no calendar ([0008](0008-no-calendar-scheduling.md)) nothing else puts it there.

## Decision

After the dashboard sync, the job reads each routine's `garmin_workout_id` from hevy2garmin's `synced_routines` and the `di_token` from `platform_credentials`, read-only. It looks up the last-used device, or uses `GARMIN_DEVICE_ID`, and posts a one-item list to `POST /device-service/devicemessage/messages`. It never refreshes the Garmin token itself: on a 401 it asks the dashboard to sync nothing, which makes hevy2garmin refresh and store the token, then reads it again.

## Evidence

- 2026-11-05: posting a single object got `500 MismatchedInputException`. A one-item list with `groupName` and `metaDataId` succeeded for both routines to device 3611918207 (#20).

## Alternatives rejected

- Upstream in hevy2garmin: right in the long run, deferred by [0015](0015-nothing-upstream-yet.md).
- The calendar: see [0008](0008-no-calendar-scheduling.md).
- A second Garmin login from this job: Garmin would see two clients, and the job would own another credential.

## Consequences

The job depends on hevy2garmin's table names and token shape (#13). The device-message endpoint is undocumented. If Garmin changes it, the watch goes back to needing the button and nothing else breaks. `test_garmin.py` pins the payload shape.
