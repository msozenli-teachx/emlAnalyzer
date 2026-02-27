"""Import EML files into the database."""

from pathlib import Path
from typing import Tuple
from .parser import EmailParser
from .database import Database


class EMLImporter:
    """Import EML files from a directory into the database."""

    def __init__(self, db: Database):
        """Initialize importer with database connection."""
        self.db = db

    def import_from_directory(self, directory: str) -> Tuple[int, int]:
        """
        Import all EML files from a directory.

        Returns (imported_count, duplicate_count)
        """
        directory_path = Path(directory)

        if not directory_path.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

        if not directory_path.is_dir():
            raise NotADirectoryError(f"Not a directory: {directory}")

        eml_files = sorted(directory_path.glob("*.eml"))

        if not eml_files:
            return 0, 0

        imported = 0
        duplicates = 0

        for eml_file in eml_files:
            headers = EmailParser.parse_eml_file(str(eml_file))

            if headers is None:
                continue

            # Validate required fields
            if not headers.get("from_addr") or not headers.get("to_addr"):
                continue

            success = self.db.insert_email(
                message_id=headers.get("message_id"),
                from_addr=headers.get("from_addr"),
                to_addr=headers.get("to_addr"),
                date=headers.get("date"),
                subject=headers.get("subject"),
                in_reply_to=headers.get("in_reply_to"),
            )

            if success:
                imported += 1
            else:
                duplicates += 1

        return imported, duplicates
