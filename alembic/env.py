from logging.config import fileConfig

# Import create_engine
from sqlalchemy import create_engine, pool

from alembic import context
import sys
import os

# --- 1. Set up sys.path (finds 'gookybot' in 'src/') ---
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

# --- 2. Import your models and set target_metadata ---
# This MUST happen before fileConfig()
from gookybot.database.models.base import Base
from gookybot.database.models.guild import Guild
from gookybot.database.models.leveling_profile import LevelingProfile
target_metadata = Base.metadata
# --- END CRITICAL SECTION ---

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def get_database_url():
    """Gets the database URL and patches it for psycopg2."""
    # This reads the PRODUCTION url from Railway's env vars
    db_url = os.getenv("DATABASE_URL")
    
    if not db_url:
        # This reads the LOCAL url from alembic.ini
        return config.get_main_option("sqlalchemy.url")

    # Force the URL to use the 'psycopg2' (sync) driver
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    elif db_url.startswith("postgresql+asyncpg://"):
         db_url = db_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
    
    return db_url

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    db_url_for_alembic = get_database_url()
    
    # Manually create the engine with our URL
    connectable = create_engine(db_url_for_alembic, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata, 
            compare_type=True
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()