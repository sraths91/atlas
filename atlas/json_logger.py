"""Structured JSON logging formatter for production use.

Usage:
    from atlas.json_logger import JsonFormatter

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logging.getLogger().addHandler(handler)

Or set ATLAS_LOG_FORMAT=json environment variable for auto-configuration.
"""
import json
import logging
import time
from typing import Optional


class JsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects.

    Output format:
    {"ts": "2026-03-26T10:30:00", "level": "INFO", "logger": "atlas.wifi", "msg": "...", ...}
    """

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            'ts': time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(record.created)),
            'level': record.levelname,
            'logger': record.name,
            'msg': record.getMessage(),
        }

        if record.exc_info and record.exc_info[0]:
            entry['exception'] = self.formatException(record.exc_info)

        if hasattr(record, 'duration_ms'):
            entry['duration_ms'] = record.duration_ms

        return json.dumps(entry, default=str)


def configure_json_logging():
    """Replace all root logger formatters with JsonFormatter.

    Call this at startup when ATLAS_LOG_FORMAT=json is set.
    """
    fmt = JsonFormatter()
    root = logging.getLogger()
    for handler in root.handlers:
        handler.setFormatter(fmt)
