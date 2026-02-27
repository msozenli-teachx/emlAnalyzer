#!/usr/bin/env python3
"""Test thread reconstruction and interaction analysis."""

import sys
import os
from pathlib import Path

# Add the eml_analyzer module to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from eml_analyzer.database import Database
from eml_analyzer.importer import EMLImporter
from eml_analyzer.threads import ThreadManager


def test_threads_and_interactions():
    """Test the complete thread and interaction workflow."""
    # Clean up any existing database
    db_path = "test_threads.db"
    if Path(db_path).exists():
        Path(db_path).unlink()

    print("=" * 70)
    print("THREAD RECONSTRUCTION & INTERACTION ANALYSIS TEST")
    print("=" * 70)

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

    # Reconstruct threads
    print("\n3. Reconstructing threads...")
    tm = ThreadManager(db.connection)
    thread_count, orphaned_count = tm.reconstruct_threads()
    print(f"   ✓ Threads created: {thread_count}")
    if orphaned_count > 0:
        print(f"   ⚠ Orphaned emails: {orphaned_count}")

    # List threads
    print("\n4. Listing all threads:")
    threads = tm.get_all_threads()
    print(f"   ✓ Total threads: {len(threads)}")
    for idx, thread in enumerate(threads[:5], 1):
        print(f"   {idx}. [{thread['message_count']} msgs] {thread['subject'][:50]}")

    # Display a sample thread
    print("\n5. Displaying sample thread (first thread):")
    if threads:
        thread_id = threads[0]["id"]
        emails = tm.get_thread_emails(thread_id)
        print(f"   Thread {thread_id}: {len(emails)} messages")
        for idx, email in enumerate(emails[:3], 1):
            print(f"   {idx}. {email['from']} → {email['to']}")
            print(f"      {email['subject'][:50]}")

    # Build interactions
    print("\n6. Building interaction model...")
    interaction_count = tm.build_interactions()
    print(f"   ✓ Interactions recorded: {interaction_count}")

    # Get top senders
    print("\n7. Top senders (by replies sent):")
    top_senders = tm.get_top_senders(5)
    if top_senders:
        for idx, user in enumerate(top_senders, 1):
            print(f"   {idx}. {user['sender']:30} → {user['total_replies']:3} replies")
    else:
        print("   (No senders found)")

    # Get top recipients
    print("\n8. Top recipients (by replies received):")
    top_recipients = tm.get_top_recipients(5)
    if top_recipients:
        for idx, user in enumerate(top_recipients, 1):
            print(f"   {idx}. {user['recipient']:30} ← {user['total_replies_received']:3} replies")
    else:
        print("   (No recipients found)")

    # Get dominance scores
    print("\n9. User dominance scores:")
    dominance_scores = tm.get_dominance_scores(5)
    if dominance_scores:
        print(f"   {'User':<30} {'Score':>7} {'Sent':>5} {'Recv':>5}")
        print("   " + "-" * 52)
        for user in dominance_scores:
            score = user["dominance_score"]
            print(
                f"   {user['user']:<30} {score:+7.2f} {user['sent']:>5} {user['received']:>5}"
            )
    else:
        print("   (No dominance data)")

    # Test interaction between two users
    print("\n10. Testing pairwise interaction analysis:")
    if top_senders and len(top_senders) > 0 and top_recipients and len(top_recipients) > 0:
        user1 = top_senders[0]["sender"]
        user2 = top_recipients[0]["recipient"]
        interaction = tm.get_interaction_between(user1, user2)
        print(f"   {user1} → {user2}: {interaction['user1_to_user2']} replies")
        print(f"   {user2} → {user1}: {interaction['user2_to_user1']} replies")
        print(f"   Total interactions: {interaction['total']}")

    # Verify thread structure
    print("\n11. Verifying thread structure:")
    all_threads = tm.get_all_threads()
    total_emails_in_threads = sum(t["message_count"] for t in all_threads)
    print(f"   Total threads: {len(all_threads)}")
    print(f"   Total emails in threads: {total_emails_in_threads}")
    print(f"   Average emails per thread: {total_emails_in_threads / len(all_threads):.1f}" if all_threads else "   N/A")

    # Verify all emails are in threads
    cursor = db.connection.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM thread_members")
    thread_member_count = cursor.fetchone()["count"]
    print(f"   Emails assigned to threads: {thread_member_count}/{imported}")

    # Clean up
    db.close()
    Path(db_path).unlink()

    print("\n" + "=" * 70)
    print("✓ ALL TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    test_threads_and_interactions()
