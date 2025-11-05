import os
import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load .env file (for local development)
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    logger.critical("DATABASE_URL environment variable not set. Aborting.")
    raise ValueError("DATABASE_URL environment variable not set.")

if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

try:
    engine = create_async_engine(DATABASE_URL)
    async_session_maker = async_sessionmaker(engine, expire_on_commit=False)
    logger.info("Async database engine and session maker created successfully.")
except Exception as e:
    logger.critical(f"Failed to create async engine: {e}", exc_info=True)
    raise