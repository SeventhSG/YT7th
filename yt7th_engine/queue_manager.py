"""Sequential download queue driving the Downloader, one item at a time."""
import shutil
import threading
from dataclasses import dataclass, field

from . import downloader

LOW_SPACE_GB = 1.0

# Item lifecycle: fetching -> queued -> downloading -> done
#                 any non-terminal state -> cancelled / error
TERMINAL = ("done", "error", "cancelled")


def default_space_check(settings):
    """Return an error message if the target drive is low on space, else None."""
    try:
        free = shutil.disk_usage(settings.get("download_dir", ".")).free
    except OSError:
        return None
    free_gb = free / 1_000_000_000
    if free_gb < LOW_SPACE_GB:
        return (f"Low disk space ({free_gb:.1f} GB free). Merging may fail - "
                "free up space or change the download folder in Settings.")
    return None


@dataclass
class QueueItem:
    id: int
    url: str
    settings: dict
    status: str = "fetching"
    metadata: dict = field(default_factory=dict)
    progress: dict = field(default_factory=dict)
    files: list = field(default_factory=list)  # output paths, in finish order
    error: str = ""


class QueueManager:
    """Owns the item list and a worker thread that downloads strictly in
    FIFO order. All callbacks fire on worker/fetch threads - UI must marshal.
    """

    def __init__(self, on_update=None, on_file_done=None,
                 downloader_factory=downloader.Downloader,
                 info_fetcher=None, space_check=default_space_check):
        self._on_update = on_update
        self._on_file_done = on_file_done
        self._factory = downloader_factory
        self._fetch = info_fetcher or downloader.fetch_info
        self._space_check = space_check
        self._items = []
        self._next_id = 1
        self._active_downloader = None
        self._shutdown = False
        self._cond = threading.Condition()
        self._worker = threading.Thread(target=self._work, daemon=True)
        self._worker.start()

    def items(self):
        with self._cond:
            return list(self._items)

    def add(self, url, settings):
        with self._cond:
            item = QueueItem(self._next_id, url, dict(settings))
            self._next_id += 1
            self._items.append(item)
        self._notify(item)
        threading.Thread(target=self._fetch_meta, args=(item,),
                         daemon=True).start()
        return item

    def remove(self, item_id):
        """Cancel an active item, drop a pending one, forget a finished one."""
        with self._cond:
            item = next((i for i in self._items if i.id == item_id), None)
            if item is None:
                return
            if item.status == "downloading":
                if self._active_downloader:
                    self._active_downloader.cancel()
                return  # error_cb("Cancelled") finishes the transition
            if item.status in TERMINAL:
                self._items.remove(item)
                return
            item.status = "cancelled"
            self._cond.notify_all()
        self._notify(item)

    def shutdown(self):
        with self._cond:
            self._shutdown = True
            if self._active_downloader:
                self._active_downloader.cancel()
            self._cond.notify_all()

    def _notify(self, item):
        if self._on_update:
            self._on_update(item)

    def _fetch_meta(self, item):
        try:
            meta = self._fetch(item.url, item.settings)
            with self._cond:
                if item.status != "fetching":
                    return  # cancelled while fetching
                item.metadata = meta
                item.status = "queued"
                self._cond.notify_all()
        except Exception as e:  # noqa: BLE001
            with self._cond:
                if item.status != "fetching":
                    return
                item.status = "error"
                item.error = downloader.friendly_error(str(e))
        self._notify(item)

    def _next_item(self):
        """First item not yet finished; None while it is still fetching."""
        for item in self._items:
            if item.status in TERMINAL:
                continue
            return item if item.status == "queued" else None
        return None

    def _work(self):
        while True:
            with self._cond:
                item = self._next_item()
                while item is None and not self._shutdown:
                    self._cond.wait()
                    item = self._next_item()
                if self._shutdown:
                    return
                space_err = self._space_check(item.settings)
                if space_err:
                    item.status = "error"
                    item.error = space_err
                    self._notify(item)
                    continue
                item.status = "downloading"
                dl = self._factory(
                    progress_cb=lambda p, i=item: self._on_progress(i, p),
                    done_cb=lambda *a, i=item: self._file_done(i, *a),
                    error_cb=lambda msg, i=item: self._on_error(i, msg),
                )
                self._active_downloader = dl
            self._notify(item)
            dl.download(item.url, item.settings)
            with self._cond:
                self._active_downloader = None
                if item.status == "downloading":
                    item.status = "done"
                    item.progress = {**item.progress, "percent": 100}
            self._notify(item)

    def _on_progress(self, item, p):
        with self._cond:
            item.progress = p
        self._notify(item)

    def _file_done(self, item, title, url, filepath, quality):
        if filepath:
            with self._cond:
                item.files.append(filepath)
        if self._on_file_done:
            self._on_file_done(title, url, filepath, quality)

    def _on_error(self, item, msg):
        with self._cond:
            item.status = "cancelled" if msg == "Cancelled" else "error"
            if msg != "Cancelled":
                item.error = msg
        self._notify(item)
