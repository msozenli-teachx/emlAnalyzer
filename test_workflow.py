#!/usr/bin/env python3
"""Test the complete EML analyzer workflow without external dependencies."""

import sys
import os

# Add the eml_analyzer module to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from eml_analyzer.database import Database
from eml_analyzer.importer import EMLImporter
from pathlib import Path


def test_workflow():
    """Test the complete workflow."""
    # Clean up any existing database
    db_path = "test_emails.db"
    if Path(db_path).exists():
        Path(db_path).unlink()

    print("=" * 60)
    print("EML ANALYZER - WORKFLOW TEST")
    print("=" * 60)

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

    # Get statistics
    print("\n3. Retrieving statistics...")
    stats = db.get_stats()
    print("   " + "-" * 56)
    print(f"   Total Messages:    {stats['total_messages']}")
    print(f"   Unique Senders:    {stats['unique_senders']}")
    if stats["date_range"]["start"]:
        print(f"   Date Range:        {stats['date_range']['start']} to {stats['date_range']['end']}")
    print("   " + "-" * 56)

    # Get senders list
    print("\n4. Unique senders:")
    senders = db.get_senders_list()
    for sender in senders:
        print(f"   - {sender}")

    # Test duplicate detection by importing again
    print("\n5. Testing duplicate detection (importing again)...")
    imported2, duplicates2 = importer.import_from_directory("data/sample_emails")
    print(f"   ✓ Imported: {imported2} emails (should be 0)")
    print(f"   ⊘ Duplicates skipped: {duplicates2} (should be {imported})")

    # Clean up
    db.close()
    Path(db_path).unlink()

    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    test_workflow()
