# Time-Based Insights Feature

## Overview

The Time-Based Insights feature adds temporal analysis capabilities to the EML Analyzer, allowing you to understand email communication patterns over time. This includes daily activity tracking, hourly distribution analysis, and thread lifetime calculations.

## Features

### 1. Daily Activity Analysis

Track the number of messages sent per day and the unique senders contributing to each day's activity.

**What it measures:**
- Message count per day
- Number of unique senders per day
- Peak activity days
- Quietest days
- Average daily message volume

**Use cases:**
- Identify communication peaks and valleys
- Understand team productivity patterns
- Plan for high-volume periods
- Detect anomalies in communication

### 2. Hourly Distribution

Analyze how email activity is distributed across different hours of the day (0-23 UTC).

**What it measures:**
- Message count per hour
- Number of unique senders per hour
- Busiest hour of the day
- Quietest hour of the day
- Average messages per hour

**Use cases:**
- Understand when team members are most active
- Identify optimal times for async communication
- Plan meeting schedules around email peaks
- Detect time zone patterns in global teams

### 3. Thread Lifetime Analysis

Calculate the duration of each thread, defined as the time span from the first message to the last message in the thread.

**What it measures:**
- Duration of each thread (in seconds, hours, days)
- Number of messages in each thread
- First and last message timestamps
- Average thread lifetime
- Median thread lifetime
- Longest and shortest threads

**Use cases:**
- Understand conversation dynamics
- Identify long-running discussions
- Measure resolution times for issue threads
- Analyze discussion intensity

## Database Schema

### daily_activity Table

```sql
CREATE TABLE daily_activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL UNIQUE,           -- YYYY-MM-DD format
    message_count INTEGER NOT NULL,       -- Total messages on that day
    unique_senders INTEGER NOT NULL,      -- Number of unique senders
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### hourly_distribution Table

```sql
CREATE TABLE hourly_distribution (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hour INTEGER NOT NULL UNIQUE,         -- 0-23 (UTC)
    message_count INTEGER NOT NULL,       -- Total messages in that hour
    unique_senders INTEGER NOT NULL,      -- Number of unique senders
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### thread_lifetimes Table

```sql
CREATE TABLE thread_lifetimes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id INTEGER NOT NULL UNIQUE,
    first_message_date TEXT NOT NULL,     -- ISO 8601 format
    last_message_date TEXT NOT NULL,      -- ISO 8601 format
    lifetime_seconds INTEGER NOT NULL,    -- Duration in seconds
    message_count INTEGER NOT NULL,       -- Messages in thread
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (thread_id) REFERENCES threads(id)
);
```

## API Methods

### Calculate Time Insights

```python
from eml_analyzer.threads import ThreadManager

tm = ThreadManager(db.connection)

# Calculate all time-based insights
days = tm.calculate_daily_activity()        # Returns: number of days
hours = tm.calculate_hourly_distribution()  # Returns: number of hours
threads = tm.calculate_thread_lifetimes()   # Returns: number of threads
```

### Daily Activity Queries

```python
# Get daily activity data
activity = tm.get_daily_activity()
# Returns: List of dicts with 'date', 'message_count', 'unique_senders'

# Get daily activity summary
summary = tm.get_daily_activity_summary()
# Returns: Dict with:
#   - total_messages: Total messages across all days
#   - total_days: Number of days with activity
#   - avg_per_day: Average messages per day
#   - max_day: Highest message count on any single day
#   - min_day: Lowest message count on any single day
```

### Hourly Distribution Queries

```python
# Get hourly distribution data
distribution = tm.get_hourly_distribution()
# Returns: List of dicts with 'hour' (0-23), 'message_count', 'unique_senders'

# Get hourly distribution summary
summary = tm.get_hourly_activity_summary()
# Returns: Dict with:
#   - busiest_hour: Hour with most messages
#   - quietest_hour: Hour with fewest messages
#   - total_hours: Number of hours with activity
#   - avg_per_hour: Average messages per hour
#   - max_hour_count: Message count in busiest hour
#   - min_hour_count: Message count in quietest hour
```

### Thread Lifetime Queries

```python
# Get thread lifetimes with sorting options
lifetimes = tm.get_thread_lifetimes(limit=10, sort_by="lifetime")
# sort_by options:
#   - "lifetime": Longest threads first (default)
#   - "messages": Most messages first
#   - "recent": Most recent threads first
# Returns: List of dicts with:
#   - thread_id
#   - first_message_date
#   - last_message_date
#   - lifetime_seconds
#   - lifetime_hours
#   - lifetime_days
#   - message_count

# Get thread lifetime statistics
stats = tm.get_thread_lifetime_stats()
# Returns: Dict with:
#   - avg_lifetime_seconds, avg_lifetime_hours, avg_lifetime_days
#   - median_lifetime_seconds, median_lifetime_hours, median_lifetime_days
#   - min_lifetime_seconds
#   - max_lifetime_seconds
#   - total_threads
```

## CLI Commands

### Calculate Time Insights

```bash
eml-analyzer calculate-time-insights <db_file>
```

Calculates all time-based insights:
- Daily activity for all days
- Hourly distribution for all hours
- Thread lifetimes for all threads

**Output:**
```
Calculating time-based insights...
✓ Daily activity calculated: 17 days
✓ Hourly distribution calculated: 12 hours
✓ Thread lifetimes calculated: 17 threads
```

### Daily Activity Report

```bash
eml-analyzer daily-activity <db_file>
```

Displays daily message activity with summary statistics.

**Output:**
```
======================================================================
DAILY MESSAGE ACTIVITY
======================================================================
Date            Messages   Unique Senders
----------------------------------------------------------------------
2024-01-01            1                1
2024-01-02            1                1
2024-01-03            1                1
...
----------------------------------------------------------------------
Total Messages:    26
Total Days:        17
Average per Day:   1.5
Peak Day:          6 messages
Slowest Day:       1 messages
======================================================================
```

### Hourly Distribution Report

```bash
eml-analyzer hourly-distribution <db_file>
```

Displays hourly message distribution with summary statistics.

**Output:**
```
======================================================================
HOURLY MESSAGE DISTRIBUTION
======================================================================
Hour (UTC)      Messages   Unique Senders
----------------------------------------------------------------------
00:00-00:59           1               1
01:00-01:59           1               1
02:00-02:59           1               1
...
----------------------------------------------------------------------
Busiest Hour:      18:00 (6 messages)
Quietest Hour:     00:00 (1 messages)
Average per Hour:  2.2
======================================================================
```

### Thread Lifetimes Report

```bash
eml-analyzer thread-lifetimes <db_file> [--limit 10] [--sort lifetime|messages|recent]
```

Displays thread lifetimes with filtering and sorting options.

**Options:**
- `--limit N`: Show top N threads (default: 10)
- `--sort lifetime`: Sort by duration (longest first) - default
- `--sort messages`: Sort by message count (most first)
- `--sort recent`: Sort by most recent threads first

**Output:**
```
==============================================================================================
THREAD LIFETIMES
==============================================================================================
Thread   Duration                 Messages   First Message
-----------------------------------------------------------------------------------------------
17       20 hours, 45 minutes            2   2024-01-17
6        9 hours                        10   2024-01-06
16       2 hours                         2   2024-01-16
1        0 seconds                       1   2024-01-01
2        0 seconds                       1   2024-01-02
-----------------------------------------------------------------------------------------------
Total Threads:         17
Average Lifetime:      1 hour, 52 minutes, and 3 seconds
Median Lifetime:       0 seconds
Longest Thread:        20 hours, 45 minutes
Shortest Thread:       0 seconds
==============================================================================================
```

## Implementation Details

### Date Handling

- **Daily Activity**: Uses `DATE(date)` SQL function to group emails by calendar date
- **Hourly Distribution**: Uses `strftime('%H', date)` to extract hour from UTC timestamp
- **Thread Lifetimes**: Calculates difference between MIN and MAX timestamps in each thread
- **Timezone Handling**: All dates are normalized to UTC before analysis (see dateutil module)
- **NULL Handling**: Emails with NULL or unparseable dates are skipped during calculations

### Performance Characteristics

- **Calculation Complexity**: O(n) where n = number of emails
- **Query Complexity**: O(1) for summary statistics, O(k) for k results
- **Index Coverage**: Indexed on date, hour, and thread_id for fast queries
- **Storage**: Minimal overhead (~1KB per day, ~100 bytes per hour, ~200 bytes per thread)

### Data Integrity

- **UNIQUE Constraints**: Prevent duplicate daily_activity and hourly_distribution records
- **Foreign Keys**: thread_lifetimes.thread_id references threads.id
- **Validation**: Skips invalid dates and negative lifetimes during calculation
- **Idempotency**: Running calculations multiple times produces consistent results

## Usage Examples

### Example 1: Analyze Daily Patterns

```python
from eml_analyzer.threads import ThreadManager

tm = ThreadManager(db.connection)
tm.calculate_daily_activity()

summary = tm.get_daily_activity_summary()
print(f"Average messages per day: {summary['avg_per_day']:.1f}")
print(f"Peak day: {summary['max_day']} messages")

activity = tm.get_daily_activity()
for day in activity:
    if day['message_count'] > summary['avg_per_day']:
        print(f"Above average: {day['date']} ({day['message_count']} messages)")
```

### Example 2: Find Busiest Hours

```python
tm.calculate_hourly_distribution()

summary = tm.get_hourly_activity_summary()
print(f"Busiest hour: {summary['busiest_hour']:02d}:00")
print(f"Quietest hour: {summary['quietest_hour']:02d}:00")

distribution = tm.get_hourly_distribution()
for hour_data in distribution:
    if hour_data['hour'] >= 9 and hour_data['hour'] <= 17:  # Business hours
        print(f"{hour_data['hour']:02d}:00: {hour_data['message_count']} messages")
```

### Example 3: Identify Long-Running Discussions

```python
tm.calculate_thread_lifetimes()

# Get threads with longest discussions
long_threads = tm.get_thread_lifetimes(limit=5, sort_by="lifetime")
for thread in long_threads:
    days = thread['lifetime_days']
    if days > 1:
        print(f"Thread {thread['thread_id']}: {days:.1f} days, {thread['message_count']} messages")
```

### Example 4: Measure Team Communication Intensity

```python
tm.calculate_daily_activity()
tm.calculate_hourly_distribution()

daily_summary = tm.get_daily_activity_summary()
hourly_summary = tm.get_hourly_activity_summary()

print(f"Total activity span: {daily_summary['total_days']} days")
print(f"Daily average: {daily_summary['avg_per_day']:.1f} messages")
print(f"Hourly average: {hourly_summary['avg_per_hour']:.1f} messages")

# Calculate intensity score
intensity = daily_summary['avg_per_day'] * hourly_summary['total_hours']
print(f"Communication intensity: {intensity:.1f}")
```

## Limitations and Considerations

1. **Timezone Representation**: Hourly distribution is in UTC. For multi-timezone teams, consider converting to local time zones for analysis.

2. **Single-Day Threads**: Threads with all messages on the same day show 0 seconds lifetime. This is correct but may not capture the full discussion context.

3. **Date Parsing**: Emails with unparseable dates are skipped. Check the raw database for emails with NULL dates if results seem incomplete.

4. **Historical Data**: Calculations include all emails in the database. For incremental updates, consider filtering by date range.

5. **Performance**: On very large datasets (>100,000 emails), calculations may take several seconds. Results are cached in tables for fast querying.

## Related Features

- **Response Time Analysis**: Measures time between original message and reply (see RESPONSE_TIME_ANALYSIS.md)
- **Thread Reconstruction**: Builds conversation threads from Message-ID and In-Reply-To headers (see THREADS_AND_INTERACTIONS.md)
- **Interaction Analysis**: Tracks sender→recipient relationships and dominance scores (see THREADS_AND_INTERACTIONS.md)

## Testing

Run the time-based insights test suite:

```bash
python3 test_time_insights.py
```

This test:
1. Generates test data with 30 emails
2. Imports emails and reconstructs threads
3. Calculates all time-based insights
4. Verifies calculations for accuracy
5. Checks data integrity and constraints
6. Displays sample results

Expected output:
```
✓ Daily activity calculated: 17 days
✓ Hourly distribution calculated: 12 hours
✓ Thread lifetimes calculated: 17 threads
✓ All time-based insights tests completed!
```
