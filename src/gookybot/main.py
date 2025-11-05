import os
import asyncio
from dotenv import load_dotenv
import logging
from gookybot.config.logging import setup_logging
from gookybot.core.bot import GookyBot
logger = logging.getLogger(__name__)


async def main():
    setup_logging()

    load_dotenv()
    TOKEN = os.getenv("DISCORD_TOKEN")

    if not TOKEN:
        logger.critical("DISCORD_TOKEN not found in environment variables.")
        return
    
    bot = GookyBot()

    try:
        logger.info("Starting bot...")
        await bot.start(TOKEN)
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested by user.")
    finally:
        logger.info("Shutting down bots and closing sessions...")
        await bot.close()
        logger.info("Bot shutdown complete!")


def run():
    asyncio.run(main())

if __name__ == "__main__":
    run()
