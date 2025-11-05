from typing import List, Optional
from gookybot.core.bot import GookyBot
from gookybot.database.models import LevelingProfile
import logging
from sqlalchemy import select, func, desc

logger = logging.getLogger(__name__)


class LevelingManager:
    
    def __init__(self, bot: GookyBot):
        self.db_session = bot.db_session
    
    def xp_for_level(self, level: int) -> int:
        """Calculate the XP required for a given level."""
        return 10 * (level ** 2) + 10 * level + 100
    
    async def add_xp(self, user_id: int, guild_id: int, xp: int):
        async with self.db_session() as session:
            try:
                stmt = select(LevelingProfile).where(
                    LevelingProfile.user_discord_id == user_id,
                    LevelingProfile.guild_discord_id == guild_id
                )
                profile = (await session.execute(stmt)).scalar_one_or_none()

                if not profile:
                    profile = LevelingProfile(
                        user_discord_id=user_id,
                        guild_discord_id=guild_id,
                        xp=0,
                        level=0,
                    )
                    session.add(profile)
                
                profile.xp += xp

                while profile.xp >= self.xp_for_level(profile.level + 1):
                    profile.level += 1
                
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Error adding XP: {e}", exc_info=True)
    
    async def get_user_profile(self, user_id: int, guild_id: int) -> Optional[LevelingProfile]:
        async with self.db_session() as session:
            try:
                stmt = select(LevelingProfile).where(
                    LevelingProfile.user_discord_id == user_id,
                    LevelingProfile.guild_discord_id == guild_id
                )

                profile = (await session.execute(stmt)).scalar_one_or_none()

                return profile
            
            except Exception as e:
                logger.error(f"Error retrieving user profile: {e}", exc_info=True)
                return None

    # --- NEW FUNCTION FOR /rank ---
    async def get_user_rank(self, user_id: int, guild_id: int) -> Optional[int]:
        """Gets the user's rank number in a specific guild."""
        async with self.db_session() as session:
            try:
                # Create a subquery that ranks all users in the guild
                subquery = select(
                    LevelingProfile.user_discord_id,
                    func.row_number().over(
                        order_by=desc(LevelingProfile.xp)
                    ).label("rank")
                ).where(LevelingProfile.guild_discord_id == guild_id).subquery()

                # Select the rank for the specific user from the subquery
                stmt = select(subquery.c.rank).where(
                    subquery.c.user_discord_id == user_id
                )
                
                rank = (await session.execute(stmt)).scalar_one_or_none()
                return rank
            except Exception as e:
                logger.error(f"Error getting user rank: {e}", exc_info=True)
                return None

    # --- NEW FUNCTION FOR /leaderboard ---
    async def get_leaderboard(self, guild_id: int) -> List[LevelingProfile]:
        """Gets the full, sorted leaderboard for a guild."""
        async with self.db_session() as session:
            try:
                stmt = select(LevelingProfile).where(
                    LevelingProfile.guild_discord_id == guild_id
                ).order_by(
                    desc(LevelingProfile.xp)
                )
                profiles = (await session.execute(stmt)).scalars().all()
                return profiles
            except Exception as e:
                logger.error(f"Error getting leaderboard: {e}", exc_info=True)
                return []