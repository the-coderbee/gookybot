import discord
from discord.ext import commands
from gookybot.core.bot import GookyBot
from typing import Optional
import logging
from gookybot.utils.embeds import create_embed

logger = logging.getLogger(__name__)

class HelpCog(commands.Cog, name="Help"):
    """
    A custom help command that replaces the default one.
    """
    def __init__(self, bot: GookyBot):
        self.bot = bot

    @commands.hybrid_command(name="help", description="Shows this help message.")
    async def help(self, ctx: commands.Context, command_name: Optional[str] = None):
        """Shows a list of all commands or info about a specific command."""
        
        await ctx.defer(ephemeral=True)

        if command_name is None:
            # --- Show the main help embed (all commands) ---
            embed = create_embed(
                title="Gooky Bot Help",
                description="Here is a list of all available commands.\n"
                            f"Use `/help <command_name>` for more info on a specific command.",
            )

            for cog_name, cog in self.bot.cogs.items():
                cog_commands = cog.get_commands()
                commands_list = []
                for cmd in cog_commands:
                    
                    # --- THIS IS FIX #1 ---
                    # We must use try/except because cmd.can_run() RAISES
                    # an error (like NotOwner) if a check fails.
                    can_run = False
                    try:
                        if not cmd.hidden and await cmd.can_run(ctx):
                            can_run = True
                    except commands.CheckFailure:
                        pass  # User cannot run this command, so we skip it
                    
                    if not can_run:
                        continue
                    # --- END FIX #1 ---
                    
                    if isinstance(cmd, (commands.HybridCommand, commands.HybridGroup)):
                        commands_list.append(f"**`/{cmd.name}`** - {cmd.description or 'No description'}")
                    elif isinstance(cmd, commands.Command): # For prefix-only commands
                        commands_list.append(f"`{ctx.prefix}{cmd.name}` - {cmd.description or 'No description'}")

                
                if commands_list:
                    embed.add_field(
                        name=cog_name,
                        value="\n".join(commands_list),
                        inline=False
                    )
            
            await ctx.send(embed=embed)

        else:
            # --- Show help for a specific command ---
            cmd = self.bot.get_command(command_name.lower())
            
            if cmd is None or cmd.hidden:
                await ctx.send(f"Sorry, I couldn't find a command named `{command_name}`.", ephemeral=True)
                return

            # Also check permissions for the specific command
            try:
                if not await cmd.can_run(ctx):
                    await ctx.send(f"Sorry, you do not have permission to run `{command_name}`.", ephemeral=True)
                    return
            except commands.CheckFailure:
                 await ctx.send(f"Sorry, you do not have permission to run `{command_name}`.", ephemeral=True)
                 return


            embed = create_embed(
                title=f"Help: `/{cmd.name}`",
                description=cmd.description or "No description provided.",
            )

            params = []
            if isinstance(cmd, (commands.HybridCommand, commands.HybridGroup)):
                for param in cmd.app_command.parameters:
                    if param.required:
                        params.append(f"<{param.name}>")
                    else:
                        params.append(f"[{param.name}]")
            
            usage = f"/{cmd.name} {' '.join(params)}"
            embed.add_field(name="Usage", value=f"`{usage}`", inline=False)

            if isinstance(cmd, (commands.HybridGroup, commands.Group)):
                subcommands = []
                for sub_cmd in cmd.commands:
                    
                    # --- THIS IS FIX #2 ---
                    # Add the same try/except block for subcommands
                    can_run_sub = False
                    try:
                        if not sub_cmd.hidden and await sub_cmd.can_run(ctx):
                            can_run_sub = True
                    except commands.CheckFailure:
                        pass
                    
                    if not can_run_sub:
                        continue
                    # --- END FIX #2 ---
                    
                    subcommands.append(f"`{sub_cmd.name}` - {sub_cmd.description or 'No description'}")
                
                if subcommands:
                    embed.add_field(name="Subcommands", value="\n".join(subcommands), inline=False)
            
            await ctx.send(embed=embed)

async def setup(bot: GookyBot):
    await bot.add_cog(HelpCog(bot))
