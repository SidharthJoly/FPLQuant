from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from fplquant.config import settings


class Base(DeclarativeBase):
    pass


def make_engine(database_url: str | None = None) -> Engine:
    url = database_url or settings.database_url
    is_sqlite = url.startswith("sqlite")
    is_memory = ":memory:" in url
    connect_args = {"check_same_thread": False} if is_sqlite else {}
    if is_sqlite and not is_memory:
        Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    # In-memory SQLite is per-connection; without StaticPool, a request handled
    # on a different thread (e.g. FastAPI's run_in_threadpool) would see a
    # fresh, empty database instead of the one migrations/fixtures set up.
    poolclass = StaticPool if is_memory else None
    return create_engine(url, connect_args=connect_args, poolclass=poolclass)


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def session_scope(session_factory: sessionmaker[Session] = SessionLocal) -> Iterator[Session]:
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
