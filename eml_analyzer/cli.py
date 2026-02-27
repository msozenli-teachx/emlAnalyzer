"""CLI entry point for EML Analyzer."""

import click
from pathlib import Path
from .database import Database
from .importer import EMLImporter
from .threads import ThreadManager
from .dateutil import DateParser


@click.group()
@click.option(
    "--db",
    default="emails.db",
    type=click.Path(),
    help="Path to the SQLite database file",
)
@click.pass_context
def main(ctx, db):
    """EML Analyzer - Analyze local EML files."""
    ctx.ensure_object(dict)
    ctx.obj["db"] = Database(db)


@main.command()
@click.argument("directory", type=click.Path(exists=True))
@click.pass_context
def import_emails(ctx, directory):
    """Import all EML files from a directory."""
    db = ctx.obj["db"]
    importer = EMLImporter(db)

    try:
        click.echo(f"Importing EML files from: {directory}")
        imported, duplicates = importer.import_from_directory(directory)

        click.echo(f"✓ Imported: {imported} emails")
        if duplicates > 0:
            click.echo(f"⊘ Duplicates skipped: {duplicates}")

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        ctx.exit(1)
    finally:
        db.close()


@main.command()
@click.pass_context
def stats(ctx):
    """Show statistics about imported emails."""
    db = ctx.obj["db"]

    try:
        stats_data = db.get_stats()

        click.echo("\n" + "=" * 50)
        click.echo("EMAIL STATISTICS")
        click.echo("=" * 50)
        click.echo(f"Total Messages:    {stats_data['total_messages']}")
        click.echo(f"Unique Senders:    {stats_data['unique_senders']}")

        if stats_data["date_range"]["start"]:
            click.echo(f"Date Range:        {stats_data['date_range']['start']} to {stats_data['date_range']['end']}")
        else:
            click.echo("Date Range:        No emails imported")

        click.echo("=" * 50 + "\n")

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        ctx.exit(1)
    finally:
        db.close()


@main.command()
@click.pass_context
def reconstruct_threads(ctx):
    """Reconstruct email threads from Message-ID and In-Reply-To headers."""
    db = ctx.obj["db"]

    try:
        click.echo("Reconstructing email threads...")
        tm = ThreadManager(db.connection)
        thread_count, orphaned_count = tm.reconstruct_threads()

        click.echo(f"✓ Threads created: {thread_count}")
        if orphaned_count > 0:
            click.echo(f"⚠ Orphaned emails: {orphaned_count} (missing parent message)")

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        ctx.exit(1)
    finally:
        db.close()


@main.command()
@click.option("--limit", default=20, help="Maximum number of threads to display")
@click.pass_context
def list_threads(ctx, limit):
    """List all threads with message counts."""
    db = ctx.obj["db"]

    try:
        tm = ThreadManager(db.connection)
        threads = tm.get_all_threads()

        if not threads:
            click.echo("No threads found. Run 'reconstruct-threads' first.")
            db.close()
            return

        click.echo("\n" + "=" * 80)
        click.echo("EMAIL THREADS")
        click.echo("=" * 80)

        for idx, thread in enumerate(threads[:limit], 1):
            click.echo(f"\n{idx}. [{thread['message_count']} messages] {thread['subject']}")
            if thread["root_message_id"]:
                click.echo(f"   Root: {thread['root_message_id']}")

        if len(threads) > limit:
            click.echo(f"\n... and {len(threads) - limit} more threads")

        click.echo("\n" + "=" * 80)

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        ctx.exit(1)
    finally:
        db.close()


@main.command()
@click.argument("thread_id", type=int)
@click.pass_context
def show_thread(ctx, thread_id):
    """Display a single thread in chronological order."""
    db = ctx.obj["db"]

    try:
        tm = ThreadManager(db.connection)
        emails = tm.get_thread_emails(thread_id)

        if not emails:
            click.echo(f"Thread {thread_id} not found or is empty.")
            db.close()
            return

        click.echo("\n" + "=" * 80)
        click.echo(f"THREAD {thread_id}")
        click.echo("=" * 80)

        for idx, email in enumerate(emails, 1):
            click.echo(f"\n--- Message {idx} ---")
            click.echo(f"From:    {email['from']}")
            click.echo(f"To:      {email['to']}")
            click.echo(f"Date:    {email['date']}")
            click.echo(f"Subject: {email['subject']}")
            if email["in_reply_to"]:
                click.echo(f"Reply-To: {email['in_reply_to']}")

        click.echo("\n" + "=" * 80)

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        ctx.exit(1)
    finally:
        db.close()


@main.command()
@click.pass_context
def build_interactions(ctx):
    """Build interaction model from email replies."""
    db = ctx.obj["db"]

    try:
        click.echo("Building interaction model...")
        tm = ThreadManager(db.connection)
        interaction_count = tm.build_interactions()

        click.echo(f"✓ Interactions recorded: {interaction_count}")

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        ctx.exit(1)
    finally:
        db.close()


@main.command()
@click.option("--limit", default=10, help="Number of top users to display")
@click.pass_context
def top_senders(ctx, limit):
    """Show top users by replies sent."""
    db = ctx.obj["db"]

    try:
        tm = ThreadManager(db.connection)
        users = tm.get_top_senders(limit)

        if not users:
            click.echo("No interactions found. Run 'build-interactions' first.")
            db.close()
            return

        click.echo("\n" + "=" * 60)
        click.echo("TOP USERS BY REPLIES SENT")
        click.echo("=" * 60)

        for idx, user in enumerate(users, 1):
            click.echo(f"{idx:2}. {user['sender']:30} → {user['total_replies']:4} replies")

        click.echo("=" * 60 + "\n")

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        ctx.exit(1)
    finally:
        db.close()


@main.command()
@click.option("--limit", default=10, help="Number of top users to display")
@click.pass_context
def top_recipients(ctx, limit):
    """Show top users by replies received."""
    db = ctx.obj["db"]

    try:
        tm = ThreadManager(db.connection)
        users = tm.get_top_recipients(limit)

        if not users:
            click.echo("No interactions found. Run 'build-interactions' first.")
            db.close()
            return

        click.echo("\n" + "=" * 60)
        click.echo("TOP USERS BY REPLIES RECEIVED")
        click.echo("=" * 60)

        for idx, user in enumerate(users, 1):
            click.echo(f"{idx:2}. {user['recipient']:30} ← {user['total_replies_received']:4} replies")

        click.echo("=" * 60 + "\n")

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        ctx.exit(1)
    finally:
        db.close()


@main.command()
@click.option("--limit", default=10, help="Number of users to display")
@click.pass_context
def dominance(ctx, limit):
    """Show user dominance scores (sent vs received replies)."""
    db = ctx.obj["db"]

    try:
        tm = ThreadManager(db.connection)
        scores = tm.get_dominance_scores(limit)

        if not scores:
            click.echo("No interactions found. Run 'build-interactions' first.")
            db.close()
            return

        click.echo("\n" + "=" * 80)
        click.echo("USER DOMINANCE SCORES")
        click.echo("=" * 80)
        click.echo("Score: (sent - received) / (sent + received)")
        click.echo("  +1.0 = only sends replies")
        click.echo("   0.0 = balanced sender/receiver")
        click.echo("  -1.0 = only receives replies")
        click.echo("-" * 80)

        for idx, user in enumerate(scores, 1):
            sent = user["sent"]
            received = user["received"]
            score = user["dominance_score"]
            score_str = f"{score:+.2f}"
            click.echo(
                f"{idx:2}. {user['user']:30} {score_str:>6}  "
                f"(sent: {sent:3}, received: {received:3})"
            )

        click.echo("=" * 80 + "\n")

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        ctx.exit(1)
    finally:
        db.close()


@main.command()
@click.pass_context
def calculate_response_times(ctx):
    """Calculate response times for all replies."""
    db = ctx.obj["db"]

    try:
        click.echo("Calculating response times...")
        tm = ThreadManager(db.connection)
        response_count = tm.calculate_response_times()

        click.echo(f"✓ Response times calculated: {response_count}")

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        ctx.exit(1)
    finally:
        db.close()


@main.command()
@click.pass_context
def avg_response_time(ctx):
    """Show overall average response time."""
    db = ctx.obj["db"]

    try:
        tm = ThreadManager(db.connection)
        stats = tm.get_overall_average_response_time()

        if stats["total_replies"] == 0:
            click.echo("No response times found. Run 'calculate-response-times' first.")
            db.close()
            return

        click.echo("\n" + "=" * 70)
        click.echo("OVERALL RESPONSE TIME STATISTICS")
        click.echo("=" * 70)
        click.echo(f"Total Replies Analyzed:  {stats['total_replies']}")
        click.echo(f"\nAverage Response Time:")
        click.echo(f"  {DateParser.format_duration(stats['avg_seconds'])}")
        click.echo(f"  ({stats['avg_hours']:.1f} hours, {stats['avg_days']:.2f} days)")
        click.echo(f"\nMedian Response Time:")
        click.echo(f"  {DateParser.format_duration(stats['median_seconds'])}")
        click.echo(f"\nFastest Response:  {DateParser.format_duration(stats['min_seconds'])}")
        click.echo(f"Slowest Response:  {DateParser.format_duration(stats['max_seconds'])}")
        click.echo("=" * 70 + "\n")

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        ctx.exit(1)
    finally:
        db.close()


@main.command()
@click.option("--limit", default=10, help="Number of users to display")
@click.pass_context
def avg_response_time_by_user(ctx, limit):
    """Show average response time per user (as replier)."""
    db = ctx.obj["db"]

    try:
        tm = ThreadManager(db.connection)
        users = tm.get_average_response_time_by_user(limit)

        if not users:
            click.echo("No response times found. Run 'calculate-response-times' first.")
            db.close()
            return

        click.echo("\n" + "=" * 80)
        click.echo("AVERAGE RESPONSE TIME BY USER (as replier)")
        click.echo("=" * 80)
        click.echo(f"{'User':<35} {'Avg Response':<20} {'Replies':>8}")
        click.echo("-" * 80)

        for user in users:
            duration = DateParser.format_duration(user["avg_seconds"])
            click.echo(
                f"{user['replier']:<35} {duration:<20} {user['reply_count']:>8}"
            )

        click.echo("=" * 80 + "\n")

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        ctx.exit(1)
    finally:
        db.close()


@main.command()
@click.option("--limit", default=10, help="Number of users to display")
@click.pass_context
def avg_response_time_to_user(ctx, limit):
    """Show average response time to each user (how quickly they get replies)."""
    db = ctx.obj["db"]

    try:
        tm = ThreadManager(db.connection)
        users = tm.get_average_response_time_to_user(limit)

        if not users:
            click.echo("No response times found. Run 'calculate-response-times' first.")
            db.close()
            return

        click.echo("\n" + "=" * 80)
        click.echo("AVERAGE RESPONSE TIME TO USER (how quickly they get replies)")
        click.echo("=" * 80)
        click.echo(f"{'User':<35} {'Avg Time to Reply':<20} {'Replies':>8}")
        click.echo("-" * 80)

        for user in users:
            duration = DateParser.format_duration(user["avg_seconds"])
            click.echo(
                f"{user['original_sender']:<35} {duration:<20} {user['reply_count']:>8}"
            )

        click.echo("=" * 80 + "\n")

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        ctx.exit(1)
    finally:
        db.close()


@main.command()
@click.pass_context
def calculate_time_insights(ctx):
    """Calculate daily activity, hourly distribution, and thread lifetimes."""
    db = ctx.obj["db"]

    try:
        click.echo("Calculating time-based insights...")
        tm = ThreadManager(db.connection)
        
        days = tm.calculate_daily_activity()
        click.echo(f"✓ Daily activity calculated: {days} days")
        
        hours = tm.calculate_hourly_distribution()
        click.echo(f"✓ Hourly distribution calculated: {hours} hours")
        
        threads = tm.calculate_thread_lifetimes()
        click.echo(f"✓ Thread lifetimes calculated: {threads} threads")

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        ctx.exit(1)
    finally:
        db.close()


@main.command()
@click.pass_context
def daily_activity(ctx):
    """Show daily message counts."""
    db = ctx.obj["db"]

    try:
        tm = ThreadManager(db.connection)
        activity = tm.get_daily_activity()
        summary = tm.get_daily_activity_summary()

        if not activity:
            click.echo("No daily activity found. Run 'calculate-time-insights' first.")
            db.close()
            return

        click.echo("\n" + "=" * 70)
        click.echo("DAILY MESSAGE ACTIVITY")
        click.echo("=" * 70)
        click.echo(f"{'Date':<15} {'Messages':>10} {'Unique Senders':>15}")
        click.echo("-" * 70)

        for day in activity:
            click.echo(
                f"{day['date']:<15} {day['message_count']:>10} {day['unique_senders']:>15}"
            )

        click.echo("-" * 70)
        click.echo(f"Total Messages:    {summary['total_messages']}")
        click.echo(f"Total Days:        {summary['total_days']}")
        click.echo(f"Average per Day:   {summary['avg_per_day']:.1f}")
        click.echo(f"Peak Day:          {summary['max_day']} messages")
        click.echo(f"Slowest Day:       {summary['min_day']} messages")
        click.echo("=" * 70 + "\n")

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        ctx.exit(1)
    finally:
        db.close()


@main.command()
@click.pass_context
def hourly_distribution(ctx):
    """Show hourly message distribution."""
    db = ctx.obj["db"]

    try:
        tm = ThreadManager(db.connection)
        distribution = tm.get_hourly_distribution()
        summary = tm.get_hourly_activity_summary()

        if not distribution:
            click.echo("No hourly distribution found. Run 'calculate-time-insights' first.")
            db.close()
            return

        click.echo("\n" + "=" * 70)
        click.echo("HOURLY MESSAGE DISTRIBUTION")
        click.echo("=" * 70)
        click.echo(f"{'Hour (UTC)':<15} {'Messages':>10} {'Unique Senders':>15}")
        click.echo("-" * 70)

        for hour_data in distribution:
            hour = hour_data["hour"]
            hour_str = f"{hour:02d}:00-{hour:02d}:59"
            click.echo(
                f"{hour_str:<15} {hour_data['message_count']:>10} {hour_data['unique_senders']:>15}"
            )

        click.echo("-" * 70)
        busiest_str = f"{summary['busiest_hour']:02d}:00" if summary['busiest_hour'] is not None else "N/A"
        quietest_str = f"{summary['quietest_hour']:02d}:00" if summary['quietest_hour'] is not None else "N/A"
        click.echo(f"Busiest Hour:      {busiest_str} ({summary['max_hour_count']} messages)")
        click.echo(f"Quietest Hour:     {quietest_str} ({summary['min_hour_count']} messages)")
        click.echo(f"Average per Hour:  {summary['avg_per_hour']:.1f}")
        click.echo("=" * 70 + "\n")

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        ctx.exit(1)
    finally:
        db.close()


@main.command()
@click.option("--limit", default=10, help="Number of threads to display")
@click.option("--sort", default="lifetime", type=click.Choice(["lifetime", "messages", "recent"]),
              help="Sort by: lifetime (longest), messages (most), recent (newest)")
@click.pass_context
def thread_lifetimes(ctx, limit, sort):
    """Show thread lifetimes."""
    db = ctx.obj["db"]

    try:
        tm = ThreadManager(db.connection)
        lifetimes = tm.get_thread_lifetimes(limit, sort_by=sort)
        stats = tm.get_thread_lifetime_stats()

        if not lifetimes:
            click.echo("No thread lifetimes found. Run 'calculate-time-insights' first.")
            db.close()
            return

        click.echo("\n" + "=" * 90)
        click.echo("THREAD LIFETIMES")
        click.echo("=" * 90)
        click.echo(f"{'Thread':<8} {'Duration':<25} {'Messages':>8} {'First Message':<20}")
        click.echo("-" * 90)

        for thread in lifetimes:
            duration = DateParser.format_duration(thread["lifetime_seconds"])
            first_date = thread["first_message_date"][:10]  # YYYY-MM-DD
            click.echo(
                f"{thread['thread_id']:<8} {duration:<25} {thread['message_count']:>8} {first_date:<20}"
            )

        click.echo("-" * 90)
        click.echo(f"Total Threads:         {stats['total_threads']}")
        click.echo(f"Average Lifetime:      {DateParser.format_duration(stats['avg_lifetime_seconds'])}")
        click.echo(f"Median Lifetime:       {DateParser.format_duration(stats['median_lifetime_seconds'])}")
        click.echo(f"Longest Thread:        {DateParser.format_duration(stats['max_lifetime_seconds'])}")
        click.echo(f"Shortest Thread:       {DateParser.format_duration(stats['min_lifetime_seconds'])}")
        click.echo("=" * 90 + "\n")

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        ctx.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
