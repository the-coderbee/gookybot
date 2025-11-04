from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from .models.base import Base
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise Exception("DATABASE_URL not found in .env file")

engine = create_async_engine(DATABASE_URL)

async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


# for manual creation
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)