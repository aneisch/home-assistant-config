"""Solcast Solar logging helpers."""

import logging

_LOG_MESSAGE_REWRITES: dict[str, tuple[str, tuple[int, ...]]] = {
    "Finished fetching %s data in %.3f seconds (success: %s)": (
        "Finished fetching %s data (success: %s)",
        (0, 2),
    ),
}


class _LogFilter(logging.Filter):
    """Rewrite selected Solcast Solar log messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Rewrite a configured log record."""
        if not isinstance(record.msg, str) or (rewrite := _LOG_MESSAGE_REWRITES.get(record.msg)) is None:
            return True

        replacement_message, argument_indexes = rewrite
        if isinstance(record.args, tuple) and all(0 <= index < len(record.args) for index in argument_indexes):
            record.msg = replacement_message
            record.args = tuple(record.args[index] for index in argument_indexes)
        return True


_LOG_FILTER = _LogFilter()


def get_logger(name: str) -> logging.Logger:
    """Return a logger with Solcast Solar message rewrites enabled."""
    logger = logging.getLogger(name)
    logger.addFilter(_LOG_FILTER)
    return logger
