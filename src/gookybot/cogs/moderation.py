import discord
from discord.ext import commands
from gookybot.core.bot import GookyBot
import logging
from typing import Optional
import re # For parsing duration
from datetime import timedelta # For timeout duration
from gookybot.utils.embeds import create_embed
logger = logging.getLogger(__name__)

class ModerationCog(commands.Cog, name="Moderation"):
    """
Set of moderation commands for server admins."""

    def __init__(self, bot: GookyBot):
        self.bot = bot
        # Regex to parse duration strings like "1d", "3h", "10m", "30s"
        self.duration_regex = re.compile(
            r"((?P<weeks>\d+?)w)?"
            r"((?P<days>\d+?)d)?"
            r"((?P<hours>\d+?)h)?"
            r"((?P<minutes>\d+?)m)?"
            r"((?P<seconds>\d+?)s)?"
        )

    def _parse_duration(self, duration_str: str) -> Optional[timedelta]:
        """Parses a duration string (e.g., 1d12h) into a timedelta object."""
        match = self.duration_regex.fullmatch(duration_str)
        if not match:
            return None

        data = {key: int(value) for key, value in match.groupdict(default=0).items()}
        duration = timedelta(
            weeks=data["weeks"],
            days=data["days"],
            hours=data["hours"],
            minutes=data["minutes"],
            seconds=data["seconds"]
        )
        return duration if duration.total_seconds() > 0 else None

    @commands.hybrid_command(
        name="kick",
        description="Kicks a member from the server."
    )
    @commands.has_permissions(kick_members=True)
    @commands.guild_only()
    async def kick(self, ctx: commands.Context, member: discord.Member, *, reason: Optional[str] = "No reason provided."):
        """
        Kicks a member from the server.
        You must have the "Kick Members" permission to use this.
        """
        if ctx.author.top_role <= member.top_role:
            await ctx.send(f"You cannot kick {member.mention} because they have an equal or higher role than you.", ephemeral=True)
            return
        
        if member == ctx.guild.owner:
            await ctx.send("You cannot kick the server owner.", ephemeral=True)
            return

        try:
            await member.kick(reason=f"Kicked by {ctx.author} | Reason: {reason}")
            logger.info(f"User {member} (ID: {member.id}) was kicked by {ctx.author} for: {reason}")
            
            embed = create_embed(
                title="Member Kicked",
                description=f"**{member.mention}** was kicked by {ctx.author.mention}.",
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            await ctx.send(embed=embed)
        except discord.Forbidden:
            await ctx.send(f"I do not have permission to kick {member.mention}. Please check my roles and permissions.", ephemeral=True)
        except Exception as e:
            await ctx.send(f"An error occurred while trying to kick {member.mention}: {e}", ephemeral=True)

    @commands.hybrid_command(
        name="ban",
        description="Bans a member from the server."
    )
    @commands.has_permissions(ban_members=True)
    @commands.guild_only()
    async def ban(self, ctx: commands.Context, member: discord.Member, *, reason: Optional[str] = "No reason provided."):
        """
        Bans a member from the server.
        You must have the "Ban Members" permission to use this.
        """
        if ctx.author.top_role <= member.top_role:
            await ctx.send(f"You cannot ban {member.mention} because they have an equal or higher role than you.", ephemeral=True)
            return
        
        if member == ctx.guild.owner:
            await ctx.send("You cannot ban the server owner.", ephemeral=True)
            return

        try:
            await member.ban(reason=f"Banned by {ctx.author} | Reason: {reason}")
            logger.info(f"User {member} (ID: {member.id}) was banned by {ctx.author} for: {reason}")
            
            embed = create_embed(
                title="Member Banned",
                description=f"**{member.mention}** was banned by {ctx.author.mention}.",
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            await ctx.send(embed=embed)
        except discord.Forbidden:
            await ctx.send(f"I do not have permission to ban {member.mention}. Please check my roles and permissions.", ephemeral=True)
        except Exception as e:
            await ctx.send(f"An error occurred while trying to ban {member.mention}: {e}", ephemeral=True)

    # --- NEW TIMEOUT COMMAND ---

    @commands.hybrid_command(
        name="timeout",
        description="Times out a member for a specified duration (e.g., 10m, 1h, 3d)."
    )
    @commands.has_permissions(moderate_members=True)
    @commands.guild_only()
    async def timeout(self, ctx: commands.Context, member: discord.Member, duration: str, *, reason: Optional[str] = "No reason provided."):
        """
        Times out a member for a duration (e.g., 10m, 1h, 3d).
        You must have the "Moderate Members" permission.
        """
        if ctx.author.top_role <= member.top_role:
            await ctx.send(f"You cannot time out {member.mention} because they have an equal or higher role than you.", ephemeral=True)
            return
        
        if member == ctx.guild.owner:
            await ctx.send("You cannot time out the server owner.", ephemeral=True)
            return

        # Parse the duration string
        delta = self._parse_duration(duration)
        if delta is None:
            await ctx.send("Invalid duration format. Use `w`, `d`, `h`, `m`, `s`.\nExample: `1d12h` or `30m`.", ephemeral=True)
            return
        
        # Discord's maximum timeout is 28 days
        if delta.total_seconds() > 2419200: # 28 days
            await ctx.send("The maximum timeout duration is 28 days.", ephemeral=True)
            return

        try:
            await member.timeout(delta, reason=f"Timed out by {ctx.author} | Reason: {reason}")
            logger.info(f"User {member} (ID: {member.id}) was timed out by {ctx.author} for {duration}. Reason: {reason}")

            embed = create_embed(
                title="Member Timed Out",
                description=f"**{member.mention}** was timed out by {ctx.author.mention}.",
            )
            embed.add_field(name="Duration", value=duration, inline=True)
            embed.add_field(name="Reason", value=reason, inline=True)
            await ctx.send(embed=embed)
        
        except discord.Forbidden:
            await ctx.send(f"I do not have permission to time out {member.mention}. Please check my roles and permissions.", ephemeral=True)
        except Exception as e:
            await ctx.send(f"An error occurred while trying to time out {member.mention}: {e}", ephemeral=True)


    @commands.hybrid_command(
        name="clear",
        description="Clears a specified number of messages from the channel."
    )
    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    async def clear(self, ctx: commands.Context, amount: int):
        """
        Clears a specified number of messages.
        You must have the "Manage Messages" permission.
        """
        if amount <= 0:
            await ctx.send("The amount must be a positive number.", ephemeral=True)
            return
        
        if amount > 100:
            await ctx.send("I can only clear up to 100 messages at a time.", ephemeral=True)
            return

        try:
            # Defer the response for slash commands, as deleting can take time
            await ctx.defer(ephemeral=True)
            
            # Purge the messages
            deleted_messages = await ctx.channel.purge(limit=amount)
            
            # Send a temporary confirmation message
            await ctx.send(f"Successfully cleared {len(deleted_messages)} messages.", ephemeral=True, delete_after=5)
            logger.info(f"{ctx.author} cleared {len(deleted_messages)} messages in {ctx.channel.name}")

        except discord.Forbidden:
            await ctx.send("I do not have permission to delete messages in this channel.", ephemeral=True)
        except Exception as e:
            await ctx.send(f"An error occurred: {e}", ephemeral=True)
    
    @commands.hybrid_command(name="embed", description="Creates and sends a custom embed.")
    @commands.has_guild_permissions(manage_guild=True)
    async def embed(
        self, 
        ctx: commands.Context,
        channel: discord.TextChannel,
        title: Optional[str] = None,
        description: Optional[str] = None,
        color: Optional[str] = None,
        image_url: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        author: Optional[str] = None,
        footer: Optional[str] = None,
        field_name: Optional[str] = None,
        field_value: Optional[str] = None
    ):
        """Creates and sends a custom embed. Use \n for new lines."""
        
        # At least one of the main components must be present
        if not any([title, description, image_url, author, field_name]):
            await ctx.send("You can't send an empty embed. Please provide at least a title, description, image, or field.", ephemeral=True)
            return
            
        # Validate field
        if (field_name and not field_value) or (not field_name and field_value):
            await ctx.send("To add a field, you must provide *both* a `field_name` and a `field_value`.", ephemeral=True)
            return
            
        # Process \n for new lines
        if description:
            description = description.replace(r"\n", "\n")
        if field_value:
            field_value = field_value.replace(r"\n", "\n")

        # Create embed
        if color:
            try:
                embed_color = discord.Color.from_string(color)
            except ValueError:
                await ctx.send("Invalid color. Use a hex code (e.g., `#FF0000`) or a color name (e.g., `red`).", ephemeral=True)
                return
            embed = create_embed(title=title, description=description, color=embed_color)
        else:
            embed = create_embed(title=title, description=description)

        # Set optional attributes
        if image_url:
            embed.set_image(url=image_url)
        if thumbnail_url:
            embed.set_thumbnail(url=thumbnail_url)
        if author:
            embed.set_author(name=author)
        if footer:
            embed.set_footer(text=footer)
        if field_name and field_value:
            embed.add_field(name=field_name, value=field_value, inline=False)

        # Send the embed
        try:
            await channel.send(embed=embed)
            await ctx.send(f"Embed successfully sent to {channel.mention}.", ephemeral=True)
            logger.info(f"{ctx.author.name} sent a custom embed to {channel.name}")
        except discord.Forbidden:
            await ctx.send(f"I don't have permission to send messages in {channel.mention}.", ephemeral=True)
        except Exception as e:
            await ctx.send(f"An error occurred: {e}", ephemeral=True)
            logger.error(f"Error sending embed: {e}", exc_info=True)
    
    # --- NEW COMMAND ---
    @commands.hybrid_command(name="say", description="Sends a plain text message as the bot.")
    @commands.has_guild_permissions(manage_guild=True)
    async def say(
        self,
        ctx: commands.Context,
        channel: discord.TextChannel,
        message: str
    ):
        """Sends a plain text message to a channel. Use \n for new lines."""
        
        # Process \n for new lines, just like in the embed command
        message_content = message.replace(r"\n", "\n")

        # Send the message
        try:
            await channel.send(message_content)
            await ctx.send(f"Message successfully sent to {channel.mention}.", ephemeral=True)
            logger.info(f"{ctx.author.name} sent a 'say' command to {channel.name}")
        except discord.Forbidden:
            await ctx.send(f"I don't have permission to send messages in {channel.mention}.", ephemeral=True)
        except Exception as e:
            await ctx.send(f"An error occurred: {e}", ephemeral=True)
            logger.error(f"Error sending 'say' message: {e}", exc_info=True)


async def setup(bot: GookyBot):
    await bot.add_cog(ModerationCog(bot))
