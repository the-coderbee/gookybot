from pathlib import Path
import discord
from discord.ext import commands
from gookybot.database.connection import async_session_maker
import logging
from gookybot.features.guild_management.manager import GuildManager


logger = logging.getLogger(__name__)
BOT_OWNER_ID = 1151122735989280780

class GookyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        self.db_session = async_session_maker
        logger.info("Database session maker attached to bot instance.")

        self.guild_manager = GuildManager(self)
        super().__init__(command_prefix=self.guild_manager.get_prefix, intents=intents, help_command=None, owner_id=BOT_OWNER_ID)
        

    async def load_all_cogs(self):
        logger.info("Loading all cogs...")
        cogs_dir = Path(__file__).parent.parent / 'cogs'
        loaded_cogs = 0
        for cog_file in cogs_dir.glob("*.py"):
            if cog_file.name.startswith("__"):
                continue

            extension = f'gookybot.cogs.{cog_file.stem}'
            try:
                await self.load_extension(extension)
                logger.info(f"Successfully loaded cog: {extension}")
                loaded_cogs += 1
            except Exception as e:
                logger.error(f"Failed to load cog: {extension}. Error: {e}")
        logger.info(f"Cog loading complete | loaded {loaded_cogs} cogs")
    
    async def setup_hook(self):
        logger.info(f"Starting setup for {self.user}...")

        await self.load_all_cogs()
        
        logger.info("Syncing global command tree...")
        await self.tree.sync()
        logger.info("Global sync complete.")
        
        logger.info("Bot setup complete!")
        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')
        logger.info('------')

    async def on_ready(self):
        """Called when the bot is fully ready and connected."""
        activity = discord.Activity(
            type=discord.ActivityType.watching, 
            name="Flix's Citadel"
        )
        await self.change_presence(status=discord.Status.online, activity=activity)
        logger.info("Bot presence set.")
        logger.info("Bot is ready!")