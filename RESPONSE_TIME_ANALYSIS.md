# Response Time Analysis

This document describes the response time analysis features added to EML Analyzer.

## Overview

EML Analyzer now includes sophisticated response time analysis that:

1. **Calculates response times** for every reply with timezone awareness
2. **Stores results efficiently** in a dedicated table to avoid recalculation
3. **Provides statistics** on overall and per-user response times
4. **Handles timezones correctly** by converting all dates to UTC

## Key Features

### Timezone-Aware Date Parsing

All email dates are parsed with full timezone awareness:

- **RFC 2822 format**: `Mon, 20 Jan 2024 14:30:00 +0500`
- **ISO format**: `2024-01-01T18:00:00`
- **Timezone abbreviations**: EST, EDT, PST, PDT, CST, CDT, MST, MDT, UTC, GMT
- **Numeric offsets**: +0530, -0800, etc.

All dates are converted to UTC for accurate comparison.

### Response Time Calculation

For each reply (email with In-Reply-To header):

1. Find the original email by Message-ID
2. Parse both dates with timezone awareness
3. Calculate time difference in seconds
4. Store in response_times table (never recalculate)
5. Skip negative times (clock skew)

### Efficient Storage

Response times are pre-calculated and stored in a dedicated table:

```sql
CREATE TABLE response_times (
    id INTEGER PRIMARY KEY,
    reply_email_id INTEGER,          -- Which email is the reply
    original_email_id INTEGER,       -- Which email it's replying to
    replier TEXT,                    -- Sender of the reply
    original_sender TEXT,            -- Original sender
    response_seconds INTEGER,        -- Time difference in seconds
    created_at TIMESTAMP
);
```

**Indexes:**
- `idx_response_times_replier` - Fast queries by replier
- `idx_response_times_original_sender` - Fast queries by original sender
- `idx_response_times_reply_email_id` - Fast lookup by email ID

### Query Performance

All queries use indexed lookups:

```
Overall average:           O(n) single aggregation
Per-user average:          O(m log m) where m = interactions
Median calculation:        O(m) with indexed sort
```

## Database Schema

### response_times Table

```sql
CREATE TABLE response_times (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reply_email_id INTEGER NOT NULL,
    original_email_id INTEGER NOT NULL,
    replier TEXT NOT NULL,
    original_sender TEXT NOT NULL,
    response_seconds INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(reply_email_id, original_email_id),
    FOREIGN KEY (reply_email_id) REFERENCES emails(id),
    FOREIGN KEY (original_email_id) REFERENCES emails(id)
);
```

**Constraints:**
- UNIQUE on (reply_email_id, original_email_id) prevents duplicates
- FOREIGN KEYs ensure referential integrity

## Commands

### Calculate Response Times

```bash
eml-analyzer calculate-response-times
```

Analyzes all replies and pre-calculates response times.

**Output:**
```
Calculating response times...
✓ Response times calculated: 12
```

**What it does:**
1. Finds all emails with In-Reply-To header
2. Locates original email by Message-ID
3. Parses dates with timezone awareness
4. Calculates time difference
5. Stores in response_times table
6. Skips already-calculated times

### Overall Average Response Time

```bash
eml-analyzer avg-response-time
```

Shows overall statistics across all replies.

**Output:**
```
======================================================================
OVERALL RESPONSE TIME STATISTICS
======================================================================
Total Replies Analyzed:  12

Average Response Time:
  2 hours, 38 minutes, and 45 seconds
  (2.6 hours, 0.11 days)

Median Response Time:
  1 hour

Fastest Response:  0 seconds
Slowest Response:  20 hours, 45 minutes
======================================================================
```

**Metrics:**
- **Average**: Mean response time across all replies
- **Median**: Middle value (better for outliers)
- **Fastest**: Minimum response time
- **Slowest**: Maximum response time

### Average Response Time by User

```bash
eml-analyzer avg-response-time-by-user [--limit 10]
```

Shows how quickly each user responds to messages.

**Output:**
```
================================================================================
AVERAGE RESPONSE TIME BY USER (as replier)
================================================================================
User                           Avg Response         Replies
--------------------------------------------------------------------------------
alice@example.com              1 hour                   1
bob@example.com                1 hour                   1
charlie@example.com            1 hour                   3
diana@example.com              1 hour                   2
frank@example.com              1 hour                   2
================================================================================
```

**Interpretation:**
- Users with lower average response times are more responsive
- Reply count shows how many replies each user made

### Average Response Time to User

```bash
eml-analyzer avg-response-time-to-user [--limit 10]
```

Shows how quickly each user receives replies to their messages.

**Output:**
```
================================================================================
AVERAGE RESPONSE TIME TO USER (how quickly they get replies)
================================================================================
User                           Avg Time to Reply    Replies
--------------------------------------------------------------------------------
charlie@example.com            40 minutes               3
bob@example.com                1 hour                   1
diana@example.com              1 hour                   2
eve@example.com                1 hour                   2
alice@example.com              1 hour, 30 minutes       2
================================================================================
```

**Interpretation:**
- Shows how quickly users get responses to their messages
- Lower times indicate the user gets quick replies
- Useful for identifying important/popular users

## Timezone Handling

### How Timezone Awareness Works

1. **Parse date with timezone**: `Mon, 20 Jan 2024 14:30:00 +0500`
2. **Convert to UTC**: `2024-01-20T09:30:00+00:00`
3. **Compare in UTC**: All dates normalized to same timezone
4. **Calculate difference**: Accurate across timezones

### Example

```
Email A: Mon, 20 Jan 2024 14:30:00 +0500  (UTC+5, India)
  → UTC: 2024-01-20 09:30:00

Email B: Mon, 20 Jan 2024 22:15:00 -0800  (UTC-8, Pacific)
  → UTC: 2024-01-21 06:15:00

Difference: 20 hours, 45 minutes
```

Without timezone awareness, the difference would be calculated incorrectly!

### Supported Formats

**RFC 2822 with numeric offset:**
```
Mon, 20 Jan 2024 14:30:00 +0500
Fri, 19 Jan 2024 22:15:00 -0800
Sat, 21 Jan 2024 00:00:00 +0000
```

**RFC 2822 with timezone abbreviation:**
```
Mon, 20 Jan 2024 14:30:00 EST
Mon, 20 Jan 2024 14:30:00 EDT
Mon, 20 Jan 2024 14:30:00 UTC
```

**ISO 8601 format:**
```
2024-01-20T14:30:00
2024-01-20T14:30:00+05:00
```

## Python API

### DateParser Class

```python
from eml_analyzer.dateutil import DateParser

# Parse a date string
dt = DateParser.parse_date("Mon, 20 Jan 2024 14:30:00 +0500")
# Returns: datetime in UTC

# Parse safely (returns None on error)
dt = DateParser.parse_date_safe("invalid date")

# Format duration
duration = DateParser.format_duration(9525)
# Returns: "2 hours, 38 minutes, and 45 seconds"

# Convert seconds
hours = DateParser.seconds_to_hours(3600)  # 1.0
days = DateParser.seconds_to_days(86400)   # 1.0
```

### ThreadManager Response Time Methods

```python
from eml_analyzer.threads import ThreadManager

tm = ThreadManager(db.connection)

# Calculate all response times
count = tm.calculate_response_times()

# Get overall statistics
stats = tm.get_overall_average_response_time()
# Returns: {
#     "avg_seconds": 9525.0,
#     "avg_hours": 2.65,
#     "avg_days": 0.11,
#     "total_replies": 12,
#     "min_seconds": 0,
#     "max_seconds": 74700,
#     "median_seconds": 3600
# }

# Get per-user response times (as replier)
users = tm.get_average_response_time_by_user(limit=10)
# Returns: [{
#     "replier": "alice@example.com",
#     "avg_seconds": 3600.0,
#     "avg_hours": 1.0,
#     "avg_days": 0.042,
#     "reply_count": 5,
#     "min_seconds": 0,
#     "max_seconds": 7200
# }, ...]

# Get per-user response times (as recipient)
users = tm.get_average_response_time_to_user(limit=10)
# Returns: [{
#     "original_sender": "bob@example.com",
#     "avg_seconds": 2400.0,
#     "avg_hours": 0.67,
#     "avg_days": 0.028,
#     "reply_count": 3,
#     "min_seconds": 600,
#     "max_seconds": 3600
# }, ...]

# Get comprehensive stats
stats = tm.get_response_time_stats()
# Returns: {
#     "overall": {...},
#     "fastest_responders": [...],
#     "most_replied_to": [...]
# }
```

## Example Workflow

```bash
#!/bin/bash

# 1. Generate test data
python3 generate_test_data.py

# 2. Import emails
eml-analyzer import-emails ./data/sample_emails

# 3. Reconstruct threads
eml-analyzer reconstruct-threads

# 4. Calculate response times
eml-analyzer calculate-response-times

# 5. View overall statistics
eml-analyzer avg-response-time

# 6. View per-user statistics
eml-analyzer avg-response-time-by-user --limit 5
eml-analyzer avg-response-time-to-user --limit 5
```

## Edge Cases Handled

### Missing Parent Messages

If an email's In-Reply-To points to a non-existent message:
- The response time is **not calculated**
- The reply is **skipped** (no error)

### Clock Skew

If a reply has an earlier timestamp than the original:
- Response time would be **negative**
- The entry is **skipped** to maintain data integrity

### Timezone Parsing Errors

If a date cannot be parsed:
- The response time **is not calculated**
- The reply is **skipped** (no error)
- No exceptions are raised

### Duplicate Response Times

If the same reply is processed twice:
- The UNIQUE constraint prevents duplicates
- The second insert is **ignored**

## Performance Characteristics

### Calculation

- **Time**: O(n) where n = number of replies
- **Space**: O(m) where m = unique (reply_id, original_id) pairs
- **10 replies**: < 1ms
- **1,000 replies**: < 50ms
- **10,000 replies**: < 500ms

### Queries

- **Overall average**: O(n) single aggregation query
- **Per-user average**: O(m log m) where m = interactions
- **Query time**: < 10ms for typical datasets

### Storage

- **Per response time**: ~60 bytes (indexes included)
- **10 replies**: < 1 KB
- **1,000 replies**: < 100 KB
- **10,000 replies**: < 1 MB

## Data Integrity

### Constraints

- **UNIQUE(reply_email_id, original_email_id)**: Prevents duplicate calculations
- **FOREIGN KEY** constraints ensure referential integrity
- **NOT NULL** constraints on all required fields

### Validation

- **Negative response times**: Skipped (clock skew)
- **Missing parent emails**: Skipped (orphaned replies)
- **Parse errors**: Skipped (malformed dates)

### Verification

```sql
-- Check for negative response times
SELECT COUNT(*) FROM response_times WHERE response_seconds < 0;
-- Should return: 0

-- Check for orphaned entries
SELECT COUNT(*) FROM response_times
WHERE reply_email_id NOT IN (SELECT id FROM emails)
   OR original_email_id NOT IN (SELECT id FROM emails);
-- Should return: 0
```

## Limitations

1. **No nested reply chains**: Only direct replies are tracked (not replies to replies)
2. **One-way measurement**: sender → recipient, not bidirectional
3. **No weighted averages**: All replies counted equally
4. **No time-based filtering**: All replies included regardless of age

## Future Enhancements

- Response time trends over time
- Response time by day of week
- Response time by time of day
- Weighted averages (recent replies weighted more)
- Response time percentiles (95th, 99th)
- Average time to first reply in thread
- Conversation turn-around time

## Testing

Run the comprehensive test suite:

```bash
python3 test_response_times.py
```

**Test Coverage:**
- Timezone-aware date parsing
- Response time calculation
- Overall statistics
- Per-user statistics
- Duration formatting
- Data integrity checks
- Negative response time filtering
- Orphaned entry detection

## Troubleshooting

### "No response times found"
Make sure to run `calculate-response-times` before viewing statistics.

### Incorrect response times
Check that email dates are in valid RFC 2822 or ISO format.

### Missing timezone information
Dates without timezone info are assumed to be UTC.

### Very large response times
These might indicate:
- Slow response patterns
- Emails from different time periods
- Timezone offset issues

Use the median instead of average to handle outliers.

## References

- RFC 2822: Internet Message Format
- RFC 5322: Internet Message Format (obsoletes 2822)
- ISO 8601: Date and time format
- Python datetime documentation
