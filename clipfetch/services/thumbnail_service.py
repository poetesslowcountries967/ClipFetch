from __future__ import annotations

import hashlib
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from clipfetch.config.constants import THUMBNAIL_CACHE_DIR
from clipfetch.config.metadata import APP_VERSION


class ThumbnailService:
    """Small bounded pool for preview thumbnails."""

    MAX_BYTES = 1024 * 1024
    WORKERS = 2

    def __init__(self):
        THUMBNAIL_CACHE_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )
        self._executor = ThreadPoolExecutor(
            max_workers=self.WORKERS,
            thread_name_prefix="thumbnail",
        )

    def fetch_async(self, url, callback):
        if not url:
            callback(False, None)
            return

        self._executor.submit(
            self._fetch,
            url,
            callback,
        )

    def shutdown(self):
        self._executor.shutdown(
            wait=False,
            cancel_futures=True,
        )

    def _fetch(self, url, callback):
        target = THUMBNAIL_CACHE_DIR / (
            hashlib.sha256(
                url.encode("utf-8")
            ).hexdigest()
            + ".img"
        )

        try:
            if target.exists():
                callback(
                    True,
                    target.read_bytes(),
                )
                return

            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": (
                        f"Mozilla/5.0 ClipFetch/{APP_VERSION}"
                    )
                },
            )

            with urllib.request.urlopen(
                request,
                timeout=20,
            ) as response:
                data = response.read(
                    self.MAX_BYTES
                )

            target.write_bytes(data)
            callback(True, data)

        except Exception:
            callback(False, None)
