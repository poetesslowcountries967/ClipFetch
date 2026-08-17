from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from clipfetch.config.constants import (
    APP_SUPPORT_DIR,
    DATABASE_FILE,
)


class HistoryManager:
    """
    Histórico genérico de mídia.

    Identidade principal:
        extractor_key + media_id

    Essa combinação é independente do site específico. O campo `source`
    continua guardando o URL resolvido e serve também como fallback para
    registros antigos que ainda não possuem media_id.

    O banco não substitui o download archive do yt-dlp:
    - download archive: impede repetição;
    - SQLite: guarda contexto, fonte e caminho final.
    """

    SUCCESS_STATUSES = (
        "Concluído",
        "Já baixado",
        "Já baixado — arquivo não encontrado",
    )

    def __init__(self):
        APP_SUPPORT_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS downloads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    source TEXT,
                    title TEXT NOT NULL,
                    extractor TEXT,
                    extractor_key TEXT,
                    media_id TEXT,
                    media_key TEXT,
                    output_path TEXT,
                    output_format TEXT,
                    resolution TEXT,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )

            columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(downloads)"
                ).fetchall()
            }

            migrations = {
                "source": (
                    "ALTER TABLE downloads "
                    "ADD COLUMN source TEXT"
                ),
                "extractor_key": (
                    "ALTER TABLE downloads "
                    "ADD COLUMN extractor_key TEXT"
                ),
                "media_id": (
                    "ALTER TABLE downloads "
                    "ADD COLUMN media_id TEXT"
                ),
                "media_key": (
                    "ALTER TABLE downloads "
                    "ADD COLUMN media_key TEXT"
                ),
            }

            for column, statement in migrations.items():
                if column not in columns:
                    connection.execute(statement)

            # Migração dos dados legados.
            connection.execute(
                """
                UPDATE downloads
                SET source = url
                WHERE source IS NULL OR TRIM(source) = ''
                """
            )

            connection.execute(
                """
                UPDATE downloads
                SET extractor_key = extractor
                WHERE (
                    extractor_key IS NULL
                    OR TRIM(extractor_key) = ''
                )
                AND extractor IS NOT NULL
                AND TRIM(extractor) != ''
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_downloads_media_key
                ON downloads(media_key)
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_downloads_source
                ON downloads(source)
                """
            )

    def _connect(self):
        connection = sqlite3.connect(
            DATABASE_FILE
        )
        connection.row_factory = (
            sqlite3.Row
        )
        return connection

    @staticmethod
    def make_media_key(
        extractor_key,
        media_id,
    ):
        extractor = str(
            extractor_key
            or ""
        ).strip().casefold()

        identifier = str(
            media_id
            or ""
        ).strip()

        if not extractor or not identifier:
            return ""

        return f"{extractor}:{identifier}"

    def add(self, **data):
        url = str(
            data.get("url", "")
            or ""
        )

        source = str(
            data.get("source", "")
            or url
        )

        extractor = str(
            data.get("extractor", "")
            or ""
        )

        extractor_key = str(
            data.get("extractor_key", "")
            or extractor
        )

        media_id = str(
            data.get("media_id", "")
            or ""
        )

        media_key = str(
            data.get("media_key", "")
            or self.make_media_key(
                extractor_key,
                media_id,
            )
        )

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO downloads (
                    url,
                    source,
                    title,
                    extractor,
                    extractor_key,
                    media_id,
                    media_key,
                    output_path,
                    output_format,
                    resolution,
                    status,
                    error_message,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    url,
                    source,
                    data.get("title", ""),
                    extractor,
                    extractor_key,
                    media_id,
                    media_key,
                    data.get("output_path", ""),
                    data.get("output_format", ""),
                    data.get("resolution", ""),
                    data.get("status", ""),
                    data.get("error_message", ""),
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),
                ),
            )

    def list_recent(
        self,
        limit=500,
    ):
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM downloads
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    def get(
        self,
        record_id,
    ):
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM downloads
                WHERE id = ?
                """,
                (record_id,),
            ).fetchone()

        return (
            dict(row)
            if row
            else None
        )

    def _matching_success_records(
        self,
        extractor_key,
        media_id,
        source,
        limit=100,
    ):
        """
        Retorna registros anteriores da mesma mídia.

        Prioridade:
        1. extractor_key + media_id;
        2. source exata para dados legados sem media_id.
        """

        media_key = self.make_media_key(
            extractor_key,
            media_id,
        )

        placeholders = ",".join(
            "?"
            for _ in self.SUCCESS_STATUSES
        )

        with self._connect() as connection:
            if media_key:
                rows = connection.execute(
                    f"""
                    SELECT *
                    FROM downloads
                    WHERE media_key = ?
                    AND status IN ({placeholders})
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (
                        media_key,
                        *self.SUCCESS_STATUSES,
                        limit,
                    ),
                ).fetchall()

                if rows:
                    return [
                        dict(row)
                        for row in rows
                    ]

            source = str(
                source
                or ""
            ).strip()

            if not source:
                return []

            rows = connection.execute(
                f"""
                SELECT *
                FROM downloads
                WHERE source = ?
                AND status IN ({placeholders})
                ORDER BY id DESC
                LIMIT ?
                """,
                (
                    source,
                    *self.SUCCESS_STATUSES,
                    limit,
                ),
            ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    def find_previous_download(
        self,
        extractor_key,
        media_id,
        source,
    ):
        """
        Localiza o melhor registro anterior.

        Retorno:
        {
            "record": dict | None,
            "output_path": str,
            "file_exists": bool,
            "matched_by": "media_key" | "source" | ""
        }

        Se houver vários registros, um caminho que ainda existe no disco
        tem prioridade sobre um registro mais recente com caminho vazio.
        """

        media_key = self.make_media_key(
            extractor_key,
            media_id,
        )

        rows = self._matching_success_records(
            extractor_key,
            media_id,
            source,
        )

        if not rows:
            return {
                "record": None,
                "output_path": "",
                "file_exists": False,
                "matched_by": "",
            }

        matched_by = (
            "media_key"
            if media_key
            and any(
                row.get("media_key")
                == media_key
                for row in rows
            )
            else "source"
        )

        first = rows[0]

        for row in rows:
            output_path = str(
                row.get("output_path")
                or ""
            ).strip()

            if (
                output_path
                and Path(output_path).exists()
            ):
                return {
                    "record": row,
                    "output_path": output_path,
                    "file_exists": True,
                    "matched_by": matched_by,
                }

        return {
            "record": first,
            "output_path": str(
                first.get("output_path")
                or ""
            ).strip(),
            "file_exists": False,
            "matched_by": matched_by,
        }

    def clear(self):
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM downloads"
            )
