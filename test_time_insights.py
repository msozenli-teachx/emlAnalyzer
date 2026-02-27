#!/usr/bin/env python3
"""Test time-based insights (daily activity, hourly distribution, thread lifetimes)."""

import sys
import os
from pathlib import Path

# Add the eml_analyzer module to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from eml_analyzer.database import Database
from eml_analyzer.importer import EMLImporter
from eml_analyzer.threads import ThreadManager
from eml_analyzer.dateutil import DateParser


def test_time_insights():
    """Test time-based insights."""
    # Clean up any existing database
    db_path = "test_time_insights.db"
    if Path(db_path).exists():
        Path(db_path).unlink()

    print("=" * 80)
    print("TIME-BASED INSIGHTS TEST")
    print("=" * 80)

    # Initialize database
    print("\n1. Initializing database...")
    db = Database(db_path)
    print("   ✓ Database initialized")

    # Import emails
    print("\n2. Importing EML files from data/sample_emails/...")
    importer = EMLImporter(db)
    imported, duplicates = importer.import_from_directory("data/sample_emails")
    print(f"   ✓ Imported: {imported} emails")

    # Reconstruct threads
    print("\n3. Reconstructing threads...")
    tm = ThreadManager(db.connection)
    thread_count, orphaned_count = tm.reconstruct_threads()
    print(f"   ✓ Threads created: {thread_count}")

    # Calculate daily activity
    print("\n4. Calculating daily activity...")
    days = tm.calculate_daily_activity()
    print(f"   ✓ Daily activity calculated: {days} days")

    # Get daily activity
    print("\n5. Daily activity summary...")
    activity = tm.get_daily_activity()
    summary = tm.get_daily_activity_summary()
    if activity:
        print(f"   Total messages: {summary['total_messages']}")
        print(f"   Total days: {summary['total_days']}")
        print(f"   Average per day: {summary['avg_per_day']:.1f}")
        print(f"   Peak day: {summary['max_day']} messages")
        print(f"   Slowest day: {summary['min_day']} messages")
        print(f"   Sample days:")
        for day in activity[:3]:
            print(f"     {day['date']}: {day['message_count']} messages, {day['unique_senders']} senders")

    # Calculate hourly distribution
    print("\n6. Calculating hourly distribution...")
    hours = tm.calculate_hourly_distribution()
    print(f"   ✓ Hourly distribution calculated: {hours} hours")

    # Get hourly distribution
    print("\n7. Hourly distribution summary...")
    distribution = tm.get_hourly_distribution()
    hour_summary = tm.get_hourly_activity_summary()
    if distribution:
        print(f"   Total hours with activity: {hour_summary['total_hours']}")
        print(f"   Average per hour: {hour_summary['avg_per_hour']:.1f}")
        if hour_summary['busiest_hour'] is not None:
            print(f"   Busiest hour: {hour_summary['busiest_hour']:02d}:00 ({hour_summary['max_hour_count']} messages)")
            print(f"   Quietest hour: {hour_summary['quietest_hour']:02d}:00 ({hour_summary['min_hour_count']} messages)")
        print(f"   Sample hours:")
        for hour_data in distribution[:3]:
            hour = hour_data["hour"]
            print(f"     {hour:02d}:00: {hour_data['message_count']} messages, {hour_data['unique_senders']} senders")

    # Calculate thread lifetimes
    print("\n8. Calculating thread lifetimes...")
    threads = tm.calculate_thread_lifetimes()
    print(f"   ✓ Thread lifetimes calculated: {threads} threads")

    # Get thread lifetime stats
    print("\n9. Thread lifetime statistics...")
    lifetime_stats = tm.get_thread_lifetime_stats()
    print(f"   Total threads: {lifetime_stats['total_threads']}")
    print(f"   Average lifetime: {DateParser.format_duration(lifetime_stats['avg_lifetime_seconds'])}")
    print(f"   Median lifetime: {DateParser.format_duration(lifetime_stats['median_lifetime_seconds'])}")
    print(f"   Longest thread: {DateParser.format_duration(lifetime_stats['max_lifetime_seconds'])}")
    print(f"   Shortest thread: {DateParser.format_duration(lifetime_stats['min_lifetime_seconds'])}")

    # Get thread lifetimes sorted by duration
    print("\n10. Longest threads (by lifetime)...")
    lifetimes = tm.get_thread_lifetimes(limit=5, sort_by="lifetime")
    for thread in lifetimes:
        duration = DateParser.format_duration(thread["lifetime_seconds"])
        print(f"   Thread {thread['thread_id']}: {duration} ({thread['message_count']} messages)")

    # Get thread lifetimes sorted by message count
    print("\n11. Threads with most messages...")
    lifetimes_by_msg = tm.get_thread_lifetimes(limit=5, sort_by="messages")
    for thread in lifetimes_by_msg:
        print(f"   Thread {thread['thread_id']}: {thread['message_count']} messages ({DateParser.format_duration(thread['lifetime_seconds'])})")

    # Verify data integrity
    print("\n12. Verifying data integrity...")
    cursor = db.connection.cursor()
    
    cursor.execute("SELECT COUNT(*) as count FROM daily_activity")
    daily_count = cursor.fetchone()["count"]
    print(f"   ✓ Daily activity records: {daily_count}")

    cursor.execute("SELECT COUNT(*) as count FROM hourly_distribution")
    hourly_count = cursor.fetchone()["count"]
    print(f"   ✓ Hourly distribution records: {hourly_count}")

    cursor.execute("SELECT COUNT(*) as count FROM thread_lifetimes")
    lifetime_count = cursor.fetchone()["count"]
    print(f"   ✓ Thread lifetime records: {lifetime_count}")

    # Check for negative lifetimes
    cursor.execute("SELECT COUNT(*) as count FROM thread_lifetimes WHERE lifetime_seconds < 0")
    negative_count = cursor.fetchone()["count"]
    if negative_count == 0:
        print(f"   ✓ No negative thread lifetimes")
    else:
        print(f"   ✗ Found {negative_count} negative thread lifetimes")

    # Clean up
    db.close()
    Path(db_path).unlink()

    print("\n" + "=" * 80)
    print("✓ ALL TIME-BASED INSIGHTS TESTS COMPLETED!")
    print("=" * 80)


if __name__ == "__main__":
    test_time_insights()
