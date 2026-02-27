#!/usr/bin/env python3
"""Generate realistic test EML dataset for testing."""

from pathlib import Path
from datetime import datetime, timedelta
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def generate_eml_dataset(output_dir: str = "data/sample_emails"):
    """Generate a realistic EML dataset with 25+ emails."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Base date for deterministic generation
    base_date = datetime(2024, 1, 1, 9, 0, 0)

    # Define email participants
    participants = [
        "alice@example.com",
        "bob@example.com",
        "charlie@example.com",
        "diana@example.com",
        "eve@example.com",
        "frank@example.com",
    ]

    emails_data = []

    # 1-5: Initial emails from different senders
    for i in range(5):
        sender = participants[i % len(participants)]
        recipient = participants[(i + 1) % len(participants)]
        msg_id = f"<msg{i+1:03d}@example.com>"
        date = base_date + timedelta(days=i, hours=9)

        emails_data.append({
            "from": sender,
            "to": recipient,
            "subject": f"Initial Discussion Topic {i+1}",
            "message_id": msg_id,
            "in_reply_to": None,
            "date": date.isoformat(),
            "body": f"This is the initial message {i+1} starting a new discussion.",
        })

    # 6-15: Reply chain (multi-level replies)
    base_msg_id = "<msg006@example.com>"
    for i in range(10):
        sender = participants[(i + 2) % len(participants)]
        recipient = participants[(i + 3) % len(participants)]
        msg_id = f"<msg{i+6:03d}@example.com>"
        date = base_date + timedelta(days=5, hours=9 + i)
        in_reply_to = base_msg_id if i == 0 else f"<msg{i+5:03d}@example.com>"

        emails_data.append({
            "from": sender,
            "to": recipient,
            "subject": f"Re: Multi-level Reply Chain",
            "message_id": msg_id,
            "in_reply_to": in_reply_to,
            "date": date.isoformat(),
            "body": f"Reply {i+1} in the conversation chain.",
        })

    # 16-20: Emails with missing Message-ID
    for i in range(5):
        sender = participants[i % len(participants)]
        recipient = participants[(i + 2) % len(participants)]
        date = base_date + timedelta(days=10 + i, hours=14)

        emails_data.append({
            "from": sender,
            "to": recipient,
            "subject": f"Email without Message-ID {i+1}",
            "message_id": None,  # Missing Message-ID
            "in_reply_to": None,
            "date": date.isoformat(),
            "body": f"This email has no Message-ID header (edge case {i+1}).",
        })

    # 21-23: Duplicate entries (same from, to, subject, date)
    dup_date = base_date + timedelta(days=15)
    for i in range(3):
        emails_data.append({
            "from": "alice@example.com",
            "to": "bob@example.com",
            "subject": "Duplicate Message Test",
            "message_id": f"<dup{i+1}@example.com>" if i > 0 else "<original_dup@example.com>",
            "in_reply_to": None,
            "date": dup_date.isoformat(),
            "body": "This message is intentionally duplicated for testing.",
        })

    # 24-25: Mixed timezones
    emails_data.append({
        "from": "frank@example.com",
        "to": "eve@example.com",
        "subject": "Email from UTC+5 timezone",
        "message_id": "<tz_utc5@example.com>",
        "in_reply_to": None,
        "date": "Mon, 20 Jan 2024 14:30:00 +0500",
        "body": "This email is from UTC+5 timezone.",
    })

    emails_data.append({
        "from": "eve@example.com",
        "to": "frank@example.com",
        "subject": "Email from UTC-8 timezone",
        "message_id": "<tz_utc8@example.com>",
        "in_reply_to": "<tz_utc5@example.com>",
        "date": "Mon, 20 Jan 2024 22:15:00 -0800",
        "body": "This email is from UTC-8 timezone (Pacific).",
    })

    # 26: Email with special characters in subject
    emails_data.append({
        "from": "charlie@example.com",
        "to": "diana@example.com",
        "subject": "Special chars: 你好 🎉 [TEST] (FW: Original)",
        "message_id": "<special_chars@example.com>",
        "in_reply_to": None,
        "date": (base_date + timedelta(days=18)).isoformat(),
        "body": "Email with special characters in the subject line.",
    })

    # 27: Very long subject line
    emails_data.append({
        "from": "diana@example.com",
        "to": "charlie@example.com",
        "subject": "This is an extremely long subject line that contains a lot of information and goes on and on and on to test how the system handles very verbose email subjects in the database",
        "message_id": "<long_subject@example.com>",
        "in_reply_to": None,
        "date": (base_date + timedelta(days=19)).isoformat(),
        "body": "Email with a very long subject line.",
    })

    # 28: Email with no subject
    emails_data.append({
        "from": "bob@example.com",
        "to": "alice@example.com",
        "subject": "",
        "message_id": "<no_subject@example.com>",
        "in_reply_to": None,
        "date": (base_date + timedelta(days=20)).isoformat(),
        "body": "This email has no subject line.",
    })

    # 29: Complex reply chain with multiple recipients
    emails_data.append({
        "from": "alice@example.com",
        "to": "bob@example.com, charlie@example.com",
        "subject": "Team Discussion",
        "message_id": "<team_disc@example.com>",
        "in_reply_to": None,
        "date": (base_date + timedelta(days=21)).isoformat(),
        "body": "Discussion with multiple recipients.",
    })

    # 30: Reply to the team discussion
    emails_data.append({
        "from": "charlie@example.com",
        "to": "alice@example.com, bob@example.com",
        "subject": "Re: Team Discussion",
        "message_id": "<team_disc_reply@example.com>",
        "in_reply_to": "<team_disc@example.com>",
        "date": (base_date + timedelta(days=21, hours=2)).isoformat(),
        "body": "Reply to team discussion.",
    })

    # Write EML files
    for idx, email_data in enumerate(emails_data, 1):
        msg = MIMEText(email_data["body"])
        msg["From"] = email_data["from"]
        msg["To"] = email_data["to"]
        msg["Subject"] = email_data["subject"]
        msg["Date"] = email_data["date"]

        if email_data["message_id"]:
            msg["Message-ID"] = email_data["message_id"]

        if email_data["in_reply_to"]:
            msg["In-Reply-To"] = email_data["in_reply_to"]

        # Write to file
        filename = f"{idx:03d}_email.eml"
        filepath = output_path / filename

        with open(filepath, "w") as f:
            f.write(msg.as_string())

        print(f"Generated: {filename} - {email_data['subject'][:50]}")

    print(f"\n✓ Generated {len(emails_data)} test emails in {output_dir}/")


if __name__ == "__main__":
    generate_eml_dataset()
