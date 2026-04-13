from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.models import Base


connect_args = {"check_same_thread": False} if settings.POSTGRES_URL.startswith("sqlite") else {}

engine = create_engine(
    settings.POSTGRES_URL,
    echo=settings.SQL_ECHO,
    future=True,
    pool_pre_ping=True,
    connect_args=connect_args,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


def init_db() -> None:
    if engine.dialect.name == "postgresql":
        with engine.begin() as connection:
            try:
                connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            except Exception:
                pass
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

