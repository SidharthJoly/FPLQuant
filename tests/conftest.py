from collections.abc import Iterator

import pytest
from sqlalchemy.orm import Session, sessionmaker

from fplquant.models.base import Base, make_engine


@pytest.fixture
def db_session() -> Iterator[Session]:
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()
