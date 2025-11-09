from typing import Optional
import discord
from discord.ext import commands
from gookybot.core.bot import GookyBot
from gookybot.database.models.autorole import AutoRole
from gookybot.utils.embeds import create_embed
from sqlalchemy import select, delete
import logging

logger = logging.getLogger(__name__)


class SettingsCog(commands.Cog):
    def __init__(self, bot: GookyBot):
        self.bot = bot
    
    @commands.hybrid_group(name="settings", description="Configure bot settings for this server.")
    @commands.has_guild_permissions(manage_guild=True)
    async def settings(self, ctx:commands.Context):
        if ctx.invoked_subcommand is None:
            await self.view(ctx)
    
    @settings.command(name="view", description="View the current bot settings for this server.")
    @commands.has_guild_permissions(manage_guild=True)
    async def view(self, ctx: commands.Context):
        await ctx.defer(ephemeral=True)
        settings = await self.bot.guild_manager.get_or_create_guild(ctx.guild.id)

        welcome_status = "Welcoming Enabled" if settings.welcome_enabled else "Welcome Disabled"
        welcome_channel = ctx.guild.get_channel(settings.welcome_channel_id) if settings.welcome_channel_id else "Not set"

        leveling_status = "Leveling Enabled" if settings.leveling_enabled else "Disabled"
        level_channel = ctx.guild.get_channel(settings.leveling_channel_id) if settings.leveling_channel_id else "Not Set"
        level_notify = "Enabled" if settings.leveling_notify_on_levelup else "Disabled"

        autovc_channel = ctx.guild.get_channel(settings.auto_vc_channel_id) if settings.auto_vc_channel_id else "Disabled"

        async with self.bot.db_session() as session:
            stmt = select(AutoRole).where(AutoRole.guild_id == ctx.guild.id)
            rules = (await session.execute(stmt)).scalars().all()
        
        join_roles = []
        level_roles = []
        for rule in rules:
            role = ctx.guild.get_role(rule.role_id)
            if not role:
                continue
            if rule.trigger_type == 'on_join':
                join_roles.append(role.mention)
            elif rule.trigger_type == 'on_level':
                level_roles.append(f"{role.mention} (at Lvl {rule.required_level})")

        antispam_status = "Enabled" if settings.antispam_enabled else "Disabled"
        mod_log_channel_id = settings.mod_log_channel_id if settings else None
        mod_log_channel = ctx.guild.get_channel(mod_log_channel_id) if mod_log_channel_id else "Not Set"

        embed = create_embed(
            title=f"Settings for {ctx.guild.name}"
        )
        embed.add_field(
            name="Welcome System",
            value=f"Status: {welcome_status}\n"
            f"Channel: {welcome_channel.mention if isinstance(welcome_channel, discord.TextChannel) else welcome_channel}",
            inline=False 
        )
        embed.add_field(
            name="Leveling System",
            value=f"Status: {leveling_status}\n"
            f"Notify on Level Up: {level_notify}\n"
            f"Command Channel: {level_channel.mention if isinstance(level_channel, discord.TextChannel) else level_channel}",
            inline=False
        )
        embed.add_field(
            name="Auto Voice Channels",
            value=f"'Join-to-Create' Channel: {autovc_channel.mention if isinstance(autovc_channel, discord.VoiceChannel) else autovc_channel}",
            inline=False
        )
        embed.add_field(
            name="🤖 Auto Roles",
            value=f"**On Join:** {', '.join(join_roles) or 'None'}\n"
                  f"**On Level Up:** {', '.join(level_roles) or 'None'}",
            inline=False
        )
        embed.add_field(
            name="🛡️ Anti-Spam System",
            value=f"**Status:** {antispam_status}\n"
                  f"**Mod Log Channel:** {mod_log_channel.mention if isinstance(mod_log_channel, discord.TextChannel) else mod_log_channel}",
            inline=False
        )

        await ctx.send(embed=embed)
    
    @settings.command(name="togglewelcome", description="Enable or disable the welcome message system.")
    @commands.has_guild_permissions(manage_guild=True)
    async def set_welcome(
        self,
        ctx: commands.Context,
        enabled: bool,
        channel: discord.TextChannel
    ):
        await ctx.defer(ephemeral=True)
        settings = await self.bot.guild_manager.get_or_create_guild(ctx.guild.id)

        settings.welcome_enabled = enabled
        settings.welcome_channel_id = channel.id

        async with self.bot.db_session() as session:
            session.add(settings)
            await session.commit()
        
        status = "enabled" if enabled else "disabled"
        await ctx.send(f"Success! Welcome messages have been {status} and set to {channel.mention}.")

    @settings.command(name="leveling", description="Configure the levling system.")
    @commands.has_guild_permissions(manage_channels=True)
    async def set_leveling(
        self,
        ctx: commands.Context,
        enabled: bool,
        notify_on_levelup: Optional[bool] = None,
        command_channel: Optional[discord.TextChannel] = None
    ):
        await ctx.defer(ephemeral=True)
        settings = await self.bot.guild_manager.get_or_create_guild(ctx.guild.id)

        settings.leveling_enabled = enabled
        if not enabled:
            settings.leveling_notify_on_levelup = notify_on_levelup
        
        if notify_on_levelup:
            settings.leveling_notify_on_levelup = notify_on_levelup
        if command_channel is not None:
            settings.leveling_channel_id = command_channel.id
        
        if not enabled:
            settings.leveling_channel_id = None
            settings.leveling_notify_on_levelup = False
        
        async with self.bot.db_session() as session:
            session.add(settings)
            await session.commit()
        
        status = "Enabled" if enabled else "Disabled"
        await ctx.send(f"Success! The leveling system has been {status}")
    
    @settings.command(name="autovc", description="Set or disable the 'Join-to-Create' voice channel.")
    @commands.has_guild_permissions(manage_guild=True)
    async def set_autovc(
        self,
        ctx: commands.Context,
        channel: Optional[discord.VoiceChannel] = None
    ):
        """
        Set the 'Join-to-Create' channel.
        If no channel is provided, this feature will be disabled.
        """
        await ctx.defer(ephemeral=True)
        settings = await self.bot.guild_manager.get_or_create_guild(ctx.guild.id)

        if channel:
            settings.auto_vc_channel_id = channel.id
            message = f"Success! {channel.mention} is now the 'Join-to-Create' channel."
        else:
            settings.auto_vc_channel_id = None
            message = "Success! The Auto VC feature has been disabled."
            
        async with self.bot.db_session() as session:
            session.add(settings)
            await session.commit()
            
        await ctx.send(message)
    
    @settings.group(name="autorole", description="Configure roles to be automatically assigned.")
    @commands.has_guild_permissions(manage_roles=True)
    async def autorole(self, ctx: commands.Context):
        """Main group command for auto-role settings."""
        if ctx.invoked_subcommand is None:
            await ctx.send(
                "Please use a subcommand: `add_join_role`, `add_level_role`, `remove_role`, or `list` (which is `/settings view`).",
                ephemeral=True
            )
    
    @autorole.command(name="add_join_role", description="Assign a role to new members when they join.")
    @commands.has_guild_permissions(manage_roles=True)
    async def add_join_role(self, ctx: commands.Context, role: discord.Role):
        """Adds a role to be given to members when they join."""
        await ctx.defer(ephemeral=True)
        
        if role >= ctx.guild.me.top_role:
            await ctx.send(f"I cannot assign {role.mention} because it is higher than or equal to my own top role.", ephemeral=True)
            return

        async with self.bot.db_session() as session:
            new_rule = AutoRole(
                guild_id=ctx.guild.id,
                role_id=role.id,
                trigger_type="on_join"
            )
            try:
                session.add(new_rule)
                await session.commit()
                await ctx.send(f"Success! {role.mention} will now be given to all new members.", ephemeral=True)
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to add join role: {e}", exc_info=True)
                await ctx.send(f"Failed to add this role. Does it already have a rule?", ephemeral=True)

    @autorole.command(name="add_level_role", description="Assign a role when a member reaches a specific level.")
    @commands.has_guild_permissions(manage_roles=True)
    async def add_level_role(self, ctx: commands.Context, level: int, role: discord.Role):
        """Adds a role to be given at a specific level."""
        await ctx.defer(ephemeral=True)

        if level <= 0:
            await ctx.send("Level must be 1 or higher.", ephemeral=True)
            return
            
        if role >= ctx.guild.me.top_role:
            await ctx.send(f"I cannot assign {role.mention} because it is higher than or equal to my own top role.", ephemeral=True)
            return

        async with self.bot.db_session() as session:
            new_rule = AutoRole(
                guild_id=ctx.guild.id,
                role_id=role.id,
                trigger_type="on_level",
                required_level=level
            )
            try:
                session.add(new_rule)
                await session.commit()
                await ctx.send(f"Success! {role.mention} will now be given at level {level}.", ephemeral=True)
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to add level role: {e}", exc_info=True)
                await ctx.send(f"Failed to add this role. Does it already have a rule?", ephemeral=True)

    @autorole.command(name="remove_role", description="Removes any auto-role rule associated with a role.")
    @commands.has_guild_permissions(manage_roles=True)
    async def remove_role(self, ctx: commands.Context, role: discord.Role):
        """Removes an auto-role rule."""
        await ctx.defer(ephemeral=True)
        
        async with self.bot.db_session() as session:
            stmt = delete(AutoRole).where(
                AutoRole.guild_id == ctx.guild.id,
                AutoRole.role_id == role.id
            )
            result = await session.execute(stmt)
            await session.commit()
            
            if result.rowcount > 0:
                await ctx.send(f"Success! The auto-role rule for {role.mention} has been removed.", ephemeral=True)
            else:
                await ctx.send(f"No auto-role rule was found for {role.mention}.", ephemeral=True)

    @settings.command(name="antispam", description="Configure the anti-spam system.")
    @commands.has_guild_permissions(manage_guild=True)
    async def set_antispam(
        self,
        ctx: commands.Context,
        enabled: bool,
        mod_log_channel: Optional[discord.TextChannel] = None
    ):
        """Enable/disable anti-spam and set the mod log channel."""
        await ctx.defer(ephemeral=True)
        settings = await self.bot.guild_manager.get_or_create_guild(ctx.guild.id)
        
        settings.antispam_enabled = enabled
        if mod_log_channel:
            settings.mod_log_channel_id = mod_log_channel.id
        elif enabled and not mod_log_channel:
            settings.mod_log_channel_id = ctx.guild.system_channel.id if ctx.guild.system_channel else None
        
        if not enabled:
            settings.mod_log_channel_id = None
            
        async with self.bot.db_session() as session:
            session.add(settings)
            await session.commit()
            
        status = "enabled" if enabled else "disabled"
        await ctx.send(f"Success! The anti-spam system has been **{status}**.")

async def setup(bot: GookyBot):
    await bot.add_cog(SettingsCog(bot))
