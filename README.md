# EML Analyzer

A Python CLI tool for analyzing local EML (email) files. Import emails from a directory, parse headers, store them in a SQLite database, and generate statistics.

## Features

- **EML File Import**: Import all EML files from a directory
- **Header Parsing**: Extract From, To, Date, Subject, Message-ID, and In-Reply-To headers
- **Duplicate Detection**: Prevent duplicate emails from being inserted using hash-based and Message-ID detection
- **SQLite Storage**: Efficient storage with indexed lookups
- **Statistics**: View total messages, unique senders, and date range
- **Thread Reconstruction**: Automatically reconstruct email conversations using Message-ID and In-Reply-To headers
- **Interaction Analysis**: Track sender→recipient relationships and communication patterns
- **Response Time Analysis**: Calculate timezone-aware response times between original messages and replies
- **Time-Based Insights**: Analyze daily activity, hourly distribution, and thread lifetimes
- **Edge Case Handling**:
  - Missing Message-IDs
  - Duplicate entries
  - Mixed timezones
  - Special characters in subjects
  - Multi-level reply chains

## Project Structure

```
eml_analyzer/
├── eml_analyzer/
│   ├── __init__.py           # Package initialization
│   ├── cli.py                # CLI entry point (Click-based)
│   ├── database.py           # SQLite database models and utilities
│   ├── parser.py             # EML file parsing
│   ├── importer.py           # EML file import logic
│   ├── threads.py            # Thread reconstruction, interactions, response times, time insights
│   └── dateutil.py           # Timezone-aware date parsing and formatting
├── data/
│   └── sample_emails/        # Test dataset (30 realistic emails)
├── setup.py                  # Package setup and dependencies
├── generate_test_data.py     # Script to generate test dataset
├── test_workflow.py          # Workflow test script
├── test_threads_and_interactions.py  # Thread and interaction tests
├── test_response_times.py    # Response time analysis tests
├── test_time_insights.py     # Time-based insights tests
├── README.md                 # This file
├── QUICKSTART.md             # Quick start guide
├── PROJECT_SUMMARY.md        # Project overview
├── THREADS_AND_INTERACTIONS.md  # Thread reconstruction documentation
├── RESPONSE_TIME_ANALYSIS.md    # Response time analysis documentation
└── TIME_INSIGHTS_FEATURE.md     # Time-based insights documentation
```

## Installation

### Prerequisites
- Python 3.8+
- Click library (for CLI)
- email-validator library (optional, for validation)

### Install from source

```bash
cd eml_analyzer
pip install -e .
```

Or install dependencies manually:

```bash
pip install click email-validator
```

## Usage

### Import EML files

```bash
eml-analyzer import-emails /path/to/eml/folder
```

Example:
```bash
eml-analyzer import-emails ./data/sample_emails
```

Output:
```
Importing EML files from: ./data/sample_emails
✓ Imported: 28 emails
⊘ Duplicates skipped: 2
```

### View Statistics

```bash
eml-analyzer stats
```

Output:
```
==================================================
EMAIL STATISTICS
==================================================
Total Messages:    28
Unique Senders:    6
Date Range:        2024-01-01T18:00:00 to Sat, 20 Jan 2024 22:15:00 -0800
==================================================
```

### Specify Custom Database Path

```bash
eml-analyzer --db /path/to/custom.db import-emails /path/to/eml/folder
eml-analyzer --db /path/to/custom.db stats
```

## Database Schema

### emails table

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key (auto-increment) |
| message_id | TEXT | Unique Message-ID header (nullable) |
| from_addr | TEXT | Sender email address |
| to_addr | TEXT | Recipient email address(es) |
| date | TEXT | Email date in ISO format |
| subject | TEXT | Email subject line (nullable) |
| in_reply_to | TEXT | In-Reply-To header (nullable) |
| hash | TEXT | SHA256 hash for duplicate detection |
| created_at | TIMESTAMP | When the record was created |

### Indexes

- `idx_message_id` on message_id
- `idx_from_addr` on from_addr
- `idx_hash` on hash

## Duplicate Detection

The system uses two methods to detect duplicates:

1. **Hash-based Detection**: Computes SHA256 hash of (from_addr, to_addr, subject, date)
2. **Message-ID Detection**: Checks for duplicate Message-IDs (if present)

This ensures that even emails without Message-IDs won't be duplicated.

## Test Dataset

The project includes a generated test dataset with 30 realistic emails covering:

- ✓ Initial emails from different senders (5)
- ✓ Multi-level reply chains (10)
- ✓ Emails without Message-IDs (5)
- ✓ Duplicate entries (3)
- ✓ Mixed timezones (2)
- ✓ Special characters in subjects (1)
- ✓ Very long subjects (1)
- ✓ No subject line (1)
- ✓ Multiple recipients (2)

### Generate Test Dataset

```bash
python generate_test_data.py
```

This creates 30 deterministic EML files in `data/sample_emails/`.

### Run Workflow Test

```bash
python test_workflow.py
```

This tests:
1. Database initialization
2. Importing emails
3. Statistics retrieval
4. Duplicate detection on re-import

## Advanced Features

### Thread Reconstruction

Automatically reconstruct email conversations using Message-ID and In-Reply-To headers:

```bash
eml-analyzer reconstruct-threads
eml-analyzer list-threads
eml-analyzer show-thread 1
```

See [THREADS_AND_INTERACTIONS.md](THREADS_AND_INTERACTIONS.md) for detailed documentation.

### Interaction Analysis

Analyze communication patterns and identify key participants:

```bash
eml-analyzer build-interactions
eml-analyzer top-senders --limit 10
eml-analyzer top-recipients --limit 10
eml-analyzer dominance
```

### Response Time Analysis

Calculate timezone-aware response times between original messages and replies:

```bash
eml-analyzer calculate-response-times
eml-analyzer avg-response-time
eml-analyzer avg-response-time-by-user
eml-analyzer avg-response-time-to-user
```

See [RESPONSE_TIME_ANALYSIS.md](RESPONSE_TIME_ANALYSIS.md) for detailed documentation.

### Time-Based Insights

Analyze daily activity, hourly distribution, and thread lifetimes:

```bash
eml-analyzer calculate-time-insights
eml-analyzer daily-activity
eml-analyzer hourly-distribution
eml-analyzer thread-lifetimes --limit 10 --sort lifetime
```

See [TIME_INSIGHTS_FEATURE.md](TIME_INSIGHTS_FEATURE.md) for detailed documentation.

## Example Workflow

```bash
# Generate test data
python generate_test_data.py

# Import emails
eml-analyzer import-emails ./data/sample_emails

# View statistics
eml-analyzer stats

# Reconstruct threads
eml-analyzer reconstruct-threads
eml-analyzer list-threads

# Analyze interactions
eml-analyzer build-interactions
eml-analyzer top-senders

# Calculate response times
eml-analyzer calculate-response-times
eml-analyzer avg-response-time

# Analyze time-based patterns
eml-analyzer calculate-time-insights
eml-analyzer daily-activity
eml-analyzer hourly-distribution
eml-analyzer thread-lifetimes
```

## Architecture

### Database Layer (`database.py`)

- Handles SQLite connection and schema creation
- Provides methods for inserting and querying emails
- Implements duplicate detection logic

### Parser Layer (`parser.py`)

- Uses Python's built-in `email` library
- Extracts relevant headers from EML files
- Handles parsing errors gracefully

### Importer Layer (`importer.py`)

- Orchestrates the import process
- Validates required fields (From, To)
- Counts imported vs. duplicate emails

### CLI Layer (`cli.py`)

- Click-based command-line interface
- Two main commands: `import-emails` and `stats`
- Supports custom database path

## Error Handling

- Invalid EML files are skipped with error messages
- Missing required fields (From, To) are skipped
- Database integrity errors are caught during insertion
- File not found errors are reported clearly

## Performance

- **Indexing**: Database queries use indexes on frequently accessed columns
- **Batch Processing**: Emails are processed sequentially to minimize memory usage
- **Hash-based Deduplication**: O(1) lookup time for duplicate detection

## Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Quick start guide for new users
- **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - High-level project overview
- **[THREADS_AND_INTERACTIONS.md](THREADS_AND_INTERACTIONS.md)** - Thread reconstruction and interaction analysis
- **[RESPONSE_TIME_ANALYSIS.md](RESPONSE_TIME_ANALYSIS.md)** - Response time calculation and analysis
- **[TIME_INSIGHTS_FEATURE.md](TIME_INSIGHTS_FEATURE.md)** - Daily activity, hourly distribution, and thread lifetime analysis

## Future Enhancements

- Export statistics to JSON/CSV
- Search/filter emails by sender, date range, subject
- Detect spam patterns
- Export selected emails
- Web interface for browsing
- Real-time email monitoring
- Machine learning-based conversation classification
- Sentiment analysis on email threads

## License

MIT
