import discord
import logging
from gookybot.database.models import AutoRole
from sqlalchemy import select

logger = logging.getLogger(__name__)


class AutoRoleManager:
    def __init__(self, bot):
        self.bot = bot
        self.db_session = bot.db_session

    async def _grant_role(self, member: discord.Member, role_id: int, reason: str):
        """A helper function to safely grant a role."""
        role = member.guild.get_role(role_id)
        if not role:
            logger.warning(f"AutoRole: Role ID {role_id} not found in guild {member.guild.name}.")
            return
        
        if member.guild.me.top_role <= role:
            logger.warning(f"AutoRole: Bot role is too low to grant '{role.name}' in {member.guild.name}.")
            return

        if role in member.roles:
            return

        try:
            await member.add_roles(role, reason=reason)
            logger.info(f"AutoRole: Granted role '{role.name}' to {member.display_name} in {member.guild.name}.")
        except discord.Forbidden:
            logger.error(f"AutoRole: Bot lacks 'Manage Roles' permission in {member.guild.name}.")
        except Exception as e:
            logger.error(f"AutoRole: Failed to grant role {role.name} to {member.display_name}: {e}", exc_info=True)

    async def handle_member_join(self, member: discord.Member):
        """Called by GeneralCog to grant 'on_join' roles."""
        async with self.db_session() as session:
            stmt = select(AutoRole).where(
                AutoRole.guild_id == member.guild.id,
                AutoRole.trigger_type == "on_join"
            )
            roles_to_grant = (await session.execute(stmt)).scalars().all()

            for rule in roles_to_grant:
                await self._grant_role(member, rule.role_id, "Auto-role on join")

    async def handle_level_up(self, member: discord.Member, new_level: int):
        """Called by LevelingCog to grant 'on_level' roles."""
        async with self.db_session() as session:
            stmt = select(AutoRole).where(
                AutoRole.guild_id == member.guild.id,
                AutoRole.trigger_type == "on_level",
                AutoRole.required_level <= new_level
            )
            roles_to_grant = (await session.execute(stmt)).scalars().all()
            
            for rule in roles_to_grant:
                await self._grant_role(member, rule.role_id, f"Auto-role for reaching level {rule.required_level}")