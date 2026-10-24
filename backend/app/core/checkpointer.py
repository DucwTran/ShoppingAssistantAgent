import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

from app.core.config import settings

CHECKPOINT_DB = settings.data_dir / "checkpoints.sqlite"


@contextmanager
def open_checkpointer(path: Path | None = None) -> Iterator[SqliteSaver]:
    """SQLite-backed checkpointer: threads paused for approval survive a server restart.

    check_same_thread=False because FastAPI runs sync endpoints on a thread pool; SqliteSaver
    serializes access to the connection with its own lock.
    """
    path = path or CHECKPOINT_DB
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    try:
        yield SqliteSaver(conn)
    finally:
        conn.close()


def prune_checkpoints(saver: SqliteSaver, max_age: timedelta, now: datetime | None = None) -> int:
    """Delete every thread whose last activity is older than `max_age`; returns how many were deleted.

    Each step of a run writes a checkpoint, so without pruning the database only grows. The rule is
    the same for finished threads, threads paused for a decision and threads stopped by an error:
    once idle for `max_age`, nobody is expected to come back to them. The freed space is then
    returned to the file system.
    """
    cutoff = (now or datetime.now(timezone.utc)) - max_age
    # Thread ids are read straight from SqliteSaver's table: list() would deserialize every checkpoint.
    with saver.cursor(transaction=False) as cur:
        thread_ids = [row[0] for row in cur.execute("SELECT DISTINCT thread_id FROM checkpoints")]

    stale = []
    for thread_id in thread_ids:
        latest = saver.get_tuple({"configurable": {"thread_id": thread_id}})
        if latest and datetime.fromisoformat(latest.checkpoint["ts"]) < cutoff:
            stale.append(thread_id)

    for thread_id in stale:
        saver.delete_thread(thread_id)
    if stale:
        with saver.cursor() as cur:
            cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            cur.execute("VACUUM")
    return len(stale)
