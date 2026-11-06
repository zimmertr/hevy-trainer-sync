import os
import tempfile
import unittest
from unittest import mock

from hevy_trainer_sync import kube

CRONJOB = {
    "metadata": {"name": "hevy-trainer-sync", "uid": "uid-1", "namespace": "ns"},
    "spec": {"jobTemplate": {"spec": {"backoffLimit": 0, "template": {"spec": {"containers": []}}}}},
}


class JobFromTest(unittest.TestCase):
    def test_matches_what_kubectl_create_job_from_makes(self):
        job = kube.job_from(CRONJOB)
        self.assertEqual(job["metadata"]["generateName"], "hevy-trainer-sync-save-")
        self.assertEqual(job["metadata"]["annotations"], {"cronjob.kubernetes.io/instantiate": "manual"})
        self.assertEqual(job["metadata"]["labels"], {})
        self.assertEqual(job["metadata"]["ownerReferences"], [{
            "apiVersion": "batch/v1", "kind": "CronJob", "name": "hevy-trainer-sync", "uid": "uid-1",
            "controller": True, "blockOwnerDeletion": True,
        }])
        self.assertIs(job["spec"], CRONJOB["spec"]["jobTemplate"]["spec"])

    def test_template_labels_are_carried(self):
        cj = {**CRONJOB, "spec": {"jobTemplate": {"metadata": {"labels": {"app": "x"}}, "spec": {}}}}
        self.assertEqual(kube.job_from(cj)["metadata"]["labels"], {"app": "x"})


class RunCronjobTest(unittest.TestCase):
    def test_reads_the_cronjob_and_creates_a_job_as_the_service_account(self):
        with tempfile.TemporaryDirectory() as sa:
            for name, text in (("namespace", "hevy2garmin-system\n"), ("token", "tok\n"), ("ca.crt", "")):
                with open(os.path.join(sa, name), "w") as f:
                    f.write(text)
            with mock.patch.object(kube.ssl, "create_default_context") as ctx, \
                    mock.patch.object(kube, "request", side_effect=[
                        (CRONJOB, {}), ({"metadata": {"name": "hevy-trainer-sync-save-abc"}}, {})]) as request:
                name = kube.run_cronjob("hevy-trainer-sync", sa_dir=sa, api="https://k")
        self.assertEqual(name, "hevy-trainer-sync-save-abc")
        ctx.assert_called_once_with(cafile=os.path.join(sa, "ca.crt"))
        get, post = request.call_args_list
        base = "https://k/apis/batch/v1/namespaces/hevy2garmin-system"
        self.assertEqual(get.args, ("GET", f"{base}/cronjobs/hevy-trainer-sync"))
        self.assertEqual(get.kwargs["headers"], {"Authorization": "Bearer tok"})
        self.assertIs(get.kwargs["context"], ctx.return_value)
        self.assertEqual(post.args, ("POST", f"{base}/jobs"))
        self.assertEqual(post.kwargs["body"], kube.job_from(CRONJOB))

    def test_an_answer_without_a_name_is_empty(self):
        with tempfile.TemporaryDirectory() as sa:
            for name in ("namespace", "token", "ca.crt"):
                with open(os.path.join(sa, name), "w") as f:
                    f.write("x")
            with mock.patch.object(kube.ssl, "create_default_context"), \
                    mock.patch.object(kube, "request", side_effect=[(CRONJOB, {}), (None, {})]):
                self.assertEqual(kube.run_cronjob("hevy-trainer-sync", sa_dir=sa), "")


if __name__ == "__main__":
    unittest.main()
