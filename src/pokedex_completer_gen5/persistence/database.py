from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from pokedex_completer_gen5.persistence.models import Base
from pokedex_completer_gen5.runtime import ensure_runtime_dirs

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def database_url() -> str:
    paths = ensure_runtime_dirs()
    return f"sqlite:///{paths.db_path.as_posix()}"


def engine() -> Engine:
    global _engine, _SessionLocal
    if _engine is None:
        _engine = create_engine(database_url(), future=True)
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, expire_on_commit=False)
    return _engine


def init_database() -> None:
    Base.metadata.create_all(bind=engine())


def reset_database_engine_for_tests() -> None:
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


@contextmanager
def session_scope() -> Iterator[Session]:
    init_database()
    if _SessionLocal is None:
        raise RuntimeError("Database session factory was not initialized")
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
