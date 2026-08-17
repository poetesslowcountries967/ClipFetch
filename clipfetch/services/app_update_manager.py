from __future__ import annotations

import json
import re
import threading
import urllib.request
from dataclasses import dataclass

from clipfetch.config.metadata import APP_NAME, APP_VERSION, UPDATE_REPOSITORY


@dataclass(frozen=True)
class AppUpdateInfo:
    current_version: str
    latest_version: str
    html_url: str
    dmg_url: str
    release_name: str


class AppUpdateManager:
    @staticmethod
    def _version_tuple(value: str):
        return tuple(int(part) for part in re.findall(r"\d+", value)[:4])

    def check_async(self, callback):
        threading.Thread(target=self._check, args=(callback,), daemon=True).start()

    def _check(self, callback):
        repository = UPDATE_REPOSITORY.strip().strip("/")
        if "/" not in repository:
            callback(False, None, "O repositório oficial de atualização é inválido.")
            return
        url = f"https://api.github.com/repos/{repository}/releases/latest"
        try:
            request = urllib.request.Request(
                url,
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": f"{APP_NAME}/{APP_VERSION}",
                },
            )
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
            tag = str(data.get("tag_name") or data.get("name") or "")
            dmg_url = ""
            for asset in data.get("assets") or []:
                if str(asset.get("name") or "").casefold().endswith(".dmg"):
                    dmg_url = str(asset.get("browser_download_url") or "")
                    break
            callback(
                True,
                AppUpdateInfo(
                    APP_VERSION,
                    tag,
                    str(data.get("html_url") or ""),
                    dmg_url,
                    str(data.get("name") or tag),
                ),
                "",
            )
        except Exception as error:
            callback(False, None, str(error))

    @classmethod
    def is_newer(cls, latest: str):
        return cls._version_tuple(latest) > cls._version_tuple(APP_VERSION)
