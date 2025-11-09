import discord
from discord.ext import commands
import logging
import aiohttp
from sqlalchemy import select, delete
from bs4 import BeautifulSoup
from gookybot.database.models.autovc import AutoVC
from gookybot.utils.embeds import create_embed
from gookybot.core.bot import GookyBot


logger = logging.getLogger(__name__)
DISPLAY_NAME_PREFIX = "🎧 "


class CopyLinkView(discord.ui.View):
    def __init__(self, link_to_copy: str):
        super().__init__(timeout=None)
        self.link_to_copy = link_to_copy
    
    @discord.ui.button(label="Copy Link", style=discord.ButtonStyle.green, emoji="📋")
    async def copy_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        formatted_link = f"```{self.link_to_copy}```"

        await interaction.response.send_message(
            content=formatted_link,
            ephemeral=True
        )


class AutomationCog(commands.Cog):

    def __init__(self, bot: GookyBot):
        self.bot = bot
        self.http_session = aiohttp.ClientSession()
        self.temp_vcs: dict[int, int] = {}
    
    async def cog_unload(self):
        await self.http_session.close()

    async def fetch_wallpaper_image(self, url: str) -> str | None:
        try:
            async with self.http_session.get(url) as response:
                if response.status != 200:
                    logger.warning(f"Failed to fetch {url}, status: {response.status}")
                    return None
                
                html = await response.text()
                
                soup = BeautifulSoup(html, 'html.parser')
                
                image_tag = soup.find("meta", property="og:image")
                
                if image_tag and image_tag.get("content"):
                    return image_tag.get("content")
                else:
                    logger.warning(f"No og:image tag found for {url}")
                    return None
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}", exc_info=True)
            return None
    
    @commands.hybrid_command(name="wallpaperengine", description="Share a Steam Wallpaper Engine link.")
    async def wallpaper_engine(self, ctx: commands.Context, link: str):
        """Posts a Wallpaper Engine link."""
        if not link.startswith("https://steamcommunity.com/sharedfiles/filedetails/?id="):
            await ctx.send("Please provide a valid Wallpaper Engine link.", ephemeral=True)
            return
        
        await ctx.defer()

        image_url = await self.fetch_wallpaper_image(link)
        
        embed = create_embed(
            title="Steam Wallpaper Share",
            description=f"**{ctx.author.display_name}** shared a wallpaper!\n\n"
            f"[Visit Steam page]({link})",
        )

        if image_url:
            embed.set_image(url=image_url)
        else:
            embed.set_thumbnail(url="https://store.cloudflare.steamstatic.com/public/images/v6/logo_steam_footer.png")
        
        view = CopyLinkView(link_to_copy=link)
        await ctx.send(embed=embed, view=view)

    async def _get_owner_from_cache(self, channel_id: int) -> int | None:
        """Helper to find an owner_id from a channel_id in the cache."""
        for owner_id, cid in self.temp_vcs.items():
            if cid == channel_id:
                return owner_id
        return None

    @commands.Cog.listener()
    async def initialize_and_cleanup(self):
        """
        This is our "Garbage Collector" and "Cache Re-builder".
        It runs once when the bot starts up.
        """
        logger.info("AutoVC: Checking for orphaned VCs and re-populating cache...")
        channels_deleted = 0
        channels_repopulated = 0
        
        async with self.bot.db_session() as session:
            # 1. Get all stored VCs from the database
            stmt = select(AutoVC)  # <-- 2. Use AutoVC
            result = await session.execute(stmt)
            all_temp_vcs = result.scalars().all()
            
            db_channels_to_delete = []

            for temp_vc in all_temp_vcs:
                channel = self.bot.get_channel(temp_vc.voice_channel_id) # <-- 3. Use voice_channel_id
                
                if channel is None:
                    # The channel was deleted while the bot was offline.
                    # We must clean up the database entry.
                    db_channels_to_delete.append(temp_vc.voice_channel_id) # <-- 4. Use voice_channel_id
                    logger.info(f"AutoVC: Cleaning stale DB entry for channel {temp_vc.voice_channel_id}")
                    continue

                if len(channel.members) == 0:
                    # It's an orphan and empty, delete it from Discord
                    try:
                        await channel.delete(reason="AutoVC: Startup cleanup")
                        db_channels_to_delete.append(temp_vc.voice_channel_id) # <-- 5. Use voice_channel_id
                        channels_deleted += 1
                    except Exception as e:
                        logger.error(f"Error deleting orphaned VC: {e}", exc_info=True)
                else:
                    # It's an orphan but people are in it!
                    # Re-add it to our cache so we can manage it.
                    self.temp_vcs[temp_vc.user_discord_id] = temp_vc.voice_channel_id # <-- 6. Use correct columns
                    channels_repopulated += 1

            # 2. Clean up the database in one go
            if db_channels_to_delete:
                delete_stmt = delete(AutoVC).where(AutoVC.voice_channel_id.in_(db_channels_to_delete)) # <-- 7. Use AutoVC
                await session.execute(delete_stmt)
                await session.commit()
                        
        logger.info(f"AutoVC: Cleanup complete. Deleted {channels_deleted}, repopulated {channels_repopulated}.")


    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """
        Handles creating and deleting channels using the fast dict cache.
        """
        if member.bot:
            return

        guild_settings = await self.bot.guild_manager.get_or_create_guild(member.guild.id)
        if not guild_settings or not guild_settings.auto_vc_channel_id:
            return
        
        generator_channel_id = guild_settings.auto_vc_channel_id
        
        # --- Handle Channel Creation ---
        if after.channel and after.channel.id == generator_channel_id:
            
            # 1. CHECK THE CACHE (this is fast!)
            if member.id in self.temp_vcs:
                # 2A. USER ALREADY HAS A CHANNEL: Move them to it
                existing_channel = self.bot.get_channel(self.temp_vcs[member.id])
                if existing_channel:
                    try:
                        await member.move_to(existing_channel)
                        logger.info(f"Moving {member.display_name} to their existing VC.")
                    except Exception as e:
                        logger.warning(f"Failed to move {member.display_name} to existing VC: {e}")
                else:
                    # The channel was deleted but our cache is stale.
                    self.temp_vcs.pop(member.id, None)
            
            # 2B. USER DOES NOT HAVE A CHANNEL: Create one
            if member.id not in self.temp_vcs:
                generator_channel = after.channel
                category = generator_channel.category
                channel_name = f"{DISPLAY_NAME_PREFIX}{member.display_name}'s VC"
                
                try:
                    # Create the channel on Discord
                    new_channel = await member.guild.create_voice_channel(
                        channel_name,
                        category=category,
                        overwrites=generator_channel.overwrites
                    )
                    
                    # --- ADD TO DB AND CACHE (USING NEW MODEL) ---
                    async with self.bot.db_session() as session:
                        new_db_vc = AutoVC(
                            voice_channel_id=new_channel.id, 
                            user_discord_id=member.id,
                            guild_discord_id=member.guild.id
                        )
                        session.add(new_db_vc)
                        await session.commit()
                    
                    self.temp_vcs[member.id] = new_channel.id
                    # -------------------------
                    
                    await member.move_to(new_channel)
                    logger.info(f"Created temp VC for {member.display_name} ({member.id}).")
                    
                except Exception as e:
                    # --- FIX FOR RACE CONDITION ---
                    # If the DB insertion failed (e.g., UniqueViolationError)
                    # it means the user *just* created a channel.
                    if 'new_channel' in locals():
                        await new_channel.delete(reason="AutoVC: Failed to create or race condition")
                    
                    # Try to find the channel they must have just created
                    # and move them into it.
                    async with self.bot.db_session() as session:
                        stmt = select(AutoVC).where(
                            AutoVC.user_discord_id == member.id,
                            AutoVC.guild_discord_id == member.guild.id
                        )
                        existing_vc = (await session.execute(stmt)).scalar_one_or_none()
                        if existing_vc:
                            self.temp_vcs[member.id] = existing_vc.voice_channel_id
                            existing_channel = self.bot.get_channel(existing_vc.voice_channel_id)
                            if existing_channel:
                                await member.move_to(existing_channel)

                    logger.error(f"Error in AutoVC creation, handled race condition: {e}", exc_info=True)

        # --- Handle Channel Deletion ---
        if before.channel:
            # Check if the channel they left is one of ours
            owner_id = await self._get_owner_from_cache(before.channel.id)
            
            if owner_id and len(before.channel.members) == 0:
                try:
                    await before.channel.delete(reason="AutoVC: Channel empty")
                    
                    # --- REMOVE FROM DB AND CACHE ---
                    async with self.bot.db_session() as session:
                        delete_stmt = delete(AutoVC).where(AutoVC.user_discord_id == owner_id, AutoVC.guild_discord_id == before.channel.guild.id)
                        await session.execute(delete_stmt)
                        await session.commit()
                    
                    self.temp_vcs.pop(owner_id, None)
                    # ----------------------------
                    
                    logger.info(f"Deleted temp VC '{before.channel.name}' as it was empty.")
                except discord.NotFound:
                    # Channel was already deleted, just clean up DB/cache
                    async with self.bot.db_session() as session:
                        delete_stmt = delete(AutoVC).where(AutoVC.user_discord_id == owner_id, AutoVC.guild_discord_id == before.channel.guild.id)
                        await session.execute(delete_stmt)
                        await session.commit()
                    self.temp_vcs.pop(owner_id, None)
                except Exception as e:
                    logger.error(f"Error in AutoVC deletion: {e}", exc_info=True)

async def setup(bot: GookyBot):
    await bot.add_cog(AutomationCog(bot))