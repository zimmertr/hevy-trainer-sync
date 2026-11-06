"""Send a Garmin workout to the watch, the way Garmin Connect's button does,
and list the activities the poller looks through for the watch's recording.

Undocumented connectapi calls that python-garminconnect, garmin_mcp and
gccli all implement. Authenticated with the DI bearer token hevy2garmin holds
(see db.py), sent with the native Android headers garmin-auth sends, because
connectapi answers differently to a bare bearer. No refresh here: the token
belongs to hevy2garmin, and refreshing it from a second process could rotate
its refresh token out from under it. A 401 means "ask hevy2garmin to touch
Garmin, then read the token again".
"""

from .http import request

BASE = "https://connectapi.garmin.com"
HEADERS = {
    "User-Agent": "GCM-Android-5.23",
    "X-Garmin-User-Agent": (
        "com.garmin.android.apps.connectmobile/5.23; ; Google/sdk_gphone64_arm64/google; Android/33; Dalvik/2.1.0"
    ),
    "X-Garmin-Paired-App-Version": "10861",
    "X-Garmin-Client-Platform": "Android",
    "X-App-Ver": "10861",
    "X-Lang": "en",
    "X-GCExperience": "GC5",
    "Accept-Language": "en-US,en;q=0.9",
}


def message(workout_id: str, name: str, device_id: int | str) -> dict:
    """One device message, the shape Garmin Connect posts for Send to Device.

    The endpoint takes a list of these. A bare object gets a 500
    MismatchedInputException back (seen 2026-11-05), so send_workout wraps it.
    """
    return {
        "deviceId": int(device_id),
        "messageUrl": f"workout-service/workout/FIT/{workout_id}",
        "messageType": "workouts",
        "groupName": None,
        "messageName": name,
        "priority": 1,
        "fileType": "FIT",
        "metaDataId": int(workout_id),
    }


class Garmin:
    def __init__(self, di_token: str):
        self._h = {**HEADERS, "Authorization": f"Bearer {di_token}"}

    def last_used_device_id(self) -> int:
        body, _ = request("GET", f"{BASE}/device-service/deviceservice/mylastused", headers=self._h)
        device_id = (body or {}).get("userDeviceId") if isinstance(body, dict) else None
        if not device_id:
            raise RuntimeError(f"Garmin reported no last-used device: {str(body)[:200]}")
        return int(device_id)

    def activities(self, start_date: str, end_date: str) -> list[dict]:
        """Activities Garmin holds between two YYYY-MM-DD dates, the list hevy2garmin's merge searches."""
        body, _ = request("GET", f"{BASE}/activitylist-service/activities/search/activities", headers=self._h,
                          query={"startDate": start_date, "endDate": end_date, "limit": 50, "start": 0})
        return body if isinstance(body, list) else []

    def send_workout(self, workout_id: str, name: str, device_id: int | str) -> None:
        request("POST", f"{BASE}/device-service/devicemessage/messages", headers=self._h,
                body=[message(workout_id, name, device_id)])
