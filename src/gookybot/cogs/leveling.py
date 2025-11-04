from collections import defaultdict
import logging
import discord
from typing import List
from discord.ext import commands, tasks
import time
from gookybot.utils.embeds import create_embed
from gookybot.core.bot import GookyBot
from gookybot.database.models.leveling_profile import LevelingProfile
from gookybot.features.levelling.manager import LevelingManager

logger = logging.getLogger(__name__)


class LeaderboardView(discord.ui.View):
    def __init__(self, bot: GookyBot, data: List[LevelingProfile], per_page: int = 10):
        super().__init__(timeout=180)  # 3 minute timeout
        self.bot = bot
        self.data = data
        self.per_page = per_page
        self.current_page = 0
        self.total_pages = (len(self.data) - 1) // self.per_page + 1

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
                # Fetch user to get their current name
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

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.grey, row=0, disabled=True)
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


class LevelingCog(commands.Cog):

    def __init__(self, bot: GookyBot):
        self.bot = bot
        self.level_manager = LevelingManager(bot)
        self.message_cooldowns = defaultdict(dict)
        self.reaction_cooldowns = defaultdict(dict)
        self.interaction_cooldowns = defaultdict(dict)

        self.voice_xp_loop.start()
    
    def cog_unload(self):
        self.voice_xp_loop.cancel()
    
    @tasks.loop(minutes=1)
    async def voice_xp_loop(self):
        try:
            for guild in self.bot.guilds:
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
                    
                    for member in members_to_reward:
                        additional_xp = 0
                        if member.voice.self_stream:
                            additional_xp = 15
                        await self.level_manager.add_xp(member.id, guild.id, 8 + additional_xp)
        except Exception as e:
            logger.error(f"Error in voice_xp_loop", exc_info=True)
    
    @voice_xp_loop.before_loop
    async def before_voice_xp_loop(self):
        await self.bot.wait_until_ready()
        logger.info("Vocie xp loop is ready and starting")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        
        guild_settings = await self.bot.guild_manager.get_or_create_guild(message.guild.id)

        is_command = False
        if guild_settings and message.content.startswith(guild_settings.prefix):
            is_command=True
        
        if not is_command:
            user_id = message.author.id
            guild_id = message.guild.id
            current_time = time.time()

            if not message.content and not message.attachments:
                return

            last_message_time = self.message_cooldowns.get(guild_id, {}).get(user_id, 0)
            if current_time - last_message_time < 30:
                return
            
            self.message_cooldowns[guild_id][user_id] = current_time

            
            engagement_channels = guild_settings.engagement_channels if guild_settings else []

            additional_xp = 0
            if message.channel.id in engagement_channels:
                additional_xp = 15
            
            await self.level_manager.add_xp(user_id, guild_id, 25 + additional_xp)

        await self.bot.process_commands(message)
    
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.application_command:
            return
        if not interaction.guild or interaction.user.bot:
            return
        
        user_id = interaction.user.id
        guild_id = interaction.guild.id
        current_time = time.time()

        last_interaction_time = self.interaction_cooldowns.get(guild_id, {}).get(user_id, 0)
        if current_time - last_interaction_time < 30:
            return
        self.interaction_cooldowns[guild_id][user_id] = current_time

        guild_settings = await self.bot.guild_manager.get_or_create_guild(guild_id)
        engagement_channels = guild_settings.engagement_channels if guild_settings else []

        additional_xp = 0
        if interaction.channel.id in engagement_channels:
            additional_xp = 15
        
        await self.level_manager.add_xp(user_id, guild_id, additional_xp + 25)
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id or not payload.guild_id:
            return

        user_id = payload.user_id
        guild_id = payload.guild_id
        current_time = time.time()

        last_reaction_time = self.reaction_cooldowns.get(guild_id, {}).get(user_id, 0)
        if current_time - last_reaction_time < 60:
            return
        
        self.reaction_cooldowns[guild_id][user_id] = current_time

        await self.level_manager.add_xp(guild_id, user_id, 5)
    

    @commands.hybrid_command(name="level", description="Check member's current level and XP.")
    async def get_user_level(self, ctx: commands.Context, member: discord.Member = None):
        """Checks your (or another member's) current level and XP."""
        
        target_user = member or ctx.author
        profile = await self.level_manager.get_user_profile(target_user.id, ctx.guild.id)
        
        if not profile:
            await ctx.send(f"{target_user.display_name} has no XP yet!")
            return

        xp_for_next = self.level_manager.xp_for_level(profile.level + 1)
        
        embed = create_embed(title=f"Level for {target_user.display_name}",)
        embed.set_thumbnail(url=target_user.display_avatar.url)
        embed.add_field(name="Level", value=f"`{profile.level}`", inline=True)
        embed.add_field(name="XP", value=f"`{profile.xp} / {xp_for_next}`", inline=True)
        await ctx.send(embed=embed)


    # --- NEW 'rank' COMMAND ---

    @commands.hybrid_command(name="rank", description="Check a member's server rank.")
    async def rank(self, ctx: commands.Context, member: discord.Member = None):
        """Checks your (or another member's) position on the leaderboard."""
        
        target_user = member or ctx.author
        
        rank = await self.level_manager.get_user_rank(target_user.id, ctx.guild.id)
        
        if not rank:
            await ctx.send(f"{target_user.display_name} is not on the leaderboard yet!")
            return
            
        await ctx.send(f"{target_user.display_name} is **Rank #{rank}** on the server.")


    # --- NEW 'leaderboard' COMMAND ---

    @commands.hybrid_command(name="leaderboard", description="Shows the server XP leaderboard.")
    async def leaderboard(self, ctx: commands.Context):
        """Displays the top users in the server, sorted by XP."""
        
        await ctx.defer() # This can take a moment
        
        # 1. Fetch the sorted data from the manager
        all_profiles = await self.level_manager.get_leaderboard(ctx.guild.id)
        
        if not all_profiles:
            await ctx.send("The leaderboard is empty! No one has earned XP yet.")
            return

        # 2. Create the View and the first Embed
        view = LeaderboardView(self.bot, all_profiles)
        embed = await view.get_page_embed()
        
        # 3. Send the message
        await ctx.send(embed=embed, view=view)
    
    # new admin commands
    @commands.hybrid_group(name="leveling", description="Commands to configure the leveling system.")
    @commands.has_guild_permissions(manage_guild=True)
    async def leveling(self, ctx: commands.Context):
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
        guild_settings = self.bot.guild_manager.get_or_create_guild(ctx.guild.id)

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