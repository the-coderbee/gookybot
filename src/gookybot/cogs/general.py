import logging
import re
from typing import Optional
import discord
from discord.ext import commands
from gookybot.core.bot import GookyBot


logger = logging.getLogger(__name__)


class GeneralCog(commands.Cog, name="General"):
    def __init__(self, bot: GookyBot):
        self.bot = bot
        self.guild_manager = bot.guild_manager
    
    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """Catches and handles all command errors."""
        
        # This prevents any commands with local error handlers
        # from being handled by this global handler.
        if hasattr(ctx.command, 'on_error'):
            return

        # Get the original, underlying error
        error = getattr(error, 'original', error)

        # --- Handle Specific, Common Errors ---

        if isinstance(error, commands.NotOwner):
            logger.warning(f"{ctx.author} tried to run owner-only command '{ctx.command.name}'.")
            await ctx.send("Sorry, that command can only be used by the bot owner.", ephemeral=True)

        elif isinstance(error, commands.MissingPermissions):
            logger.warning(f"{ctx.author} tried running '{ctx.command.name}' but lacked permissions.")
            missing_perms = ", ".join(error.missing_permissions)
            await ctx.send(f"You don't have permission to do that. You're missing: `{missing_perms}`", ephemeral=True)
            
        elif isinstance(error, commands.CheckFailure):
            # A generic check failed (e.g., @commands.is_owner(), @commands.has_guild_permissions)
            logger.warning(f"{ctx.author} failed a check for command '{ctx.command.name}'.")
            await ctx.send("You do not have the necessary permissions to run this command.", ephemeral=True)
            
        elif isinstance(error, commands.BadArgument):
            # User provided an invalid argument (e.g., 'abc' for an 'int')
            await ctx.send(f"Invalid argument. Please check the help for `/{ctx.command.name}`.", ephemeral=True)

        # --- Handle All Other Errors ---
        
        else:
            # This is a real, unexpected bug. Log the full traceback.
            logger.error(f"Ignoring unhandled exception in command '{ctx.command.name}':", exc_info=error)
            
            # Send a generic error message
            try:
                await ctx.send("An unexpected error occurred. I've logged it for the developer.", ephemeral=True)
            except discord.NotFound:
                # This can happen if the original interaction failed or was deferred
                pass

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """Called when the bot joins a new guild."""
        logger.info(f"Bot joined a new guild: {guild.name} ({guild.id})")
        
        # 1. Create the guild entry in the database
        await self.guild_manager.get_or_create_guild(guild.id)
        
        # 2. Send a DM to the guild owner
        guild_owner = guild.owner
        if guild_owner:
            owner_message = (
                f"Hey {guild_owner.display_name}! Thanks for inviting me to **{guild.name}**.\n\n"
                "I'm Gooky, an all-purpose bot. My default prefix is `g!`, but you can also use slash commands.\n"
                "To get started, you can configure me using the `/leveling` and `/moderation` commands."
            )
            try:
                await guild_owner.send(owner_message)
                logger.info(f"Sent guild join DM to owner of {guild.name}")
            except discord.Forbidden:
                logger.warning(f"Failed to send DM to owner of {guild.name}. They may have DMs disabled.")

        # 3. Send a DM to all other admins
        for member in guild.members:
            # Skip the owner (already messaged) and bots
            if member == guild_owner or member.bot:
                continue
                
            # Check if the member has 'Administrator' permissions
            if member.guild_permissions.administrator:
                admin_message = (
                    f"Hey {member.display_name}! Gooky bot was just added to **{guild.name}**, "
                    f"a server where you are an admin.\n\n"
                    f"The server owner, {guild_owner.display_name}, has been sent setup information."
                )
                try:
                    await member.send(admin_message)
                    logger.info(f"Sent guild join DM to admin {member.display_name} in {guild.name}")
                except discord.Forbidden:
                    logger.warning(f"Failed to send DM to admin {member.display_name} in {guild.name}.")


    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Called when a new member joins a guild."""
        guild = member.guild
        
        # Create the welcome embed
        embed = discord.Embed(
            title=f"Welcome to {guild.name}, {member.display_name}!",
            description=(
                f"We're excited to have you here. Feel free to look around and introduce yourself!\n\n"
            ),
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="⚠️ Disclaimer: Please Read the Rules",
            value=(
                "Before you start chatting, please take a moment to read the server rules in the "
                f"`#rules` channel (or equivalent). By participating, you agree to abide by them."
            ),
            inline=False
        )
        
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"You are the {guild.member_count}th member!")

        # Send the embed to the user's DMs
        try:
            await member.send(embed=embed)
            logger.info(f"Sent welcome DM to new member {member.display_name} in {guild.name}")
        except discord.Forbidden:
            logger.warning(f"Failed to send welcome DM to {member.display_name}. They may have DMs disabled.")


    @commands.hybrid_command(name="ping", description="Checks the bot's latency.")
    async def ping(self, ctx: commands.Context):
        """Checks the bot's latency."""
        await ctx.send(f"Pong! Latency: {self.bot.latency * 1000:.2f}ms")

    @commands.hybrid_command(name="setprefix", description="Sets a new command prefix for this server.")
    @commands.has_guild_permissions(manage_guild=True)
    async def setprefix(self, ctx: commands.Context, new_prefix: str):
        """Sets a new command prefix for this server."""
        
        # Add some basic validation
        if len(new_prefix) > 10:
            await ctx.send("The prefix cannot be longer than 10 characters.", ephemeral=True)
            return
        
        if re.search(r"\s", new_prefix):
            await ctx.send("The prefix cannot contain spaces.", ephemeral=True)
            return

        success = await self.guild_manager.set_prefix(ctx.guild.id, new_prefix)
        
        if success:
            await ctx.send(f"My prefix for this server has been updated to: `{new_prefix}`")
        else:
            await ctx.send("An error occurred while trying to update the prefix.", ephemeral=True)
    
    @commands.hybrid_command(name="sync", description="Syncs application commands (Bot Owner only).")
    @commands.is_owner()
    async def sync(self, ctx: commands.Context, scope: Optional[str] = None):
        """
        Syncs application commands to Discord.
        This is a developer-only command.
        
        Scopes:
        - `guild`: (Default) Syncs commands to the current guild. (Instant)
        - `global`: Syncs commands globally. (Can take up to 1 hour)
        """
        if not scope:
            # Default: Sync to current guild
            try:
                guild = ctx.guild
                self.bot.tree.copy_global_to(guild=guild)
                await self.bot.tree.sync(guild=guild)
                logger.info(f"Synced command tree to current guild: {guild.name} ({guild.id}) by {ctx.author}")
                await ctx.send(f"Commands synced to **{guild.name}**.", ephemeral=True)
                return
            except Exception as e:
                logger.error(f"Failed to sync to guild {ctx.guild.id}: {e}", exc_info=True)
                await ctx.send(f"Failed to sync to this guild: {e}", ephemeral=True)
                return

        if scope.lower() == "global":
            # Sync globally
            try:
                await self.bot.tree.sync()
                logger.info(f"Synced command tree globally by {ctx.author}")
                await ctx.send("Commands synced **globally**. Please note it may take up to an hour to see changes.", ephemeral=True)
            except Exception as e:
                logger.error(f"Failed to sync globally: {e}", exc_info=True)
                await ctx.send(f"Failed to sync globally: {e}", ephemeral=True)
        else:
            await ctx.send("Invalid scope. Use `guild` (or nothing) to sync to this server, or `global` to sync everywhere.", ephemeral=True)



async def setup(bot: GookyBot):
    # bot.add_cog is synchronous, so we don't use await
    await bot.add_cog(GeneralCog(bot))
