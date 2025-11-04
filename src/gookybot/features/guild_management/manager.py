import logging
from typing import Optional

import discord
from discord.ext import commands
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from gookybot.database.models.guild import Guild


logger = logging.getLogger(__name__)


class GuildManager:

    def __init__(self, bot):
        self.bot = bot
        self.db_session = bot.db_session

    async def get_or_create_guild(self, guild_id: int, *, session: Optional[AsyncSession] = None) -> Optional[Guild]:
        if session:
            return await self._get_or_create_guild_impl(guild_id, session)
        else:
            async with self.db_session() as new_session:
                return await self._get_or_create_guild_impl(guild_id, new_session)
    
    async def _get_or_create_guild_impl(self, guild_id: int, session: AsyncSession) -> Optional[Guild]:
        """Internal implementation of get_or_create_guild."""
        try:
            stmt = select(Guild).where(Guild.discord_id == guild_id)
            guild = (await session.execute(stmt)).scalar_one_or_none()

            if not guild:
                logger.info(f"Guild ID {guild_id} not found. Creating new entry.")
                guild = Guild(discord_id=guild_id)
                session.add(guild)
                await session.commit()
                logger.info(f"Created new guild entry for guild ID {guild_id}")
            return guild
        except Exception as e:
            logger.error(f"Error retrieving or creating guild ID {guild_id}: {e}", exc_info=True)
            return None


    async def get_prefix(self, bot, message: discord.Message) -> str:
        if not message.guild:
            return "g!"
        
        guild = await self.get_or_create_guild(message.guild.id)
        if guild:
            return commands.when_mentioned_or(guild.prefix)(bot, message)
        else:
            return "g!"
    
    async def add_engagement_channel(self, guild_id: int, channel_id: int) -> bool:
        async with self.db_session() as session:
            guild = await self.get_or_create_guild(guild_id, session=session)
            if not guild:
                return False
            
            new_list = list(guild.engagement_channels or [])
            if channel_id not in new_list:
                new_list.append(channel_id)
                guild.engagement_channels = new_list
                await session.commit()
                return True
            return False
    
    async def remove_engagement_channel(self, guild_id: int, channel_id: int) -> bool:
        async with self.db_session() as session:
            guild = await self.get_or_create_guild(guild_id, session=session)
            if not guild or not guild.engagement_channels:
                return False
            
            new_list = list(guild.engagement_channels)
            if channel_id in new_list:
                new_list.remove(channel_id)
                guild.engagement_channels = new_list
                await session.commit()
                return True
            return False

    async def set_prefix(self, guild_id: int, new_prefix: str) -> bool:
        """Sets a new command prefix for a guild."""
        async with self.db_session() as session:
            try:
                # We use session=session to keep the object attached
                guild = await self.get_or_create_guild(guild_id, session=session)
                if not guild:
                    return False
                
                guild.prefix = new_prefix
                await session.commit()
                logger.info(f"Guild {guild_id} prefix changed to '{new_prefix}'")
                return True
            except Exception as e:
                logger.error(f"Error setting prefix for guild {guild_id}: {e}", exc_info=True)
                return False