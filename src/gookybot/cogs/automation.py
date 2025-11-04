import discord
from discord.ext import commands
import logging
import aiohttp
from bs4 import BeautifulSoup
from gookybot.utils.embeds import create_embed
from gookybot.core.bot import GookyBot


logger = logging.getLogger(__name__)


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

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.http_session = aiohttp.ClientSession()
    
    async def cog_unload(self):
        """Clean up the session when the cog is unloaded."""
        await self.http_session.close()

    async def fetch_wallpaper_image(self, url: str) -> str | None:
        """
        Fetches the Steam Workshop page and scrapes the preview image URL.
        """
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


async def setup(bot: GookyBot):
    await bot.add_cog(AutomationCog(bot))