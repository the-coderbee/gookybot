import discord
import logging
import time
import datetime
from collections import defaultdict, deque
from gookybot.database.models import Infraction
from sqlalchemy import select, func, text

logger = logging.getLogger(__name__)

SPAM_MESSAGE_COUNT = 5
SPAM_TIMEFRAME = 5
WARNING_RESET_HOURS = 24


class SpamManager:
    def __init__(self, bot):
        self.bot = bot
        self.db_session = bot.db_session

        self.spam_cache: defaultdict[int, defaultdict[int, deque[float]]] = defaultdict(lambda: defaultdict(lambda: deque(maxlen=SPAM_MESSAGE_COUNT)))

    def check_for_spam(self, message: discord.Message) -> bool:
        user_id = message.author.id
        guild_id = message.guild.id
        current_time = time.time()

        user_cache = self.spam_cache[guild_id][user_id]

        while user_cache and current_time - user_cache[0] > SPAM_TIMEFRAME:
            user_cache.popleft()

        user_cache.append(current_time)

        if len(user_cache) == SPAM_MESSAGE_COUNT:
            user_cache.clear()
            return True

        return False

    async def issue_warning(self, member: discord.Member, reason: str) -> int:
        async with self.db_session() as session:
            try:
                new_infraction = Infraction(
                    guild_id=member.guild.id,
                    user_id=member.id,
                    infraction_type="spam",
                    issuer_id=self.bot.user.id,
                    reason=reason
                )
                session.add(new_infraction)
                
                stmt = select(func.count(Infraction.id)).where(
                    Infraction.guild_id == member.guild.id,
                    Infraction.user_id == member.id,
                    Infraction.infraction_type == "spam",
                    Infraction.created_at >= (func.now() - text(f"interval '{WARNING_RESET_HOURS} hours'"))
                )
                
                current_warnings = (await session.execute(stmt)).scalar()
                
                await session.commit()
                return current_warnings
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to issue spam warning: {e}", exc_info=True)
                return 0
