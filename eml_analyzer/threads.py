"""Thread reconstruction and analysis module."""

import sqlite3
from typing import Optional, List, Dict, Tuple, Set
from collections import defaultdict
from .dateutil import DateParser


class ThreadManager:
    """Manages email thread reconstruction and analysis."""

    def __init__(self, db_connection):
        """Initialize thread manager with database connection."""
        self.connection = db_connection
        self._init_thread_tables()

    def _init_thread_tables(self):
        """Initialize thread-related tables."""
        cursor = self.connection.cursor()

        # Threads table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS threads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                root_message_id TEXT,
                subject TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Thread members (which emails belong to which thread)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS thread_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id INTEGER NOT NULL,
                email_id INTEGER NOT NULL,
                FOREIGN KEY (thread_id) REFERENCES threads(id),
                FOREIGN KEY (email_id) REFERENCES emails(id),
                UNIQUE(thread_id, email_id)
            )
        """)

        # Interactions (directed: sender -> recipient)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT NOT NULL,
                recipient TEXT NOT NULL,
                count INTEGER DEFAULT 1,
                last_interaction TEXT,
                UNIQUE(sender, recipient)
            )
        """)

        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_thread_members_thread_id 
            ON thread_members(thread_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_thread_members_email_id 
            ON thread_members(email_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_interactions_sender 
            ON interactions(sender)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_interactions_recipient 
            ON interactions(recipient)
        """)

        # Response times table (stores pre-calculated response times)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS response_times (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reply_email_id INTEGER NOT NULL,
                original_email_id INTEGER NOT NULL,
                replier TEXT NOT NULL,
                original_sender TEXT NOT NULL,
                response_seconds INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (reply_email_id) REFERENCES emails(id),
                FOREIGN KEY (original_email_id) REFERENCES emails(id),
                UNIQUE(reply_email_id, original_email_id)
            )
        """)

        # Create indexes for response times
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_response_times_replier 
            ON response_times(replier)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_response_times_original_sender 
            ON response_times(original_sender)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_response_times_reply_email_id 
            ON response_times(reply_email_id)
        """)

        # Daily activity table (messages per day)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL UNIQUE,
                message_count INTEGER NOT NULL,
                unique_senders INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Hourly distribution table (messages per hour of day)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hourly_distribution (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hour INTEGER NOT NULL UNIQUE,
                message_count INTEGER NOT NULL,
                unique_senders INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Thread lifetime table (first and last message per thread)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS thread_lifetimes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id INTEGER NOT NULL UNIQUE,
                first_message_date TEXT NOT NULL,
                last_message_date TEXT NOT NULL,
                lifetime_seconds INTEGER NOT NULL,
                message_count INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (thread_id) REFERENCES threads(id)
            )
        """)

        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_daily_activity_date 
            ON daily_activity(date)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_hourly_distribution_hour 
            ON hourly_distribution(hour)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_thread_lifetimes_thread_id 
            ON thread_lifetimes(thread_id)
        """)

        self.connection.commit()

    def reconstruct_threads(self) -> Tuple[int, int]:
        """
        Reconstruct email threads using Message-ID and In-Reply-To.

        Returns (thread_count, orphaned_count)
        """
        cursor = self.connection.cursor()

        # Get all emails with their IDs and headers
        cursor.execute("""
            SELECT id, message_id, in_reply_to, from_addr, to_addr, subject, date
            FROM emails
            ORDER BY date ASC
        """)
        emails = cursor.fetchall()

        # Build lookup maps
        msg_id_to_email = {}  # message_id -> email row
        email_id_to_msg_id = {}  # email_id -> message_id
        email_id_to_in_reply_to = {}  # email_id -> in_reply_to

        for email in emails:
            email_id = email["id"]
            msg_id = email["message_id"]
            in_reply_to = email["in_reply_to"]

            if msg_id:
                msg_id_to_email[msg_id] = email
            email_id_to_msg_id[email_id] = msg_id
            if in_reply_to:
                email_id_to_in_reply_to[email_id] = in_reply_to

        # Find thread roots using Union-Find approach
        parent = {}  # email_id -> root_email_id

        def find_root(email_id):
            """Find root of thread using path compression."""
            if email_id not in parent:
                parent[email_id] = email_id
            if parent[email_id] != email_id:
                parent[email_id] = find_root(parent[email_id])
            return parent[email_id]

        def union(email_id1, email_id2):
            """Union two emails into same thread."""
            root1 = find_root(email_id1)
            root2 = find_root(email_id2)
            if root1 != root2:
                parent[root1] = root2

        # Process each email
        for email in emails:
            email_id = email["id"]
            in_reply_to = email["in_reply_to"]

            if in_reply_to and in_reply_to in msg_id_to_email:
                # Parent exists - connect to it
                parent_email = msg_id_to_email[in_reply_to]
                parent_email_id = parent_email["id"]
                union(email_id, parent_email_id)
            else:
                # No parent or parent missing - this is a root or orphan
                find_root(email_id)

        # Group emails by thread root
        threads_map = defaultdict(list)
        for email in emails:
            root = find_root(email["id"])
            threads_map[root].append(email)

        # Create threads in database
        thread_count = 0
        orphaned_count = 0

        for root_email_id, thread_emails in threads_map.items():
            # Get root email info
            root_email = next(e for e in emails if e["id"] == root_email_id)
            root_msg_id = root_email["message_id"]
            subject = root_email["subject"] or "(no subject)"

            # Create thread
            cursor.execute(
                """
                INSERT INTO threads (root_message_id, subject)
                VALUES (?, ?)
                """,
                (root_msg_id, subject),
            )
            thread_id = cursor.lastrowid
            thread_count += 1

            # Add emails to thread
            for email in thread_emails:
                cursor.execute(
                    """
                    INSERT INTO thread_members (thread_id, email_id)
                    VALUES (?, ?)
                    """,
                    (thread_id, email["id"]),
                )

                # Count orphaned emails (those without parent)
                if email["in_reply_to"] and email["in_reply_to"] not in msg_id_to_email:
                    if email["id"] != root_email_id:
                        orphaned_count += 1

        self.connection.commit()
        return thread_count, orphaned_count

    def build_interactions(self) -> int:
        """
        Build interaction model from replies.

        For each reply (email with in_reply_to), track sender -> original_sender interaction.
        Returns interaction count.
        """
        cursor = self.connection.cursor()

        # Get all emails with their message IDs and headers
        cursor.execute("""
            SELECT id, message_id, in_reply_to, from_addr
            FROM emails
            WHERE in_reply_to IS NOT NULL AND in_reply_to != ''
        """)
        replies = cursor.fetchall()

        # Build message_id -> sender map
        cursor.execute("""
            SELECT message_id, from_addr FROM emails
        """)
        msg_id_to_sender = {}
        for row in cursor.fetchall():
            if row["message_id"]:
                msg_id_to_sender[row["message_id"]] = row["from_addr"]

        # Track interactions
        interactions = defaultdict(lambda: {"count": 0, "last_date": None})

        cursor.execute("""
            SELECT id, in_reply_to, from_addr, date FROM emails
            WHERE in_reply_to IS NOT NULL AND in_reply_to != ''
        """)

        for email in cursor.fetchall():
            in_reply_to = email["in_reply_to"]
            sender = email["from_addr"]
            date = email["date"]

            # Find original sender
            if in_reply_to in msg_id_to_sender:
                original_sender = msg_id_to_sender[in_reply_to]
                key = (sender, original_sender)
                interactions[key]["count"] += 1
                interactions[key]["last_date"] = date

        # Insert interactions into database
        for (sender, recipient), data in interactions.items():
            cursor.execute(
                """
                INSERT INTO interactions (sender, recipient, count, last_interaction)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(sender, recipient) DO UPDATE SET
                    count = count + ?,
                    last_interaction = ?
                """,
                (sender, recipient, data["count"], data["last_date"], data["count"], data["last_date"]),
            )

        self.connection.commit()
        return len(interactions)

    def get_all_threads(self) -> List[Dict]:
        """Get all threads with message counts."""
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT 
                t.id,
                t.root_message_id,
                t.subject,
                COUNT(tm.email_id) as message_count
            FROM threads t
            LEFT JOIN thread_members tm ON t.id = tm.thread_id
            GROUP BY t.id
            ORDER BY message_count DESC
        """)

        threads = []
        for row in cursor.fetchall():
            threads.append({
                "id": row["id"],
                "root_message_id": row["root_message_id"],
                "subject": row["subject"],
                "message_count": row["message_count"] or 0,
            })
        return threads

    def get_thread_emails(self, thread_id: int) -> List[Dict]:
        """Get all emails in a thread in chronological order."""
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT 
                e.id,
                e.message_id,
                e.from_addr,
                e.to_addr,
                e.date,
                e.subject,
                e.in_reply_to
            FROM emails e
            JOIN thread_members tm ON e.id = tm.email_id
            WHERE tm.thread_id = ?
            ORDER BY e.date ASC
        """, (thread_id,))

        emails = []
        for row in cursor.fetchall():
            emails.append({
                "id": row["id"],
                "message_id": row["message_id"],
                "from": row["from_addr"],
                "to": row["to_addr"],
                "date": row["date"],
                "subject": row["subject"],
                "in_reply_to": row["in_reply_to"],
            })
        return emails

    def get_top_senders(self, limit: int = 10) -> List[Dict]:
        """Get top users by replies sent."""
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT sender, SUM(count) as total_replies
            FROM interactions
            GROUP BY sender
            ORDER BY total_replies DESC
            LIMIT ?
        """, (limit,))

        users = []
        for row in cursor.fetchall():
            users.append({
                "sender": row["sender"],
                "total_replies": row["total_replies"],
            })
        return users

    def get_top_recipients(self, limit: int = 10) -> List[Dict]:
        """Get top users by replies received."""
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT recipient, SUM(count) as total_replies_received
            FROM interactions
            GROUP BY recipient
            ORDER BY total_replies_received DESC
            LIMIT ?
        """, (limit,))

        users = []
        for row in cursor.fetchall():
            users.append({
                "recipient": row["recipient"],
                "total_replies_received": row["total_replies_received"],
            })
        return users

    def get_dominance_scores(self, limit: int = 10) -> List[Dict]:
        """
        Calculate dominance score for each user.

        Dominance = (replies_sent - replies_received) / (replies_sent + replies_received)
        Range: -1 (only receives) to +1 (only sends)
        """
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT 
                COALESCE(i1.sender, i2.recipient) as user,
                COALESCE(SUM(i1.count), 0) as sent,
                COALESCE(SUM(i2.count), 0) as received
            FROM interactions i1
            FULL OUTER JOIN interactions i2 
                ON i1.sender = i2.recipient
            WHERE i1.sender IS NOT NULL OR i2.recipient IS NOT NULL
            GROUP BY user
            ORDER BY user
        """)

        # Fallback for databases without FULL OUTER JOIN support
        try:
            results = cursor.fetchall()
        except sqlite3.OperationalError:
            # Use alternative approach for SQLite
            cursor.execute("""
                SELECT sender as user FROM interactions
                UNION
                SELECT recipient as user FROM interactions
            """)
            users = [row["user"] for row in cursor.fetchall()]

            results = []
            for user in users:
                cursor.execute("""
                    SELECT SUM(count) as sent FROM interactions WHERE sender = ?
                """, (user,))
                sent = cursor.fetchone()["sent"] or 0

                cursor.execute("""
                    SELECT SUM(count) as received FROM interactions WHERE recipient = ?
                """, (user,))
                received = cursor.fetchone()["received"] or 0

                results.append({
                    "user": user,
                    "sent": sent,
                    "received": received,
                })

        scores = []
        for row in results:
            user = row["user"]
            sent = row["sent"]
            received = row["received"]
            total = sent + received

            if total > 0:
                dominance = (sent - received) / total
            else:
                dominance = 0.0

            scores.append({
                "user": user,
                "sent": sent,
                "received": received,
                "dominance_score": dominance,
            })

        # Sort by dominance score descending, then by total activity
        scores.sort(key=lambda x: (x["dominance_score"], x["sent"] + x["received"]), reverse=True)
        return scores[:limit]

    def get_interaction_between(self, user1: str, user2: str) -> Dict:
        """Get interaction stats between two specific users."""
        cursor = self.connection.cursor()

        # Get interaction from user1 to user2
        cursor.execute("""
            SELECT count FROM interactions
            WHERE sender = ? AND recipient = ?
        """, (user1, user2))
        row1 = cursor.fetchone()
        count1 = row1["count"] if row1 else 0

        # Get interaction from user2 to user1
        cursor.execute("""
            SELECT count FROM interactions
            WHERE sender = ? AND recipient = ?
        """, (user2, user1))
        row2 = cursor.fetchone()
        count2 = row2["count"] if row2 else 0

        return {
            "user1_to_user2": count1,
            "user2_to_user1": count2,
            "total": count1 + count2,
        }

    def calculate_response_times(self) -> int:
        """
        Calculate response times for all replies.

        For each reply (email with in_reply_to), find the original email
        and calculate the time difference. Store in response_times table.

        Returns: Number of response times calculated
        """
        cursor = self.connection.cursor()

        # Get all emails with in_reply_to header
        cursor.execute("""
            SELECT id, message_id, in_reply_to, from_addr, date FROM emails
            WHERE in_reply_to IS NOT NULL AND in_reply_to != ''
        """)
        replies = cursor.fetchall()

        # Build message_id to email map
        cursor.execute("""
            SELECT id, message_id, from_addr, date FROM emails
        """)
        msg_id_to_email = {}
        for row in cursor.fetchall():
            if row["message_id"]:
                msg_id_to_email[row["message_id"]] = row

        response_count = 0

        for reply in replies:
            reply_id = reply["id"]
            in_reply_to = reply["in_reply_to"]
            replier = reply["from_addr"]
            reply_date_str = reply["date"]

            # Find original email
            if in_reply_to not in msg_id_to_email:
                continue

            original = msg_id_to_email[in_reply_to]
            original_id = original["id"]
            original_sender = original["from_addr"]
            original_date_str = original["date"]

            # Parse dates with timezone awareness
            try:
                reply_date = DateParser.parse_date(reply_date_str)
                original_date = DateParser.parse_date(original_date_str)
            except (ValueError, TypeError):
                continue

            # Calculate response time in seconds
            response_seconds = int((reply_date - original_date).total_seconds())

            # Skip negative response times (clock skew)
            if response_seconds < 0:
                continue

            # Insert into response_times table
            try:
                cursor.execute(
                    """
                    INSERT INTO response_times
                    (reply_email_id, original_email_id, replier, original_sender, response_seconds)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (reply_id, original_id, replier, original_sender, response_seconds),
                )
                response_count += 1
            except sqlite3.IntegrityError:
                # Already exists
                pass

        self.connection.commit()
        return response_count

    def get_overall_average_response_time(self) -> Dict:
        """
        Get overall average response time across all replies.

        Returns dict with:
            - avg_seconds: Average response time in seconds
            - avg_hours: Average response time in hours
            - avg_days: Average response time in days
            - total_replies: Total number of replies analyzed
            - min_seconds: Minimum response time
            - max_seconds: Maximum response time
            - median_seconds: Median response time
        """
        cursor = self.connection.cursor()

        cursor.execute("""
            SELECT 
                COUNT(*) as total_replies,
                AVG(response_seconds) as avg_seconds,
                MIN(response_seconds) as min_seconds,
                MAX(response_seconds) as max_seconds
            FROM response_times
        """)
        result = cursor.fetchone()

        if not result or result["total_replies"] == 0:
            return {
                "avg_seconds": 0,
                "avg_hours": 0,
                "avg_days": 0,
                "total_replies": 0,
                "min_seconds": 0,
                "max_seconds": 0,
                "median_seconds": 0,
            }

        total = result["total_replies"]
        avg_sec = result["avg_seconds"] or 0
        min_sec = result["min_seconds"] or 0
        max_sec = result["max_seconds"] or 0

        # Calculate median
        cursor.execute("""
            SELECT response_seconds FROM response_times
            ORDER BY response_seconds
            LIMIT 1 OFFSET ?
        """, (total // 2,))
        median_row = cursor.fetchone()
        median_sec = median_row["response_seconds"] if median_row else 0

        return {
            "avg_seconds": avg_sec,
            "avg_hours": avg_sec / 3600,
            "avg_days": avg_sec / 86400,
            "total_replies": total,
            "min_seconds": min_sec,
            "max_seconds": max_sec,
            "median_seconds": median_sec,
        }

    def get_average_response_time_by_user(self, limit: int = 10) -> List[Dict]:
        """
        Get average response time for each user (as replier).

        Args:
            limit: Maximum number of users to return

        Returns:
            List of dicts with:
                - replier: User email
                - avg_seconds: Average response time
                - avg_hours: Average in hours
                - avg_days: Average in days
                - reply_count: Number of replies
        """
        cursor = self.connection.cursor()

        cursor.execute("""
            SELECT 
                replier,
                COUNT(*) as reply_count,
                AVG(response_seconds) as avg_seconds,
                MIN(response_seconds) as min_seconds,
                MAX(response_seconds) as max_seconds
            FROM response_times
            GROUP BY replier
            ORDER BY avg_seconds ASC
            LIMIT ?
        """, (limit,))

        users = []
        for row in cursor.fetchall():
            avg_sec = row["avg_seconds"] or 0
            users.append({
                "replier": row["replier"],
                "avg_seconds": avg_sec,
                "avg_hours": avg_sec / 3600,
                "avg_days": avg_sec / 86400,
                "reply_count": row["reply_count"],
                "min_seconds": row["min_seconds"] or 0,
                "max_seconds": row["max_seconds"] or 0,
            })

        return users

    def get_average_response_time_to_user(self, limit: int = 10) -> List[Dict]:
        """
        Get average response time to each user (as original sender).

        This shows how quickly users get replies to their messages.

        Args:
            limit: Maximum number of users to return

        Returns:
            List of dicts with:
                - original_sender: User email
                - avg_seconds: Average response time to their messages
                - avg_hours: Average in hours
                - avg_days: Average in days
                - reply_count: Number of replies received
        """
        cursor = self.connection.cursor()

        cursor.execute("""
            SELECT 
                original_sender,
                COUNT(*) as reply_count,
                AVG(response_seconds) as avg_seconds,
                MIN(response_seconds) as min_seconds,
                MAX(response_seconds) as max_seconds
            FROM response_times
            GROUP BY original_sender
            ORDER BY avg_seconds ASC
            LIMIT ?
        """, (limit,))

        users = []
        for row in cursor.fetchall():
            avg_sec = row["avg_seconds"] or 0
            users.append({
                "original_sender": row["original_sender"],
                "avg_seconds": avg_sec,
                "avg_hours": avg_sec / 3600,
                "avg_days": avg_sec / 86400,
                "reply_count": row["reply_count"],
                "min_seconds": row["min_seconds"] or 0,
                "max_seconds": row["max_seconds"] or 0,
            })

        return users

    def get_response_time_stats(self) -> Dict:
        """
        Get comprehensive response time statistics.

        Returns dict with overall stats and top responders.
        """
        overall = self.get_overall_average_response_time()
        by_replier = self.get_average_response_time_by_user(limit=5)
        to_user = self.get_average_response_time_to_user(limit=5)

        return {
            "overall": overall,
            "fastest_responders": by_replier,
            "most_replied_to": to_user,
        }

    def calculate_daily_activity(self) -> int:
        """
        Calculate daily message counts and unique senders per day.

        Returns: Number of days with activity
        """
        cursor = self.connection.cursor()

        # Clear existing data
        cursor.execute("DELETE FROM daily_activity")

        # Get all emails grouped by date (skip NULL dates)
        cursor.execute("""
            SELECT 
                DATE(date) as day,
                COUNT(*) as message_count,
                COUNT(DISTINCT from_addr) as unique_senders
            FROM emails
            WHERE date IS NOT NULL
            GROUP BY DATE(date)
            ORDER BY day ASC
        """)

        day_count = 0
        for row in cursor.fetchall():
            day = row["day"]
            if day is None:  # Skip if date parsing failed
                continue
            message_count = row["message_count"]
            unique_senders = row["unique_senders"]

            cursor.execute(
                """
                INSERT INTO daily_activity (date, message_count, unique_senders)
                VALUES (?, ?, ?)
                """,
                (day, message_count, unique_senders),
            )
            day_count += 1

        self.connection.commit()
        return day_count

    def calculate_hourly_distribution(self) -> int:
        """
        Calculate message distribution by hour of day (0-23).

        Returns: Number of hours with activity (0-24)
        """
        cursor = self.connection.cursor()

        # Clear existing data
        cursor.execute("DELETE FROM hourly_distribution")

        # Get all emails grouped by hour (skip NULL dates)
        cursor.execute("""
            SELECT 
                CAST(strftime('%H', date) AS INTEGER) as hour,
                COUNT(*) as message_count,
                COUNT(DISTINCT from_addr) as unique_senders
            FROM emails
            WHERE date IS NOT NULL
            GROUP BY hour
            ORDER BY hour ASC
        """)

        hour_count = 0
        for row in cursor.fetchall():
            hour = row["hour"]
            if hour is None:  # Skip if hour parsing failed
                continue
            message_count = row["message_count"]
            unique_senders = row["unique_senders"]

            cursor.execute(
                """
                INSERT INTO hourly_distribution (hour, message_count, unique_senders)
                VALUES (?, ?, ?)
                """,
                (hour, message_count, unique_senders),
            )
            hour_count += 1

        self.connection.commit()
        return hour_count

    def calculate_thread_lifetimes(self) -> int:
        """
        Calculate lifetime of each thread (first to last message).

        Returns: Number of threads with lifetime calculated
        """
        cursor = self.connection.cursor()

        # Clear existing data
        cursor.execute("DELETE FROM thread_lifetimes")

        # Get thread info with first and last message dates
        cursor.execute("""
            SELECT 
                t.id as thread_id,
                MIN(e.date) as first_date,
                MAX(e.date) as last_date,
                COUNT(e.id) as message_count
            FROM threads t
            JOIN thread_members tm ON t.id = tm.thread_id
            JOIN emails e ON tm.email_id = e.id
            GROUP BY t.id
        """)

        thread_count = 0
        for row in cursor.fetchall():
            thread_id = row["thread_id"]
            first_date_str = row["first_date"]
            last_date_str = row["last_date"]
            message_count = row["message_count"]

            # Parse dates and calculate lifetime
            try:
                first_date = DateParser.parse_date(first_date_str)
                last_date = DateParser.parse_date(last_date_str)
                lifetime_seconds = int((last_date - first_date).total_seconds())
            except (ValueError, TypeError):
                continue

            cursor.execute(
                """
                INSERT INTO thread_lifetimes
                (thread_id, first_message_date, last_message_date, lifetime_seconds, message_count)
                VALUES (?, ?, ?, ?, ?)
                """,
                (thread_id, first_date_str, last_date_str, lifetime_seconds, message_count),
            )
            thread_count += 1

        self.connection.commit()
        return thread_count

    def get_daily_activity(self) -> List[Dict]:
        """
        Get daily message counts.

        Returns list of dicts with: date, message_count, unique_senders
        """
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT date, message_count, unique_senders
            FROM daily_activity
            ORDER BY date ASC
        """)

        activity = []
        for row in cursor.fetchall():
            activity.append({
                "date": row["date"],
                "message_count": row["message_count"],
                "unique_senders": row["unique_senders"],
            })
        return activity

    def get_hourly_distribution(self) -> List[Dict]:
        """
        Get hourly distribution of messages.

        Returns list of dicts with: hour (0-23), message_count, unique_senders
        """
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT hour, message_count, unique_senders
            FROM hourly_distribution
            ORDER BY hour ASC
        """)

        distribution = []
        for row in cursor.fetchall():
            distribution.append({
                "hour": row["hour"],
                "message_count": row["message_count"],
                "unique_senders": row["unique_senders"],
            })
        return distribution

    def get_thread_lifetimes(self, limit: int = 10, sort_by: str = "lifetime") -> List[Dict]:
        """
        Get thread lifetimes.

        Args:
            limit: Maximum number of threads to return
            sort_by: "lifetime" (longest first), "messages" (most messages first), "recent" (most recent first)

        Returns list of dicts with: thread_id, lifetime_seconds, lifetime_hours, lifetime_days, message_count
        """
        cursor = self.connection.cursor()

        # Determine sort order
        if sort_by == "messages":
            order_clause = "ORDER BY message_count DESC"
        elif sort_by == "recent":
            order_clause = "ORDER BY last_message_date DESC"
        else:  # lifetime
            order_clause = "ORDER BY lifetime_seconds DESC"

        cursor.execute(f"""
            SELECT 
                thread_id,
                first_message_date,
                last_message_date,
                lifetime_seconds,
                message_count
            FROM thread_lifetimes
            {order_clause}
            LIMIT ?
        """, (limit,))

        lifetimes = []
        for row in cursor.fetchall():
            lifetime_sec = row["lifetime_seconds"]
            lifetimes.append({
                "thread_id": row["thread_id"],
                "first_message_date": row["first_message_date"],
                "last_message_date": row["last_message_date"],
                "lifetime_seconds": lifetime_sec,
                "lifetime_hours": lifetime_sec / 3600,
                "lifetime_days": lifetime_sec / 86400,
                "message_count": row["message_count"],
            })
        return lifetimes

    def get_thread_lifetime_stats(self) -> Dict:
        """
        Get statistics on thread lifetimes.

        Returns dict with: avg_lifetime, median_lifetime, min_lifetime, max_lifetime, total_threads
        """
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT 
                COUNT(*) as total_threads,
                AVG(lifetime_seconds) as avg_lifetime,
                MIN(lifetime_seconds) as min_lifetime,
                MAX(lifetime_seconds) as max_lifetime
            FROM thread_lifetimes
        """)

        result = cursor.fetchone()
        if not result or result["total_threads"] == 0:
            return {
                "avg_lifetime_seconds": 0,
                "avg_lifetime_hours": 0,
                "avg_lifetime_days": 0,
                "median_lifetime_seconds": 0,
                "min_lifetime_seconds": 0,
                "max_lifetime_seconds": 0,
                "total_threads": 0,
            }

        total = result["total_threads"]
        avg_sec = result["avg_lifetime"] or 0
        min_sec = result["min_lifetime"] or 0
        max_sec = result["max_lifetime"] or 0

        # Calculate median
        cursor.execute("""
            SELECT lifetime_seconds FROM thread_lifetimes
            ORDER BY lifetime_seconds
            LIMIT 1 OFFSET ?
        """, (total // 2,))
        median_row = cursor.fetchone()
        median_sec = median_row["lifetime_seconds"] if median_row else 0

        return {
            "avg_lifetime_seconds": avg_sec,
            "avg_lifetime_hours": avg_sec / 3600,
            "avg_lifetime_days": avg_sec / 86400,
            "median_lifetime_seconds": median_sec,
            "median_lifetime_hours": median_sec / 3600,
            "median_lifetime_days": median_sec / 86400,
            "min_lifetime_seconds": min_sec,
            "max_lifetime_seconds": max_sec,
            "total_threads": total,
        }

    def get_daily_activity_summary(self) -> Dict:
        """
        Get summary statistics for daily activity.

        Returns dict with: total_messages, total_days, avg_per_day, max_day, min_day
        """
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT 
                SUM(message_count) as total_messages,
                COUNT(*) as total_days,
                AVG(message_count) as avg_per_day,
                MAX(message_count) as max_day,
                MIN(message_count) as min_day
            FROM daily_activity
        """)

        result = cursor.fetchone()
        if not result or result["total_days"] == 0:
            return {
                "total_messages": 0,
                "total_days": 0,
                "avg_per_day": 0,
                "max_day": 0,
                "min_day": 0,
            }

        return {
            "total_messages": result["total_messages"] or 0,
            "total_days": result["total_days"] or 0,
            "avg_per_day": result["avg_per_day"] or 0,
            "max_day": result["max_day"] or 0,
            "min_day": result["min_day"] or 0,
        }

    def get_hourly_activity_summary(self) -> Dict:
        """
        Get summary statistics for hourly distribution.

        Returns dict with: busiest_hour, quietest_hour, total_hours, avg_per_hour
        """
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT 
                COUNT(*) as total_hours,
                AVG(message_count) as avg_per_hour,
                MAX(message_count) as max_hour,
                MIN(message_count) as min_hour
            FROM hourly_distribution
        """)

        result = cursor.fetchone()
        if not result or result["total_hours"] == 0:
            return {
                "busiest_hour": None,
                "quietest_hour": None,
                "total_hours": 0,
                "avg_per_hour": 0,
            }

        # Get busiest hour
        cursor.execute("""
            SELECT hour FROM hourly_distribution
            ORDER BY message_count DESC
            LIMIT 1
        """)
        busiest = cursor.fetchone()
        busiest_hour = busiest["hour"] if busiest else None

        # Get quietest hour
        cursor.execute("""
            SELECT hour FROM hourly_distribution
            ORDER BY message_count ASC
            LIMIT 1
        """)
        quietest = cursor.fetchone()
        quietest_hour = quietest["hour"] if quietest else None

        return {
            "busiest_hour": busiest_hour,
            "quietest_hour": quietest_hour,
            "total_hours": result["total_hours"] or 0,
            "avg_per_hour": result["avg_per_hour"] or 0,
            "max_hour_count": result["max_hour"] or 0,
            "min_hour_count": result["min_hour"] or 0,
        }
