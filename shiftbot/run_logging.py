import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Dict, List

from .db.db import get_session as default_get_session
from .db.models.run import Run


RUN_LOGGER_NAME = "shiftbot"
COUNTER_FIELDS = ("scanned", "matched", "parsed", "upserted", "skipped", "failures")


class RunDBHandler(logging.Handler):
    """A logging handler that aggregates counters and buffers messages during a run.

    On flush, it appends the buffered messages to `Run.notes` and adds counters
    to the respective run row.
    """

    def __init__(self, run_id: int, get_session: Callable = default_get_session):
        super().__init__()
        self.run_id = run_id
        self.get_session = get_session
        self.buffer: List[str] = []
        self.counters: Dict[str, int] = {k: 0 for k in COUNTER_FIELDS}

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
        except Exception:  # pragma: no cover - formatting should be safe
            msg = record.getMessage()
        self.buffer.append(msg)

        # Aggregate numeric counters from record attributes
        for key in COUNTER_FIELDS:
            val = getattr(record, key, None)
            if isinstance(val, int):
                self.counters[key] += val

    def flush_to_db(self) -> None:
        with self.get_session() as db:
            run = db.get(Run, self.run_id)
            if not run:
                return
            # Update counters
            run.scanned += self.counters["scanned"]
            run.matched += self.counters["matched"]
            run.parsed += self.counters["parsed"]
            run.upserted += self.counters["upserted"]
            run.skipped += self.counters["skipped"]
            run.failures += self.counters["failures"]

            # Append buffered notes
            note_text = "\n".join(self.buffer)
            run.notes = (run.notes + "\n" + note_text) if run.notes else note_text
            run.finished_at_utc = datetime.now(timezone.utc)
            db.add(run)
            db.commit()


@dataclass
class RunTracker:
    """Context manager to create a Run row and capture logs to it.

    Usage:
        with RunTracker():
            ...

    It installs a `RunDBHandler` to the `shiftbot` logger for the duration of
    the context and persists aggregated counters and notes when exiting.
    """

    get_session: Callable = default_get_session
    level: int = logging.INFO
    logger_name: str = RUN_LOGGER_NAME
    _handler: RunDBHandler | None = field(init=False, default=None)
    _logger: logging.Logger | None = field(init=False, default=None)
    _run_id: int | None = field(init=False, default=None)
    _console_handler: logging.Handler | None = field(init=False, default=None)

    def __enter__(self):
        # Create Run row
        with self.get_session() as db:
            run = Run(started_at_utc=datetime.now(timezone.utc))
            db.add(run)
            db.commit()
            db.refresh(run)
            self._run_id = run.id

        # Configure logger and handler
        logger = logging.getLogger(self.logger_name)
        logger.setLevel(self.level)
        handler = RunDBHandler(run_id=self._run_id, get_session=self.get_session)
        # Simple format: timestamp level message
        fmt = logging.Formatter(fmt="%(asctime)s %(levelname)s %(message)s")
        handler.setFormatter(fmt)
        logger.addHandler(handler)
        # Also add a StreamHandler that writes to stdout/stderr so logs (and
        # exceptions emitted via logger.exception) show up in container logs.
        console = logging.StreamHandler()
        console.setLevel(self.level)
        console.setFormatter(fmt)
        logger.addHandler(console)

        self._console_handler = console

        self._handler = handler
        self._logger = logger
        return self

    def __exit__(self, exc_type, exc, tb):
        # Record failure count if exception propagated
        if exc is not None and self._handler is not None:
            # Simulate a counter bump without requiring an explicit log call
            self._handler.counters["failures"] += 1
            self._handler.buffer.append(f"Failure: {exc_type.__name__}: {exc}")
            # Also emit full traceback to logs so it appears in container stdout
            logging.getLogger(self.logger_name).exception("Unhandled exception during run")

        # Flush and detach handler
        if self._handler is not None:
            self._handler.flush_to_db()
            if self._logger is not None:
                try:
                    self._logger.removeHandler(self._handler)
                except Exception:  # pragma: no cover
                    pass
        # Remove console handler as well
        if self._console_handler is not None and self._logger is not None:
            try:
                self._logger.removeHandler(self._console_handler)
            except Exception:  # pragma: no cover
                pass
        # Don't suppress exceptions
        return False
