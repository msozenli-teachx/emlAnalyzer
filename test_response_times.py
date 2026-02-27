#!/usr/bin/env python3
"""Test response time calculations with timezone-aware dates."""

import sys
import os
from pathlib import Path

# Add the eml_analyzer module to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from eml_analyzer.database import Database
from eml_analyzer.importer import EMLImporter
from eml_analyzer.threads import ThreadManager
from eml_analyzer.dateutil import DateParser
from datetime import datetime, timezone, timedelta


def test_response_times():
    """Test the complete response time workflow."""
    # Clean up any existing database
    db_path = "test_response_times.db"
    if Path(db_path).exists():
        Path(db_path).unlink()

    print("=" * 80)
    print("RESPONSE TIME ANALYSIS TEST")
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
    if duplicates > 0:
        print(f"   ⊘ Duplicates skipped: {duplicates}")

    # Test timezone-aware date parsing
    print("\n3. Testing timezone-aware date parsing...")
    test_dates = [
        "Mon, 20 Jan 2024 14:30:00 +0500",  # UTC+5
        "Mon, 20 Jan 2024 22:15:00 -0800",  # UTC-8 (Pacific)
        "2024-01-01T18:00:00",              # ISO format
    ]

    for date_str in test_dates:
        try:
            parsed = DateParser.parse_date(date_str)
            print(f"   ✓ Parsed: {date_str}")
            print(f"     → UTC: {parsed.isoformat()}")
        except ValueError as e:
            print(f"   ✗ Failed to parse: {date_str} - {e}")

    # Reconstruct threads
    print("\n4. Reconstructing threads...")
    tm = ThreadManager(db.connection)
    thread_count, orphaned_count = tm.reconstruct_threads()
    print(f"   ✓ Threads created: {thread_count}")

    # Calculate response times
    print("\n5. Calculating response times...")
    response_count = tm.calculate_response_times()
    print(f"   ✓ Response times calculated: {response_count}")

    # Get overall average response time
    print("\n6. Overall response time statistics...")
    overall_stats = tm.get_overall_average_response_time()
    if overall_stats["total_replies"] > 0:
        print(f"   Total replies analyzed: {overall_stats['total_replies']}")
        print(f"   Average response time: {DateParser.format_duration(overall_stats['avg_seconds'])}")
        print(f"   Median response time:  {DateParser.format_duration(overall_stats['median_seconds'])}")
        print(f"   Fastest response:      {DateParser.format_duration(overall_stats['min_seconds'])}")
        print(f"   Slowest response:      {DateParser.format_duration(overall_stats['max_seconds'])}")
    else:
        print("   No response times found")

    # Get average response time by user
    print("\n7. Average response time by user (as replier)...")
    by_user = tm.get_average_response_time_by_user(limit=5)
    if by_user:
        for user in by_user:
            duration = DateParser.format_duration(user["avg_seconds"])
            print(f"   {user['replier']:<30} {duration:<25} ({user['reply_count']} replies)")
    else:
        print("   No data available")

    # Get average response time to user
    print("\n8. Average response time to user (how quickly they get replies)...")
    to_user = tm.get_average_response_time_to_user(limit=5)
    if to_user:
        for user in to_user:
            duration = DateParser.format_duration(user["avg_seconds"])
            print(f"   {user['original_sender']:<30} {duration:<25} ({user['reply_count']} replies)")
    else:
        print("   No data available")

    # Test timezone calculations
    print("\n9. Testing timezone-aware calculations...")
    cursor = db.connection.cursor()

    # Get a sample of response times
    cursor.execute("""
        SELECT rt.replier, rt.original_sender, rt.response_seconds,
               e1.date as reply_date, e2.date as original_date
        FROM response_times rt
        JOIN emails e1 ON rt.reply_email_id = e1.id
        JOIN emails e2 ON rt.original_email_id = e2.id
        LIMIT 3
    """)

    samples = cursor.fetchall()
    if samples:
        for sample in samples:
            print(f"   Reply from: {sample['replier']}")
            print(f"   To:         {sample['original_sender']}")
            print(f"   Response time: {DateParser.format_duration(sample['response_seconds'])}")
            print(f"   Original: {sample['original_date']}")
            print(f"   Reply:    {sample['reply_date']}")
            print()
    else:
        print("   No response time samples found")

    # Test duration formatting
    print("\n10. Testing duration formatting...")
    test_durations = [
        (60, "1 minute"),
        (3600, "1 hour"),
        (86400, "1 day"),
        (172800, "2 days"),
        (90061, "1 day, 1 hour, 1 minute, and 1 second"),
    ]

    for seconds, expected_contains in test_durations:
        formatted = DateParser.format_duration(seconds)
        print(f"   {seconds}s → {formatted}")

    # Verify no negative response times
    print("\n11. Verifying data integrity...")
    cursor.execute("""
        SELECT COUNT(*) as count FROM response_times
        WHERE response_seconds < 0
    """)
    negative_count = cursor.fetchone()["count"]
    if negative_count == 0:
        print("   ✓ No negative response times found")
    else:
        print(f"   ✗ Found {negative_count} negative response times")

    # Check for orphaned calculations
    cursor.execute("""
        SELECT COUNT(*) as count FROM response_times
        WHERE reply_email_id NOT IN (SELECT id FROM emails)
        OR original_email_id NOT IN (SELECT id FROM emails)
    """)
    orphaned_count = cursor.fetchone()["count"]
    if orphaned_count == 0:
        print("   ✓ All response times linked to valid emails")
    else:
        print(f"   ✗ Found {orphaned_count} orphaned response times")

    # Clean up
    db.close()
    Path(db_path).unlink()

    print("\n" + "=" * 80)
    print("✓ ALL RESPONSE TIME TESTS COMPLETED!")
    print("=" * 80)


if __name__ == "__main__":
    test_response_times()
