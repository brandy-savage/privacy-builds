from __future__ import annotations

import threading

from .app import CompanionApp


class RefreshScheduler:
    def __init__(self, app: CompanionApp, interval_seconds: int):
        self.app = app
        self.interval_seconds = max(60, interval_seconds)
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="catalog-refresh", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def _run(self) -> None:
        # Let the first foreground client request run without contending with a
        # full catalog refresh (remote cloud catalogs can take several seconds).
        if self._stop.wait(min(15, self.interval_seconds)):
            return
        self.app.refresh_catalogs()
        while not self._stop.wait(self.interval_seconds):
            self.app.refresh_catalogs()

    def stop(self) -> None:
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join(timeout=2)
