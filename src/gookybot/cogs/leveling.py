import discord
from discord.ext import commands, tasks
import logging
import time
import datetime
from collections import defaultdict
from typing import List, Optional

from gookybot.core.bot import GookyBot
from gookybot.features.levelling.manager import LevelingManager
from gookybot.database.models import LevelingProfile, Guild
from gookybot.utils.embeds import create_embed

logger = logging.getLogger(__name__)


class LeaderboardView(discord.ui.View):
    def __init__(self, bot: GookyBot, data: List[LevelingProfile], per_page: int = 10):
        super().__init__(timeout=180)
        self.bot = bot
        self.data = data
        self.per_page = per_page
        self.current_page = 0
        self.total_pages = (len(self.data) - 1) // self.per_page + 1
        self.update_buttons()

    async def get_page_embed(self) -> discord.Embed:
        """Creates an embed for the current page."""
        start_index = self.current_page * self.per_page
        end_index = start_index + self.per_page
        page_data = self.data[start_index:end_index]

        embed = create_embed(
            title="Server Leaderboard",
        )

        description = []
        for i, profile in enumerate(page_data):
            rank = start_index + i + 1
            try:
                user = await self.bot.fetch_user(profile.user_discord_id)
                username = user.display_name
            except discord.NotFound:
                username = "Unknown User"
            
            description.append(
                f"**#{rank}** {username} - **Lvl {profile.level}** ({profile.xp} XP)"
            )
        
        embed.description = "\n".join(description)
        embed.set_footer(text=f"Page {self.current_page + 1} / {self.total_pages}")
        return embed

    def update_buttons(self):
        """Disables/Enables buttons based on the current page."""
        self.prev_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page == (self.total_pages - 1)

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.grey, row=0)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page -= 1
        self.update_buttons()
        embed = await self.get_page_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.blurple, row=0)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page += 1
        self.update_buttons()
        embed = await self.get_page_embed()
        await interaction.response.edit_message(embed=embed, view=self)


class LevelingCog(commands.Cog, name="Leveling"):

    def __init__(self, bot: GookyBot):
        self.bot = bot
        self.level_manager = LevelingManager(bot)
        self.message_cooldowns = defaultdict(dict)
        self.reaction_cooldowns = defaultdict(dict)
        self.interaction_cooldowns = defaultdict(dict)

        self.voice_xp_loop.start()
    
    def cog_unload(self):
        self.voice_xp_loop.cancel()
    
    async def _check_leveling_enabled(self, guild_id: int) -> Optional[Guild]:
        guild_settings = await self.bot.guild_manager.get_or_create_guild(guild_id)
        if not guild_settings or not guild_settings.leveling_enabled:
            return None
        return guild_settings
    
    async def _check_channel(self, ctx: commands.Context, guild_settings: Guild) -> bool:
        if guild_settings.leveling_channel_id and ctx.channel.id != guild_settings.leveling_channel_id:
            channel = self.bot.get_channel(guild_settings.leveling_channel_id)
            await ctx.send(f"Please use leveling commands in {channel.mention if channel else '#level'}", ephemeral=True)
            return False
        return True
    
    async def _send_level_notification(self, user: discord.User, guild: discord.Guild, new_level: int, guild_settings: Guild):
        if not guild_settings.leveling_notify_on_levelup:
            return
        
        channel = None
        if guild_settings.leveling_channel_id:
            channel = guild.get_channel(guild_settings.leveling_channel_id)
        
        if not channel:
            channel = guild.system_channel
        
        if channel:
            try:
                embed = create_embed(
                    title="Level Up!",
                    description=f"🎉 Congratulations {user.mention}, you've reached **Level {new_level}**!"
                )
                await channel.send(embed=embed)
            except discord.Forbidden:
                logger.warning(f"Failed to send levelup notification in {guild.name}: Missing perms in {channel.name}.")
            except Exception as e:
                logger.error(f"Error sending level-up notification: {e}", exc_info=True)
        else:
             logger.warning(f"Failed to send level-up notification in {guild.name}: No channel found.")
    
    @tasks.loop(minutes=1)
    async def voice_xp_loop(self):
        try:
            for guild in self.bot.guilds:
                guild_settings = await self._check_leveling_enabled(guild.id)
                if not guild_settings:
                    continue

                for vc in guild.voice_channels:
                    if vc == guild.afk_channel:
                        continue

                    members_to_reward = []
                    for member in vc.members:
                        if member.bot:
                            continue
                        if member.voice.self_deaf or member.voice.deaf:
                            continue

                        members_to_reward.append(member)
                    
                    if len(members_to_reward) < 2:
                        continue
                    
                    for member in members_to_reward:
                        additional_xp = 0
                        if member.voice.self_stream:
                            additional_xp = 15

                        new_level = await self.level_manager.add_xp(member.id, guild.id, 8 + additional_xp)
                        if new_level:
                            await self.bot.autorole_manager.handle_level_up(member, new_level)
                            await self._send_level_notification(member, guild, new_level, guild_settings)
        except Exception as e:
            logger.error(f"Error in voice_xp_loop, {e}", exc_info=True)
    
    @voice_xp_loop.before_loop
    async def before_voice_xp_loop(self):
        await self.bot.wait_until_ready()
        logger.info("Voice xp loop is ready and starting")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        
        guild_settings = await self._check_leveling_enabled(message.guild.id)
        
        if not guild_settings:
            return
        
        if guild_settings.antispam_enabled:
            if not message.author.guild_permissions.manage_messages:
                is_spam = self.bot.spam_manager.check_for_spam(message)
                
                if is_spam:
                    
                    # --- THIS IS THE ONLY CHANGE ---
                    # We now pass a 'reason' string to the manager
                    reason = "Automated spam detection (5 messages in 5s)"
                    warning_count = await self.bot.spam_manager.issue_warning(message.author, reason)
                    # --- END OF CHANGE ---
                    
                    if warning_count >= 3:
                        timeout_duration = datetime.timedelta(minutes=5)
                        reason = f"3rd spam warning. User has {warning_count} total warnings."
                        try:
                            await message.author.timeout(timeout_duration, reason=reason)
                            await message.channel.send(f"⚠️ {message.author.mention} has been timed out for 5 minutes for persistent spam.")
                        except Exception as e:
                            logger.warning(f"Failed to timeout {message.author} for spam: {e}")
                        
                        if guild_settings.mod_log_channel_id:
                            log_channel = message.guild.get_channel(guild_settings.mod_log_channel_id)
                            if log_channel:
                                embed = create_embed(
                                    title="Anti-Spam Action Report",
                                    color=discord.Color.red()
                                )
                                embed.add_field(name="User", value=message.author.mention, inline=False)
                                embed.add_field(name="Action", value="Timed out for 5 minutes (3rd strike)", inline=False)
                                embed.add_field(name="Total Warnings", value=f"`{warning_count}`", inline=False)
                                await log_channel.send(embed=embed)
                    
                    else:
                        timeout_duration = datetime.timedelta(minutes=1)
                        reason = f"Spam detection triggered. Warning #{warning_count}."
                        try:
                            await message.author.timeout(timeout_duration, reason=reason)
                            await message.channel.send(f"Please stop spamming {message.author.mention}. This is warning #{warning_count}. (1 min timeout)")
                        except Exception as e:
                            logger.warning(f"Failed to timeout {message.author} for spam: {e}")
                    
                    return
        
        if not guild_settings.leveling_enabled:
            await self.bot.process_commands(message)
            return

        is_command = False
        if message.content.startswith(guild_settings.prefix):
            is_command=True
        
        if not is_command:
            user_id = message.author.id
            guild_id = message.guild.id
            current_time = time.time()

            if not message.content and not message.attachments:
                await self.bot.process_commands(message)
                return

            last_message_time = self.message_cooldowns.get(guild_id, {}).get(user_id, 0)
            if current_time - last_message_time < 30:
                await self.bot.process_commands(message)
                return
            
            self.message_cooldowns[guild_id][user_id] = current_time

            engagement_channels = guild_settings.engagement_channels
            additional_xp = 0
            if message.channel.id in engagement_channels:
                additional_xp = 15
            
            new_level = await self.level_manager.add_xp(user_id, guild_id, 25 + additional_xp)
            if new_level:
                await self.bot.autorole_manager.handle_level_up(message.author, new_level)
                await self._send_level_notification(message.author, message.guild, new_level, guild_settings)

        await self.bot.process_commands(message)
    
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.application_command:
            return
        if not interaction.guild or interaction.user.bot:
            return
        
        guild_settings = await self._check_leveling_enabled(interaction.guild.id)
        if not guild_settings:
            return
        
        user_id = interaction.user.id
        guild_id = interaction.guild.id
        current_time = time.time()

        last_interaction_time = self.interaction_cooldowns.get(guild_id, {}).get(user_id, 0)
        if current_time - last_interaction_time < 30:
            return
        self.interaction_cooldowns[guild_id][user_id] = current_time

        engagement_channels = guild_settings.engagement_channels
        additional_xp = 0
        if interaction.channel.id in engagement_channels:
            additional_xp = 15
        
        new_level = await self.level_manager.add_xp(user_id, guild_id, additional_xp + 25)
        if new_level:
            member = interaction.guild.get_member(interaction.user.id)
            if member:
                await self.bot.autorole_manager.handle_level_up(member, new_level)
            await self._send_level_notification(interaction.user, interaction.guild, new_level, guild_settings)
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id or not payload.guild_id:
            return

        guild_settings = await self._check_leveling_enabled(payload.guild_id)
        if not guild_settings:
            return

        user_id = payload.user_id
        guild_id = payload.guild_id
        current_time = time.time()

        last_reaction_time = self.reaction_cooldowns.get(guild_id, {}).get(user_id, 0)
        if current_time - last_reaction_time < 60:
            return
        
        self.reaction_cooldowns[guild_id][user_id] = current_time

        new_level = await self.level_manager.add_xp(user_id, guild_id, 5)
        
        if new_level:
            guild = self.bot.get_guild(guild_id)
            user = await self.bot.fetch_user(user_id)
            member = guild.get_member(user_id) if guild else None

            if member and guild and user:
                await self.bot.autorole_manager.handle_level_up(member, new_level)
                await self._send_level_notification(user, guild, new_level, guild_settings)
    

    @commands.hybrid_command(name="level", description="Check member's current level and XP.")
    async def get_user_level(self, ctx: commands.Context, member: discord.Member = None):
        """Checks your (or another member's) current level and XP."""
        
        guild_settings = await self._check_leveling_enabled(ctx.guild.id)
        if not guild_settings:
            await ctx.send("Leveling is disabled on this server.", ephemeral=True)
            return
        if not await self._check_channel(ctx, guild_settings):
            return
        
        target_user = member or ctx.author
        profile = await self.level_manager.get_user_profile(target_user.id, ctx.guild.id)
        
        if not profile:
            await ctx.send(f"{target_user.display_name} has no XP yet!")
            return

        xp_for_next = self.level_manager.xp_for_level(profile.level + 1)
        
        embed = create_embed(title=f"Level for {target_user.display_name}", color=target_user.color)
        embed.set_thumbnail(url=target_user.display_avatar.url)
        embed.add_field(name="Level", value=f"`{profile.level}`", inline=True)
        embed.add_field(name="XP", value=f"`{profile.xp} / {xp_for_next}`", inline=True)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="rank", description="Check a member's server rank.")
    async def rank(self, ctx: commands.Context, member: discord.Member = None):
        """Checks your (or another member's) position on the leaderboard."""
        
        guild_settings = await self._check_leveling_enabled(ctx.guild.id)
        if not guild_settings:
            await ctx.send("Leveling is disabled on this server.", ephemeral=True)
            return
        if not await self._check_channel(ctx, guild_settings):
            return
        target_user = member or ctx.author
        rank = await self.level_manager.get_user_rank(target_user.id, ctx.guild.id)
        
        if not rank:
            await ctx.send(f"{target_user.display_name} is not on the leaderboard yet!")
            return
            
        await ctx.send(f"{target_user.display_name} is **Rank #{rank}** on the server.")

    @commands.hybrid_command(name="leaderboard", description="Shows the server XP leaderboard.")
    async def leaderboard(self, ctx: commands.Context):
        """Displays the top users in the server, sorted by XP."""
        
        guild_settings = await self._check_leveling_enabled(ctx.guild.id)
        if not guild_settings:
            await ctx.send("Leveling is disabled on this server.", ephemeral=True)
            return
        if not await self._check_channel(ctx, guild_settings):
            return
        
        await ctx.defer()
        
        all_profiles = await self.level_manager.get_leaderboard(ctx.guild.id)
        
        if not all_profiles:
            await ctx.send("The leaderboard is empty! No one has earned XP yet.")
            return

        view = LeaderboardView(self.bot, all_profiles)
        embed = await view.get_page_embed()
        
        await ctx.send(embed=embed, view=view)
    
    @commands.hybrid_group(name="leveling", description="Commands to configure the leveling system.")
    @commands.has_guild_permissions(manage_guild=True)
    async def leveling(self, ctx: commands.Context):
        guild_settings = await self._check_leveling_enabled(ctx.guild.id)
        if not guild_settings:
            guild_settings = await self.bot.guild_manager.get_or_create_guild(ctx.guild.id)

        if ctx.invoked_subcommand is None:
            await ctx.send("Please specify a subcommand (e.g. `addchannel`, `removechannel`, `listchannel`).", ephemeral=True)
    
    @leveling.command(name="addchannel", description="Add a channel to the engagement channels list.")
    @commands.has_guild_permissions(manage_guild=True)
    async def add_eng_channel(self, ctx:commands.Context, channel: discord.TextChannel):
        success = await self.bot.guild_manager.add_engagement_channel(ctx.guild.id, channel.id)
        if success:
            await ctx.send(f"Success! {channel.mention} will now grant bonus xp.", ephemeral=True)
        else:
            await ctx.send(f"{channel.mention} is already in the list", ephemeral=True)
    

    @leveling.command(name="removechannel", description="Removes a channel from the engagement list.")
    @commands.has_guild_permissions(manage_guild=True)
    async def remove_eng_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        success = await self.bot.guild_manager.remove_engagement_channel(ctx.guild.id, channel.id)
        if success:
            await ctx.send(f"Success! Channel {channel.mention} has been removed from the list.")
        else:
            await ctx.send(f"{channel.mention} is not in the list.")
    
    @leveling.command(name="listchannel", description="Lists all channels in the engagement list.")
    @commands.has_guild_permissions(manage_guild=True)
    async def list_eng_channels(self, ctx: commands.Context):
        guild_settings = await self.bot.guild_manager.get_or_create_guild(ctx.guild.id)

        channel_ids = guild_settings.engagement_channels if guild_settings else []
        if not channel_ids:
            await ctx.send("There are no channels in the list.")
            return

        description = "Users get bonus XP for engaging in these channels.\n"
        for i, channel_id in enumerate(channel_ids):
            channel = ctx.guild.get_channel(channel_id)
            description += f"{i+1}. {channel.mention if channel else f'Unknown Channel (ID: {channel_id})'}\n"
        
        embed = create_embed(title="Engagement Channels", description=description,)
        await ctx.send(embed=embed, ephemeral=True)


async def setup(bot: GookyBot):
    await bot.add_cog(LevelingCog(bot))