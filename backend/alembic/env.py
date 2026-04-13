from app.db.models import Base
from app.db.session import engine

target_metadata = Base.metadata


def run_migrations_online():
    with engine.begin() as connection:
        target_metadata.create_all(bind=connection)


run_migrations_online()

