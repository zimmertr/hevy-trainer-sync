"""Start a run of a CronJob from inside the cluster, the way `kubectl create job --from=cronjob/NAME` does.

The poller uses it to run the hourly mirror as soon as a workout is saved, so
the weights and the next workout reach the calendar within minutes instead of
at the next hour. It authenticates as the pod's service account, which may
only read that CronJob and create Jobs in its namespace. Decision record 0041.
"""

import ssl

from .http import request

SA_DIR = "/var/run/secrets/kubernetes.io/serviceaccount"
API = "https://kubernetes.default.svc"


def _read(path: str) -> str:
    with open(path) as f:
        return f.read().strip()


def job_from(cronjob: dict) -> dict:
    """A Job from a CronJob's template, owned by it as kubectl's are, so the CronJob's history limit cleans it up."""
    meta = cronjob["metadata"]
    return {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {
            "generateName": f"{meta['name']}-save-",
            "annotations": {"cronjob.kubernetes.io/instantiate": "manual"},
            "labels": dict((cronjob["spec"]["jobTemplate"].get("metadata") or {}).get("labels") or {}),
            "ownerReferences": [{
                "apiVersion": "batch/v1",
                "kind": "CronJob",
                "name": meta["name"],
                "uid": meta["uid"],
                "controller": True,
                "blockOwnerDeletion": True,
            }],
        },
        "spec": cronjob["spec"]["jobTemplate"]["spec"],
    }


def run_cronjob(name: str, *, sa_dir: str = SA_DIR, api: str = API) -> str:
    """Create one Job from CronJob `name` in the pod's own namespace. Returns the Job's name."""
    ns = _read(f"{sa_dir}/namespace")
    headers = {"Authorization": f"Bearer {_read(f'{sa_dir}/token')}"}
    ctx = ssl.create_default_context(cafile=f"{sa_dir}/ca.crt")
    base = f"{api}/apis/batch/v1/namespaces/{ns}"
    cronjob, _ = request("GET", f"{base}/cronjobs/{name}", headers=headers, context=ctx)
    job, _ = request("POST", f"{base}/jobs", headers=headers, body=job_from(cronjob), context=ctx)
    return str((job or {}).get("metadata", {}).get("name") or "")
