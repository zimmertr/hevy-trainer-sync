# 0020. Strava keeps what the watch recorded, so the watch's own recording has to be right, and this tool never uploads to Strava

- Status: Accepted. Supersedes 0016
- Date: 2026-11-05
- Decider: TJ ("I don't really want to ever do this. I use my garmin for a lot more than strength, including runs and whatnot and that's out of the purview of hevy and this tool", and on making the first post right: "Yes, this is the goal")
- Issues and PRs: #12, #25, #26, #27
- Cited in code as: none
- Guide: [`CLAUDE.md`](../../CLAUDE.md), How it fits together, the Strava bullet

## Context

[0016](0016-garmin-keeps-posting-to-strava.md) assumed that hevy2garmin's merged sets reach the Strava activity after Garmin first forwards it, so the gap was only a matter of minutes. That was wrong. Strava never changes after Garmin's first post, so a merge in Garmin cannot fix Strava, however fast it runs.

## Decision

Garmin's own Strava connection stays on, and this tool never uploads to Strava, now or later. Strava's accuracy comes only from what the watch records. The planned workout on the watch must therefore carry the right exercises, sets, rep targets and weights, so that following it records the session correctly. hevy2garmin's merge corrects Garmin Connect, and only Garmin Connect.

## Evidence

- 2026-11-05, the 3 Nov Lower in Garmin Connect: 24 sets with Hevy's names, reps and weights (Goblet Squat 6, 4, 4, 4, 4 at 30, 50 and 80 lb, and so on), merged by hevy2garmin on 4 Nov, with Training Effect (1.6 aerobic, 0.4 anaerobic) and Body Battery (-12) kept. The merge works.
- The same session on Strava (20850643084): names change from set to set within one exercise (Goblet Squat reads Unknown, Squat, Squat, Unknown, Squat), and the reps are not Hevy's (6, 6, 6, 6, 6). That is the watch's own exercise detection.
- Strava's weights read 24.9, 45.1 and 80.1 lb. A FIT file stores weight in sixteenths of a kilogram, so 25, 45 and 80 lb entered on the watch come back as exactly those values. They were the watch's weights, not Hevy's. The earlier reading of them as merged weights (records 0001 and 0016) was wrong.

## Alternatives rejected

- Upload the merged activity to Strava from this tool, with Garmin's Strava link off: Garmin carries runs and everything else, which are outside this tool. TJ: never.
- Delete and re-upload on Strava: Strava's API has no delete.
- Rely on the merge reaching Strava, as 0016 did: it never does.

## Consequences

- Pre-filled weights stop being a convenience. A blank weight on the watch is a wrong weight on Strava (#12, now P1).
- Exercise mapping has to be right when the routine becomes a Garmin workout, because that is where Strava's names come from (#25).
- Anything done differently from the plan during a session reaches Strava only if it is entered on the watch.
- Not yet known: whether the watch records the planned rep target or its own rep count when a set is not edited. #27's first session answers it.
- The poller ([0019](0019-poll-hevy-every-minute.md)) makes Garmin Connect right within minutes. It does nothing for Strava.
