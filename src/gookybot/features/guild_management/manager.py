import logging
from typing import Optional, List

import discord
from discord.ext import commands
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from gookybot.database.models.guild import Guild

from sqlalchemy.dialects.postgresql import insert as pg_insert

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
        """
        Atomically gets a guild's settings, creating it if it doesn't exist.
        This is now safe from race conditions.
        """
        try:
            insert_stmt = pg_insert(Guild).values(
                discord_id=guild_id
            ).on_conflict_do_nothing(
                index_elements=['discord_id']
            )
            
            await session.execute(insert_stmt)
            
            select_stmt = select(Guild).where(Guild.discord_id == guild_id)
            
            guild = (await session.execute(select_stmt)).scalar_one()
            
            await session.commit()
            return guild
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Error retrieving or creating guild ID {guild_id}: {e}", exc_info=True)
            return None


    async def get_prefix(self, bot, message: discord.Message) -> str:
        if not message.guild:
            return "g!"
        
        guild = await self.get_or_create_guild(message.guild.id)
        if guild and guild.prefix:
            return commands.when_mentioned_or(guild.prefix)(bot, message)
        return commands.when_mentioned_or("g!")(bot, message)
    
    async def set_prefix(self, guild_id: int, prefix: str) -> bool:
        """Sets a new prefix for a guild."""
        async with self.db_session() as session:
            guild = await self.get_or_create_guild(guild_id, session=session)
            if not guild:
                return False
            
            guild.prefix = prefix
            await session.commit()
            return True
    
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