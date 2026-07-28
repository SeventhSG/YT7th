"""Drive one download from URL to imported media, host-agnostic.

This is the core plugin flow, lifted out of any editor's UI shell so it can
be tested without that editor running:

    submit -> poll until terminal -> import into the host editor

The caller provides an EngineClient and an import-host adapter; UI code only
wires a status callback and, for Resolve, runs this on a worker thread.
"""
import time


class JobOutcome:
    def __init__(self, ok, status, message, job, import_result=None):
        self.ok = ok                      # True if media was imported
        self.status = status              # final job status: done/error/cancelled
        self.message = message            # human-facing summary
        self.job = job                    # last job dict seen
        self.import_result = import_result

    def __repr__(self):
        return (f"JobOutcome(ok={self.ok}, status={self.status!r}, "
                f"message={self.message!r})")


def run_job(client, host, url, settings, append_to_timeline=False,
            on_status=None, poll_interval=1.0, sleep=time.sleep,
            import_finished=None):
    """Submit `url`, poll to completion, then import into `host`.

    Returns a JobOutcome. Never raises for expected failures (engine errors,
    empty results) - they come back as ok=False with a message.
    """
    from .importer import import_finished_job
    from .engine_client import EngineError, TERMINAL
    import_finished = import_finished or import_finished_job

    def status(text):
        if on_status:
            on_status(text)

    try:
        status("Fetching video info...")
        job = client.submit(url, settings)
        job_id = job["id"]

        while job.get("status") not in TERMINAL:
            sleep(poll_interval)
            job = client.get_job(job_id)
            st = job.get("status")
            if st == "downloading":
                status(f"Downloading {job.get('title') or ''} "
                       f"{job.get('percent', 0):.0f}%".strip())
            elif st == "processing":
                status("Processing...")

        if job["status"] == "error":
            return JobOutcome(False, "error", f"Error: {job.get('error')}", job)
        if job["status"] == "cancelled":
            return JobOutcome(False, "cancelled", "Cancelled.", job)

        status("Importing into the editor...")
        result = import_finished(host, job, append_to_timeline)
        msg = result.message or (
            f"Done. Imported {len(result.imported)} file(s)"
            + (f", appended {len(result.appended)}." if result.appended else ".")
        )
        return JobOutcome(True, "done", msg, job, result)
    except EngineError as e:
        return JobOutcome(False, "error", f"Engine error: {e}", None)
    except ValueError as e:
        return JobOutcome(False, "error", str(e), None)
