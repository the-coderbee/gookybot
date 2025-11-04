import discord
from typing import Optional
from gookybot.config.constants import BOT_COLOR

def create_embed(
    title: Optional[str] = None,
    description: Optional[str] = None,
    color: Optional[discord.Color] = None,
) -> discord.Embed:
    """
    Creates a standardized Discord embed for the bot.

    Args:
        title: The title of the embed.
        description: The main text of the embed.
        color: The color of the embed. Defaults to the BOT_COLOR.
    
    Returns:
        A discord.Embed object with the standard bot footer.
    """
    
    # Use the default bot color if no specific color is provided
    if color is None:
        color = BOT_COLOR
        
    embed = discord.Embed(title=title, description=description, color=color)
    
    # You can set a standard footer for all your embeds
    embed.set_footer(text="Gooky Bot")
    
    return embed