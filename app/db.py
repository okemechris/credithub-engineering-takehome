"""SQLite + SQLAlchemy wiring.

The real platform runs PostgreSQL; this exercise uses SQLite so it runs with
zero setup. The patterns (models, sessions, a get_db dependency) mirror the
real codebase.
"""

from contextlib import contextmanager
from contextvars import ContextVar

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./takehome.db"

engine = create_engine(
    # `timeout` raises pysqlite's busy-wait from its 5s default: a burst of
    # webhook calls serialized by `serialized_write()` (below) queues up on
    # SQLite's single write lock, and 5s is easy to exceed under a real
    # burst, surfacing as an `OperationalError: database is locked` (a 500)
    # instead of the request just waiting its turn a little longer.
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 30},
)
_is_sqlite = engine.dialect.name == "sqlite"


# pysqlite only opens a real transaction lazily, on the first write
# statement — so two threads racing the same request can both finish their
# read-only checks before either has taken SQLite's single write lock, and
# `SELECT ... FOR UPDATE` (see app.payments._lock_loan) is a silent no-op on
# this driver. `serialized_write()` below forces `BEGIN IMMEDIATE` for a
# transaction so it claims that write lock up front — a second concurrent
# request genuinely blocks until the first commits, then re-reads fresh
# state instead of racing on stale reads. `BEGIN IMMEDIATE` is SQLite-only
# syntax, so this whole mechanism is gated on the dialect actually being
# SQLite (this exercise's DB — see module docstring) rather than assuming it.
#
# Only the payment webhook needs this, so it's opt-in per transaction (via a
# ContextVar — safe under both the sync threadpool FastAPI runs plain `def`
# routes in and any future `async def` route, unlike `threading.local()`,
# which only stays request-scoped as long as there's a strict one-thread-
# per-request model) rather than forced on every transaction: plain read
# endpoints (GET /loans, /payment-events, /audit-log) have nothing to
# serialize against each other, and forcing them onto the same eager write
# lock would make them block one another, and any in-flight webhook, for no
# reason.
if _is_sqlite:

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_connection, connection_record):
        dbapi_connection.isolation_level = None
        # WAL lets readers (GET /loans, /payment-events, /audit-log) proceed
        # against the DB file while a webhook's write transaction is open,
        # instead of blocking behind it for the whole transaction — SQLite's
        # default rollback-journal mode allows only one connection (reader or
        # writer) to touch the file at a time.
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    _serialize: ContextVar[bool] = ContextVar("serialize_write", default=False)

    @event.listens_for(engine, "begin")
    def _sqlite_begin(conn):
        conn.exec_driver_sql("BEGIN IMMEDIATE" if _serialize.get() else "BEGIN")


@contextmanager
def serialized_write():
    """Force the SQLite transaction opened inside this block to take the
    write lock immediately, instead of SQLite's normal lazy-on-first-write
    behavior. Must wrap the *first* use of the session in the block — the
    transaction begins (and this takes effect) on that first statement. A
    no-op on any other dialect (e.g. a row-locking DB doesn't need it).
    """
    if not _is_sqlite:
        yield
        return
    token = _serialize.set(True)
    try:
        yield
    finally:
        _serialize.reset(token)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency — yields a session, always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
