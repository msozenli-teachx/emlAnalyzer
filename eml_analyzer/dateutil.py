"""Timezone-aware date parsing and utilities for email analysis."""

from datetime import datetime, timezone, timedelta
import re


class DateParser:
    """Parse and normalize email dates with timezone awareness."""

    # RFC 2822 date format regex
    RFC2822_PATTERN = re.compile(
        r'^(?P<day>\w{3}),?\s+'
        r'(?P<date>\d{1,2})\s+'
        r'(?P<month>\w{3})\s+'
        r'(?P<year>\d{4})\s+'
        r'(?P<hour>\d{1,2}):(?P<minute>\d{2})(?::(?P<second>\d{2}))?\s+'
        r'(?P<tz>[+-]\d{4}|[A-Z]{3,4})$'
    )

    MONTH_MAP = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
    }

    TIMEZONE_MAP = {
        'UTC': 0, 'GMT': 0, 'UT': 0,
        'EST': -5, 'EDT': -4,
        'CST': -6, 'CDT': -5,
        'MST': -7, 'MDT': -6,
        'PST': -8, 'PDT': -7,
        'Z': 0,
    }

    @staticmethod
    def parse_date(date_str: str) -> datetime:
        """
        Parse an email date string and return a timezone-aware datetime.

        Handles RFC 2822 format with timezone information.
        Always returns UTC datetime for consistent comparison.

        Args:
            date_str: Email date string (e.g., "Mon, 20 Jan 2024 14:30:00 +0500")

        Returns:
            datetime object in UTC timezone

        Raises:
            ValueError: If date cannot be parsed
        """
        if not date_str:
            raise ValueError("Empty date string")

        date_str = date_str.strip()

        # Try ISO format first (YYYY-MM-DDTHH:MM:SS)
        try:
            if 'T' in date_str:
                # Remove timezone info if present for ISO parsing
                if '+' in date_str:
                    date_str = date_str.split('+')[0]
                elif date_str.count('-') > 2:  # Has timezone offset
                    date_str = date_str.rsplit('-', 1)[0]
                dt = datetime.fromisoformat(date_str)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
        except (ValueError, AttributeError):
            pass

        # Try RFC 2822 format
        match = DateParser.RFC2822_PATTERN.match(date_str)
        if match:
            groups = match.groupdict()
            month = DateParser.MONTH_MAP.get(groups['month'].lower())
            if not month:
                raise ValueError(f"Invalid month: {groups['month']}")

            day = int(groups['date'])
            year = int(groups['year'])
            hour = int(groups['hour'])
            minute = int(groups['minute'])
            second = int(groups['second'] or 0)

            # Parse timezone
            tz_str = groups['tz']
            if tz_str in DateParser.TIMEZONE_MAP:
                tz_offset_hours = DateParser.TIMEZONE_MAP[tz_str]
            else:
                # Parse +/-HHMM format
                try:
                    sign = 1 if tz_str[0] == '+' else -1
                    hours = int(tz_str[1:3])
                    minutes = int(tz_str[3:5])
                    tz_offset_hours = sign * (hours + minutes / 60)
                except (ValueError, IndexError):
                    raise ValueError(f"Invalid timezone: {tz_str}")

            # Create timezone-aware datetime
            tz = timezone(timedelta(hours=tz_offset_hours))
            dt = datetime(year, month, day, hour, minute, second, tzinfo=tz)

            # Convert to UTC
            return dt.astimezone(timezone.utc)

        raise ValueError(f"Cannot parse date: {date_str}")

    @staticmethod
    def parse_date_safe(date_str: str) -> datetime:
        """
        Parse a date string, returning UTC datetime or None on error.

        Args:
            date_str: Email date string

        Returns:
            datetime in UTC, or None if parsing fails
        """
        try:
            return DateParser.parse_date(date_str)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def format_duration(seconds: float) -> str:
        """
        Format a duration in seconds as a human-readable string.

        Args:
            seconds: Duration in seconds

        Returns:
            Formatted string (e.g., "2 days, 3 hours, 15 minutes")
        """
        if seconds < 0:
            return "negative"

        days = int(seconds // 86400)
        remaining = seconds % 86400

        hours = int(remaining // 3600)
        remaining = remaining % 3600

        minutes = int(remaining // 60)
        secs = int(remaining % 60)

        parts = []
        if days > 0:
            parts.append(f"{days} day{'s' if days != 1 else ''}")
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        if secs > 0 or not parts:
            parts.append(f"{secs} second{'s' if secs != 1 else ''}")

        if len(parts) > 2:
            return ", ".join(parts[:-1]) + f", and {parts[-1]}"
        return ", ".join(parts)

    @staticmethod
    def seconds_to_hours(seconds: float) -> float:
        """Convert seconds to hours."""
        return seconds / 3600

    @staticmethod
    def seconds_to_days(seconds: float) -> float:
        """Convert seconds to days."""
        return seconds / 86400
