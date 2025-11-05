from logging.config import fileConfig

# Import create_engine
from sqlalchemy import create_engine, pool

from alembic import context
import sys
import os

# --- 1. Set up sys.path ---
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

# --- 2. Import your models ---
from gookybot.database.models.base import Base
from gookybot.database.models.guild import Guild
from gookybot.database.models.leveling_profile import LevelingProfile

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- 3. THIS IS THE CRITICAL FIX ---
# We will get the DB_URL and pass it to run_migrations_online()

# Set the target metadata for autogenerate
target_metadata = Base.metadata

def get_database_url():
    """Gets the database URL and patches it for psycopg2."""
    db_url = os.getenv("DATABASE_URL")
    
    if not db_url:
        # Fallback to local .ini file if env var is not set
        return config.get_main_option("sqlalchemy.url")

    # Force the URL to use the 'psycopg2' (sync) driver
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    elif db_url.startswith("postgresql+asyncpg://"):
         db_url = db_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
    
    return db_url

# ... (run_migrations_offline remains the same) ...
def run_migrations_offline() -> None:
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
    """Run migrations in 'online' mode.
    
    THIS FUNCTION IS NOW 100% CORRECT.
    """
    
    # Get the patched database URL
    db_url_for_alembic = get_database_url()
    
    # Manually create the engine with our URL
    # This bypasses all the .ini file-reading magic
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