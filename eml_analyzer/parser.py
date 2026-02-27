"""EML file parser for extracting email headers."""

import email
from pathlib import Path
from typing import Optional, Dict, Tuple
from email.parser import BytesParser
from email.policy import default


class EmailParser:
    """Parse EML files and extract headers."""

    @staticmethod
    def parse_eml_file(file_path: str) -> Optional[Dict]:
        """
        Parse an EML file and extract basic headers.

        Returns a dict with: from_addr, to_addr, date, subject, message_id, in_reply_to
        Returns None if parsing fails.
        """
        try:
            with open(file_path, "rb") as f:
                msg = BytesParser(policy=default).parse(f)

            return EmailParser._extract_headers(msg)
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None

    @staticmethod
    def _extract_headers(msg) -> Dict:
        """Extract relevant headers from an email message."""
        return {
            "from_addr": EmailParser._get_header(msg, "from", ""),
            "to_addr": EmailParser._get_header(msg, "to", ""),
            "date": EmailParser._get_header(msg, "date", ""),
            "subject": EmailParser._get_header(msg, "subject", ""),
            "message_id": EmailParser._get_header(msg, "message-id", None),
            "in_reply_to": EmailParser._get_header(msg, "in-reply-to", None),
        }

    @staticmethod
    def _get_header(msg, header_name: str, default_value=None):
        """Get a header value from email message."""
        value = msg.get(header_name)
        if value is None:
            return default_value
        # Convert header object to string
        return str(value).strip()
