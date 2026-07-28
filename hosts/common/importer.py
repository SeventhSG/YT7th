"""Orchestrates: a finished engine job -> media in the host editor.

Pure logic over an *import host* adapter that any editor plugin provides
(Resolve, Premiere, ...). The adapter must expose:
    import_media(paths) -> list of clip handles
    has_timeline() -> bool
    append_to_timeline(clips) -> None
So this module is host-agnostic and fully testable with a fake host. No
editor API and no HTTP live here.
"""


class ImportResult:
    def __init__(self, imported, appended, message=""):
        self.imported = imported      # file paths imported to the Media Pool
        self.appended = appended      # clips appended to the timeline
        self.message = message        # human-facing note (e.g. why not appended)

    def __repr__(self):
        return (f"ImportResult(imported={self.imported!r}, "
                f"appended={self.appended!r}, message={self.message!r})")


def import_finished_job(host, job, append_to_timeline=False):
    """Import a done job's files into Resolve.

    host   - an import host adapter (ResolveHost, PremiereHost, fake, ...)
    job    - a job dict from the engine (needs "files" or "filepath")
    append - also append the imported clips to the current timeline

    Returns an ImportResult. Raises ValueError if the job has no files.
    """
    files = list(job.get("files") or ([job["filepath"]] if job.get("filepath")
                                      else []))
    if not files:
        raise ValueError("This job produced no file to import.")

    clips = host.import_media(files)
    if not append_to_timeline:
        return ImportResult(files, [], "")

    if not host.has_timeline():
        return ImportResult(files, [],
                            "Imported to Media Pool. Open a timeline to append.")

    host.append_to_timeline(clips)
    return ImportResult(files, clips, "")
