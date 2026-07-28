"""Thin adapter over DaVinci Resolve's scripting API.

Every call into the `resolve` global lives here so the rest of the plugin can
be tested with FakeResolveHost. The real API only exists inside Resolve.
"""


class ResolveHost:
    """Wraps the Resolve scripting `resolve` object."""

    def __init__(self, resolve):
        self._resolve = resolve

    def _media_pool(self):
        proj = self._resolve.GetProjectManager().GetCurrentProject()
        if proj is None:
            raise RuntimeError("No project is open in Resolve.")
        return proj, proj.GetMediaPool()

    def import_media(self, paths):
        """Import files into the current project's Media Pool.
        Returns the list of created MediaPoolItem objects."""
        _, pool = self._media_pool()
        items = pool.ImportMedia(list(paths))
        return items or []

    def has_timeline(self):
        proj = self._resolve.GetProjectManager().GetCurrentProject()
        return bool(proj and proj.GetCurrentTimeline())

    def append_to_timeline(self, clips):
        """Append MediaPoolItems to the current timeline."""
        _, pool = self._media_pool()
        pool.AppendToTimeline(list(clips))


class FakeResolveHost:
    """In-memory stand-in for tests. Records what would happen in Resolve."""

    def __init__(self, has_timeline=True, import_returns=None,
                 project_open=True):
        self._project_open = project_open
        self._has_timeline = has_timeline
        self._import_returns = import_returns
        self.imported = []
        self.appended = []

    def import_media(self, paths):
        if not self._project_open:
            raise RuntimeError("No project is open in Resolve.")
        paths = list(paths)
        self.imported.extend(paths)
        # Default: one clip object per path (its path string as a stand-in).
        return (self._import_returns
                if self._import_returns is not None else list(paths))

    def has_timeline(self):
        return self._has_timeline

    def append_to_timeline(self, clips):
        if not self._project_open:
            raise RuntimeError("No project is open in Resolve.")
        self.appended.extend(list(clips))
