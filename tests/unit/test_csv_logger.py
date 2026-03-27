"""
Unit Tests for atlas.core.logging.CSVLogger

Tests file initialization, append/history, max_history limits,
thread safety, old log cleanup, cleanup_done deduplication, and
edge cases.
"""
import pytest
import os
import csv
import threading
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from atlas.core.logging import CSVLogger


FIELDNAMES = ['timestamp', 'value', 'label']


@pytest.fixture
def temp_csv(tmp_path):
    """Return a path string for a temporary CSV file."""
    return str(tmp_path / 'test.csv')


@pytest.fixture(autouse=True)
def clear_cleanup_done():
    """Clear the class-level _cleanup_done set before and after each test."""
    CSVLogger._cleanup_done.clear()
    yield
    CSVLogger._cleanup_done.clear()


@pytest.mark.unit
class TestCSVLogger:
    """Tests for CSVLogger."""

    def test_init_creates_file(self, temp_csv):
        """Creating a CSVLogger should create the file with headers."""
        logger = CSVLogger(
            log_file=temp_csv,
            fieldnames=FIELDNAMES,
        )

        assert os.path.exists(temp_csv)

        with open(temp_csv, 'r', newline='') as f:
            reader = csv.reader(f)
            header = next(reader)
            assert header == FIELDNAMES

    def test_append_and_get_history(self, temp_csv):
        """Appending entries should be retrievable via get_history."""
        logger = CSVLogger(
            log_file=temp_csv,
            fieldnames=FIELDNAMES,
        )

        entries = [
            {'timestamp': '2026-01-01T10:00:00', 'value': '1', 'label': 'a'},
            {'timestamp': '2026-01-01T11:00:00', 'value': '2', 'label': 'b'},
            {'timestamp': '2026-01-01T12:00:00', 'value': '3', 'label': 'c'},
        ]

        for entry in entries:
            logger.append(entry)

        history = logger.get_history()
        assert len(history) == 3
        assert history[0]['value'] == '1'
        assert history[2]['label'] == 'c'

    def test_max_history_limit(self, temp_csv):
        """In-memory history should respect max_history, keeping the latest entries."""
        logger = CSVLogger(
            log_file=temp_csv,
            fieldnames=FIELDNAMES,
            max_history=2,
        )

        for i in range(5):
            logger.append({
                'timestamp': f'2026-01-01T1{i}:00:00',
                'value': str(i),
                'label': f'entry-{i}',
            })

        history = logger.get_history()
        assert len(history) == 2
        # Should be the last 2 entries
        assert history[0]['value'] == '3'
        assert history[1]['value'] == '4'

    def test_thread_safety(self, temp_csv):
        """Concurrent appends from multiple threads should not raise or corrupt data."""
        max_history = 50
        logger = CSVLogger(
            log_file=temp_csv,
            fieldnames=FIELDNAMES,
            max_history=max_history,
        )

        errors = []

        def writer(thread_id):
            try:
                for j in range(20):
                    logger.append({
                        'timestamp': f'2026-01-01T00:{thread_id:02d}:{j:02d}',
                        'value': str(thread_id * 100 + j),
                        'label': f't{thread_id}-{j}',
                    })
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Thread errors: {errors}"

        history = logger.get_history()
        assert len(history) <= max_history

    def test_cleanup_old_logs(self, temp_csv):
        """_cleanup_old_logs should remove entries older than retention_days."""
        # Create the logger first so the file and headers exist
        logger = CSVLogger(
            log_file=temp_csv,
            fieldnames=FIELDNAMES,
            retention_days=7,
        )

        # Write entries directly to the file: some old, some recent
        now = datetime.now()
        old_ts = (now - timedelta(days=10)).isoformat()
        recent_ts = now.isoformat()

        with open(temp_csv, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerow({'timestamp': old_ts, 'value': 'old', 'label': 'remove-me'})
            writer.writerow({'timestamp': recent_ts, 'value': 'new', 'label': 'keep-me'})

        # Force cleanup (bypass the _cleanup_done guard)
        CSVLogger._cleanup_done.discard(temp_csv)
        logger._cleanup_old_logs()

        # Read the file back and verify old entry was removed
        with open(temp_csv, 'r', newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 1
        assert rows[0]['label'] == 'keep-me'

    def test_cleanup_done_flag(self, temp_csv):
        """_cleanup_old_logs should only run once per file path across instances."""
        call_count = 0
        original_cleanup = CSVLogger._cleanup_old_logs

        def counting_cleanup(self_inner):
            nonlocal call_count
            call_count += 1
            original_cleanup(self_inner)

        with patch.object(CSVLogger, '_cleanup_old_logs', counting_cleanup):
            CSVLogger(
                log_file=temp_csv,
                fieldnames=FIELDNAMES,
            )
            assert call_count == 1

            # Second instance with same file should NOT call cleanup again
            CSVLogger(
                log_file=temp_csv,
                fieldnames=FIELDNAMES,
            )
            assert call_count == 1

    def test_empty_file(self, tmp_path):
        """CSVLogger on an empty file should not crash."""
        empty_path = str(tmp_path / 'empty.csv')

        # Create an empty file
        Path(empty_path).touch()

        # Should not raise
        logger = CSVLogger(
            log_file=empty_path,
            fieldnames=FIELDNAMES,
        )

        history = logger.get_history()
        assert isinstance(history, list)

    def test_get_log_path(self, temp_csv):
        """get_log_path returns the resolved path of the log file."""
        logger = CSVLogger(
            log_file=temp_csv,
            fieldnames=FIELDNAMES,
        )

        assert logger.get_log_path() == temp_csv

    def test_clear_history(self, temp_csv):
        """clear_history empties in-memory history but does not affect the file."""
        logger = CSVLogger(
            log_file=temp_csv,
            fieldnames=FIELDNAMES,
        )

        logger.append({
            'timestamp': '2026-01-01T10:00:00',
            'value': '1',
            'label': 'a',
        })
        assert len(logger.get_history()) == 1

        logger.clear_history()
        assert len(logger.get_history()) == 0

        # File should still have the entry
        with open(temp_csv, 'r', newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 1
