# Time-Based Insights - Quick Reference Guide

## Overview

The Time-Based Insights feature analyzes email communication patterns across three dimensions:
1. **Daily Activity** - How many messages per day
2. **Hourly Distribution** - When messages are sent (by hour of day)
3. **Thread Lifetimes** - How long conversations last

## Quick Start

### Step 1: Calculate Insights
```bash
eml-analyzer calculate-time-insights
```

### Step 2: View Reports
```bash
eml-analyzer daily-activity
eml-analyzer hourly-distribution
eml-analyzer thread-lifetimes
```

## CLI Commands

### calculate-time-insights
**Purpose**: Compute all time-based insights
```bash
eml-analyzer calculate-time-insights
```
**Output**: Shows number of days, hours, and threads processed

### daily-activity
**Purpose**: Display daily message activity
```bash
eml-analyzer daily-activity
```
**Shows**:
- Messages per day
- Unique senders per day
- Peak and slowest days
- Average daily volume

### hourly-distribution
**Purpose**: Display hourly message distribution
```bash
eml-analyzer hourly-distribution
```
**Shows**:
- Messages per hour (0-23 UTC)
- Unique senders per hour
- Busiest and quietest hours
- Average messages per hour

### thread-lifetimes
**Purpose**: Display thread lifetimes with sorting
```bash
eml-analyzer thread-lifetimes [--limit N] [--sort TYPE]
```
**Options**:
- `--limit N`: Show top N threads (default: 10)
- `--sort lifetime`: Longest threads first (default)
- `--sort messages`: Most messages first
- `--sort recent`: Most recent threads first

**Shows**:
- Thread duration
- Message count
- First message date
- Average and median lifetimes

## Python API

### Basic Usage
```python
from eml_analyzer.threads import ThreadManager
from eml_analyzer.database import Database

# Initialize
db = Database("emails.db")
tm = ThreadManager(db.connection)

# Calculate insights
days = tm.calculate_daily_activity()
hours = tm.calculate_hourly_distribution()
threads = tm.calculate_thread_lifetimes()

# Query results
daily_summary = tm.get_daily_activity_summary()
hourly_summary = tm.get_hourly_activity_summary()
lifetime_stats = tm.get_thread_lifetime_stats()
```

### Daily Activity
```python
# Get all daily activity
activity = tm.get_daily_activity()
for day in activity:
    print(f"{day['date']}: {day['message_count']} messages")

# Get summary
summary = tm.get_daily_activity_summary()
print(f"Average: {summary['avg_per_day']:.1f} messages/day")
print(f"Peak: {summary['max_day']} messages")
```

### Hourly Distribution
```python
# Get all hourly data
distribution = tm.get_hourly_distribution()
for hour_data in distribution:
    hour = hour_data['hour']
    print(f"{hour:02d}:00: {hour_data['message_count']} messages")

# Get summary
summary = tm.get_hourly_activity_summary()
print(f"Busiest: {summary['busiest_hour']:02d}:00")
print(f"Quietest: {summary['quietest_hour']:02d}:00")
```

### Thread Lifetimes
```python
# Get longest threads
longest = tm.get_thread_lifetimes(limit=5, sort_by="lifetime")
for thread in longest:
    print(f"Thread {thread['thread_id']}: {thread['lifetime_days']:.1f} days")

# Get threads with most messages
busiest = tm.get_thread_lifetimes(limit=5, sort_by="messages")
for thread in busiest:
    print(f"Thread {thread['thread_id']}: {thread['message_count']} messages")

# Get statistics
stats = tm.get_thread_lifetime_stats()
print(f"Average: {stats['avg_lifetime_hours']:.1f} hours")
print(f"Median: {stats['median_lifetime_hours']:.1f} hours")
```

## Common Scenarios

### Find Peak Communication Times
```bash
# View hourly distribution
eml-analyzer hourly-distribution

# Find the busiest hour to schedule meetings
```

### Identify Long-Running Discussions
```bash
# Sort threads by duration
eml-analyzer thread-lifetimes --sort lifetime --limit 20

# Analyze conversation intensity
```

### Measure Team Activity Patterns
```bash
# View daily activity
eml-analyzer daily-activity

# Understand team productivity patterns
```

### Analyze Communication Intensity
```python
daily_summary = tm.get_daily_activity_summary()
hourly_summary = tm.get_hourly_activity_summary()

# Calculate intensity score
intensity = daily_summary['avg_per_day'] * hourly_summary['total_hours']
print(f"Communication intensity: {intensity:.1f}")
```

## Data Interpretation

### Daily Activity
- **Peak Day**: Day with most messages (indicates important discussions)
- **Average**: Expected daily message volume
- **Slowest Day**: Quietest day (may indicate holidays or low activity periods)

### Hourly Distribution
- **Busiest Hour**: When team is most active (good for async communication)
- **Quietest Hour**: When team is least active (good for focused work)
- **Distribution**: Shows work hour patterns and timezone effects

### Thread Lifetimes
- **Long Lifetimes**: Extended discussions or unresolved issues
- **Short Lifetimes**: Quick decisions or brief exchanges
- **Message Count**: Discussion intensity (more messages = more back-and-forth)

## Performance Notes

| Dataset Size | Calculation Time | Storage |
|---|---|---|
| 30 emails | <0.1s | <5KB |
| 100 emails | <0.1s | ~15KB |
| 1,000 emails | <0.5s | ~150KB |
| 10,000 emails | ~2s | ~1.5MB |

## Limitations

1. **Timezone**: Hourly distribution is in UTC
2. **Single-Day Threads**: Show 0 seconds lifetime
3. **Date Parsing**: Emails with bad dates are skipped
4. **Historical**: Calculations include all emails
5. **Large Datasets**: May take several seconds

## Troubleshooting

### No data showing up?
1. Make sure you ran `calculate-time-insights` first
2. Check that emails were imported successfully
3. Verify dates are properly parsed

### Thread showing 0 seconds lifetime?
- This is correct - all messages are on the same day
- Lifetime = difference between first and last message timestamp

### Why is my hourly distribution in UTC?
- All dates are normalized to UTC for consistency
- You can convert in your analysis if needed

### How do I export data?
- Query the database directly using SQL
- Use the Python API to retrieve and process data
- Results are cached in tables for fast access

## Documentation Links

- **Full Feature Guide**: [TIME_INSIGHTS_FEATURE.md](TIME_INSIGHTS_FEATURE.md)
- **Implementation Details**: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
- **Completion Report**: [TIME_INSIGHTS_COMPLETION.md](TIME_INSIGHTS_COMPLETION.md)
- **Main README**: [README.md](README.md)

## Examples

### Example 1: Daily Report
```bash
# Generate daily activity report
eml-analyzer daily-activity
```

### Example 2: Find Busiest Hour
```python
summary = tm.get_hourly_activity_summary()
busiest_hour = summary['busiest_hour']
print(f"Team is most active at {busiest_hour:02d}:00 UTC")
```

### Example 3: Identify Long Discussions
```python
long_threads = tm.get_thread_lifetimes(limit=10, sort_by="lifetime")
for thread in long_threads:
    if thread['lifetime_days'] > 1:
        print(f"Thread {thread['thread_id']}: {thread['lifetime_days']:.1f} days")
```

### Example 4: Communication Intensity
```python
daily = tm.get_daily_activity_summary()
hourly = tm.get_hourly_activity_summary()
intensity = daily['avg_per_day'] * hourly['total_hours']
print(f"Intensity: {intensity:.1f}")
```

## Support

For issues or questions:
1. Check the [TIME_INSIGHTS_FEATURE.md](TIME_INSIGHTS_FEATURE.md) documentation
2. Review the [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) for technical details
3. Check the source code in `eml_analyzer/threads.py`
4. Run the test suite: `python3 test_time_insights.py`
