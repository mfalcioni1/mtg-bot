import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import os
from typing import Dict, List
from cube_parser import CubeCobraParser
import argparse
from draft_bots import DraftBot
from draft import RochesterDraft
import asyncio
from aiohttp import web
import logging
import signal
from v4cb import V4CBGame

# Add argument parsing
parser = argparse.ArgumentParser(description='Run the MTG Draft Discord Bot')
parser.add_argument('--test', action='store_true', help='Run in test mode with specific guild')
args = parser.parse_args()

# Intents are required to manage certain events
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

# Load environment variables from .env file
load_dotenv()

# Move this before any commands
async def pick_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    """Provide autocomplete suggestions for card names in the current pack"""
    guild_id = interaction.guild_id
    
    if guild_id not in bot.draft_sessions:
        return []
    
    draft = bot.draft_sessions[guild_id]
    current_pack = draft.get_current_pack()
    
    # Check if it's the player's turn using the new method
    if not current_pack or interaction.user != draft.get_current_player():
        return []
    
    # Filter cards that match the current input (case-insensitive)
    matches = []
    current_lower = current.lower()
    for card in current_pack:
        if current_lower in card.name.lower():
            matches.append(app_commands.Choice(
                name=f"{card.name} ({card.color_category.upper()})",
                value=card.name
            ))
    
    # Discord has a limit of 25 choices
    return matches[:25]

# Define all commands before bot initialization
@app_commands.command(name="signup", description="Sign up for the current draft")
async def signup(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    
    if guild_id not in bot.active_drafts:
        bot.active_drafts[guild_id] = []
    
    if interaction.user in bot.active_drafts[guild_id]:
        await interaction.response.send_message("You're already signed up for the draft!", ephemeral=True)
        return
    
    bot.active_drafts[guild_id].append(interaction.user)
    participant_list = "\n".join([f"{idx + 1}. {player.display_name}" 
                                for idx, player in enumerate(bot.active_drafts[guild_id])])
    
    embed = discord.Embed(
        title="Draft Signup",
        description=f"{interaction.user.display_name} has signed up for the draft!\n\n**Current Participants:**\n{participant_list}",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)

@app_commands.command(name="clear_signup", description="Clear all signups for the current draft (Admin only)")
async def clear_signup(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You need administrator permissions to use this command!", ephemeral=True)
        return
    
    guild_id = interaction.guild_id
    bot.active_drafts[guild_id] = []
    await interaction.response.send_message("Draft signups have been cleared!", ephemeral=True)

@app_commands.command(name="pick", description="Pick a card from your current pack")
@app_commands.describe(card_name="Start typing a card name to see available options")
@app_commands.autocomplete(card_name=pick_autocomplete)
async def pick(interaction: discord.Interaction, card_name: str):
    guild_id = interaction.guild_id
    
    if guild_id not in bot.draft_sessions:
        await interaction.response.send_message("There's no active draft in this server!", ephemeral=True)
        return
    
    draft = bot.draft_sessions[guild_id]
    
    # Check if it's the player's turn
    if interaction.user != draft.get_current_player():
        await interaction.response.send_message("It's not your turn to pick!", ephemeral=True)
        return
    
    picked_card = await draft.handle_pick(interaction.user, card_name)
    if not picked_card:
        await interaction.response.send_message(
            f"Couldn't find card '{card_name}' in the current pack!",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        f"You picked {picked_card.name}!",
        ephemeral=True
    )

    await draft.update_pack_display()

    # Check if draft is complete before handling bot turns
    if draft.is_draft_complete():
        # Clear draft session
        bot.draft_sessions.pop(guild_id, None)
        bot.active_drafts[guild_id] = []
        return

    # Handle bot turns
    if draft.is_bot_turn():
        while draft.is_bot_turn() and not draft.is_draft_complete():
            current_bot = draft.get_current_player()
            current_pack = draft.get_current_pack()
            if current_pack:
                bot_pick = current_bot.make_pick(current_pack)
                if bot_pick:
                    await draft.handle_pick(current_bot, bot_pick.name)
                    await interaction.channel.send(f"Bot {current_bot.name} picked {bot_pick.name}")
                    await draft.update_pack_display()
    
    # Only notify next player if draft isn't complete
    if not draft.is_draft_complete():
        next_player = draft.get_current_player()
        if not draft.is_bot_turn():
            await interaction.channel.send(f"{next_player.mention}, it's your turn to pick!")

@app_commands.command(name="show_pack", description="Show your current pack")
async def show_pack(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    
    if guild_id not in bot.draft_sessions:
        await interaction.response.send_message("There's no active draft in this server!", ephemeral=True)
        return
    
    draft = bot.draft_sessions[guild_id]
    
    # Check if it's the player's turn using get_current_player()
    if interaction.user != draft.get_current_player():
        await interaction.response.send_message("It's not your turn to pick!", ephemeral=True)
        return
    
    current_pack = draft.get_current_pack()
    if not current_pack:
        await interaction.response.send_message("No active pack to display!", ephemeral=True)
        return
    
    # Create pack display
    pack_contents = "\n".join([
        f"{idx + 1}. {card.name} ({card.type}) - {card.color_category.upper()}"
        for idx, card in enumerate(current_pack)
    ])
    
    embed = discord.Embed(
        title=f"Pack {draft.state.current_pack_number}, Pick {draft.state.current_pick}",
        description=f"Your current pack:\n{pack_contents}",
        color=discord.Color.blue()
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@app_commands.command(name="startdraft", description="Start a new draft with a Cube Cobra cube")
@app_commands.describe(
    cube_url="Either a Cube Cobra URL or cube ID",
    cards_per_pack="Number of cards per pack (default: 15)",
    num_packs="Number of packs per player (default: 3)",
    total_players="Total number of players in draft (default: 8)"
)
async def startdraft(interaction: discord.Interaction, cube_url: str = None, 
                    cards_per_pack: int = 15, num_packs: int = 3, total_players: int = 8):
    guild_id = interaction.guild_id
    
    # Use default test cube ID if in test mode and no cube_url provided
    if bot.test_mode and not cube_url:
        cube_url = "321d4c19-8c8a-47a1-89a5-f276617c83f1"
    elif not cube_url:
        await interaction.response.send_message(
            "Please provide a Cube Cobra URL or cube ID!", 
            ephemeral=True
        )
        return
    
    # Check if there's an active draft
    if guild_id in bot.draft_sessions:
        await interaction.response.send_message("There's already an active draft in this server!", ephemeral=True)
        return
    
    # Check if we have any signups
    if guild_id not in bot.active_drafts or not bot.active_drafts[guild_id]:
        await interaction.response.send_message("No players have signed up for the draft yet! Use /signup first.", ephemeral=True)
        return
    
    # Calculate number of bots needed
    num_human_players = len(bot.active_drafts[guild_id])
    if num_human_players > total_players:
        await interaction.response.send_message(
            f"Too many players signed up! Maximum is {total_players}, but {num_human_players} are signed up.", 
            ephemeral=True
        )
        return
    
    num_bots = total_players - num_human_players
    
    await interaction.response.defer()
    
    try:
        # Validate and fetch cube data
        if not await bot.cube_parser.validate_url(cube_url):
            await interaction.followup.send(
                "Invalid cube URL or ID! Please provide either:\n"
                "• A Cube Cobra URL (e.g., https://cubecobra.com/cube/list/example)\n"
                "• Just the cube ID (e.g., example)", 
                ephemeral=True
            )
            return
        
        cards = await bot.cube_parser.fetch_cube_data(cube_url)
        if not cards:
            await interaction.followup.send(
                "Failed to fetch cube list. Please check that:\n"
                "• The cube exists\n"
                "• The cube is public\n"
                "• The cube is not empty", 
                ephemeral=True
            )
            return
        
        # Create draft session
        draft = RochesterDraft(cards, num_human_players, cards_per_pack, num_packs, num_bots)
        draft.add_bots(num_bots)
        
        try:
            draft.prepare_packs()
            draft.initialize_player_pools(bot.active_drafts[guild_id])
        except ValueError as e:
            await interaction.followup.send(str(e), ephemeral=True)
            return
        
        bot.draft_sessions[guild_id] = draft
        
        # Update embed to show draft configuration
        embed = discord.Embed(
            title="Draft Started!",
            description=f"Draft initialized with:\n"
                       f"• {len(cards)} cards in cube\n"
                       f"• {total_players} total seats\n"
                       f"• {num_human_players} human players\n"
                       f"• {num_bots} bot players\n"
                       f"• {cards_per_pack} cards per pack\n"
                       f"• {num_packs} packs per player\n\n"
                       f"Color Distribution:\n"
                       f"• White: {sum(1 for c in cards if c.color_category == 'w')}\n"
                       f"• Blue: {sum(1 for c in cards if c.color_category == 'u')}\n"
                       f"• Black: {sum(1 for c in cards if c.color_category == 'b')}\n"
                       f"• Red: {sum(1 for c in cards if c.color_category == 'r')}\n"
                       f"• Green: {sum(1 for c in cards if c.color_category == 'g')}\n"
                       f"• Multi: {sum(1 for c in cards if c.color_category == 'm')}\n"
                       f"• Colorless: {sum(1 for c in cards if c.color_category == 'c')}\n\n"
                       f"The first pack will be sent shortly!",
            color=discord.Color.green()
        )
        
        await interaction.followup.send(embed=embed)
        
        # If first player is a bot, start bot picking
        if draft.is_bot_turn():
            while draft.is_bot_turn():
                current_bot = draft.get_current_player()
                current_pack = draft.get_current_pack()
                if current_pack:
                    picked_card = current_bot.make_pick(current_pack)
                    if picked_card:
                        await draft.handle_pick(current_bot, picked_card.name)
                        await interaction.channel.send(f"Bot {current_bot.name} picked {picked_card.name}")
                        await draft.update_pack_display()
            
            # Notify first human player
            next_player = draft.get_current_player()
            await interaction.channel.send(f"{next_player.mention}, it's your turn to pick!")
        
        await draft.set_draft_channel(interaction.channel)
        await draft.update_pack_display()
        
    except Exception as e:
        print(f"Error in startdraft: {e}")  # Log the error
        await interaction.followup.send(
            "An unexpected error occurred while starting the draft. Please try again later.", 
            ephemeral=True
        )

@app_commands.command(name="viewpool", description="View a player's drafted cards")
@app_commands.describe(player="The player whose pool you want to view (defaults to yourself)")
async def viewpool(interaction: discord.Interaction, player: discord.Member = None):
    guild_id = interaction.guild_id
    
    if guild_id not in bot.draft_sessions:
        await interaction.response.send_message("There's no active draft in this server!", ephemeral=True)
        return
    
    draft = bot.draft_sessions[guild_id]
    
    # If no player specified, show the requester's pool
    target_player = player or interaction.user
    
    # Check if player is in the draft
    if target_player not in draft.player_pools:
        await interaction.response.send_message(
            f"{target_player.display_name} is not participating in this draft!",
            ephemeral=True
        )
        return
    
    pool = draft.player_pools[target_player]
    
    if not pool:
        await interaction.response.send_message(
            f"{target_player.display_name} hasn't drafted any cards yet!",
            ephemeral=True
        )
        return
    
    # Group cards by color category
    cards_by_color = {}
    for card in pool:
        color = card.color_category.upper()
        if color not in cards_by_color:
            cards_by_color[color] = []
        cards_by_color[color].append(card)
    
    # Create embed with sorted cards by color
    embed = discord.Embed(
        title=f"{target_player.display_name}'s Draft Pool",
        description=f"Total Cards: {len(pool)}",
        color=discord.Color.blue()
    )
    
    # Color order: White, Blue, Black, Red, Green, Multi, Colorless
    color_order = ['W', 'U', 'B', 'R', 'G', 'M', 'C']
    
    for color in color_order:
        if color in cards_by_color:
            cards = cards_by_color[color]
            card_list = "\n".join([f"• {card.name} ({card.type})" for card in cards])
            embed.add_field(
                name=f"{color} ({len(cards)})",
                value=card_list or "None",
                inline=False
            )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@app_commands.command(name="quitdraft", description="Quit the current draft and reset everything (Admin only)")
async def quitdraft(interaction: discord.Interaction):
    """Quit the current draft and reset all states"""
    # Check if user has admin permissions
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "You need administrator permissions to use this command!", 
            ephemeral=True
        )
        return
    
    guild_id = interaction.guild_id
    
    # Check if there's an active draft
    if guild_id not in bot.draft_sessions:
        await interaction.response.send_message(
            "There's no active draft to quit!", 
            ephemeral=True
        )
        return
    
    try:
        # Clear the pack display
        draft = bot.draft_sessions[guild_id]
        await draft.pack_display.clear_display(guild_id)
        
        # Clear all states
        bot.active_drafts[guild_id] = []
        bot.draft_sessions.pop(guild_id, None)
        
        await interaction.response.send_message(
            "Draft has been terminated. All states have been reset.\n"
            "Use `/signup` to start a new draft!",
            ephemeral=False
        )
        
    except Exception as e:
        print(f"Error in quitdraft: {e}")
        await interaction.response.send_message(
            "An error occurred while trying to quit the draft. Please try again.",
            ephemeral=True
        )

@app_commands.command(name="v4cb_start", description="Start a new V4CB game with a banned list")
@app_commands.describe(banned_list="Comma-separated list of banned cards")
async def v4cb_start(interaction: discord.Interaction, banned_list: str):
    """Start a new V4CB game"""
    channel_id = interaction.channel_id
    
    if channel_id in bot.v4cb_games and bot.v4cb_games[channel_id].is_active:
        await interaction.response.send_message(
            "There's already an active V4CB game in this channel!",
            ephemeral=True
        )
        return
    
    # Create new game or get existing game instance
    if channel_id not in bot.v4cb_games:
        bot.v4cb_games[channel_id] = V4CBGame(channel_id)
    
    # Parse banned list
    banned_cards = [card.strip() for card in banned_list.split(',')]
    
    # Start the game
    bot.v4cb_games[channel_id].start_game(banned_cards)
    
    await interaction.response.send_message(
        f"V4CB game started! Banned cards:\n{', '.join(banned_cards)}\n\n"
        f"Use `/v4cb_submit` to submit your cards!"
    )

@app_commands.command(name="v4cb_submit", description="Submit your cards for V4CB")
@app_commands.describe(cards="Comma-separated list of exactly 4 cards")
async def v4cb_submit(interaction: discord.Interaction, cards: str):
    """Submit cards for V4CB"""
    channel_id = interaction.channel_id
    
    if channel_id not in bot.v4cb_games or not bot.v4cb_games[channel_id].is_active:
        await interaction.response.send_message(
            "There's no active V4CB game in this channel!",
            ephemeral=True
        )
        return
    
    # Parse cards
    card_list = [card.strip() for card in cards.split(',')]
    
    # Submit cards
    success, error = bot.v4cb_games[channel_id].submit_cards(interaction.user, card_list)
    
    if not success:
        await interaction.response.send_message(error, ephemeral=True)
        return
    
    # Create status message
    game = bot.v4cb_games[channel_id]
    submitted_players = [player.display_name for player in game.submissions.keys()]
    
    embed = discord.Embed(
        title="Cards Submitted Successfully!",
        description="Your cards have been recorded.",
        color=discord.Color.green()
    )
    
    embed.add_field(
        name="Current Submissions",
        value="\n".join(submitted_players),
        inline=False
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)
    
    # Send a public message about the new submission
    public_embed = discord.Embed(
        title="New V4CB Submission",
        description=f"{interaction.user.display_name} has submitted their cards!",
        color=discord.Color.blue()
    )
    public_embed.add_field(
        name="Players who have submitted",
        value="\n".join(submitted_players),
        inline=False
    )
    await interaction.channel.send(embed=public_embed)

@app_commands.command(name="v4cb_reveal", description="Reveal all submitted cards and start new round")
async def v4cb_reveal(interaction: discord.Interaction):
    """Reveal all submitted cards and reset for next round"""
    channel_id = interaction.channel_id
    
    if channel_id not in bot.v4cb_games or not bot.v4cb_games[channel_id].is_active:
        await interaction.response.send_message(
            "There's no active V4CB game in this channel!",
            ephemeral=True
        )
        return
    
    # Get submissions and reset for next round
    submissions = bot.v4cb_games[channel_id].reveal_and_reset()
    
    if not submissions:
        await interaction.response.send_message("No submissions to reveal!")
        return
    
    # Create reveal message
    embed = discord.Embed(
        title="V4CB Round Results",
        description="All submissions for this round:",
        color=discord.Color.gold()
    )
    
    for player, cards in submissions.items():
        embed.add_field(
            name=player.display_name,
            value=", ".join(cards),
            inline=False
        )
    
    embed.add_field(
        name="Next Round",
        value="All submissions have been cleared. Players can now submit new cards for the next round.",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

@app_commands.command(name="v4cb_update_banned", description="Add cards to the banned list")
@app_commands.describe(banned_list="Comma-separated list of cards to ban")
async def v4cb_update_banned(interaction: discord.Interaction, banned_list: str):
    """Add cards to the banned list"""
    channel_id = interaction.channel_id
    
    if channel_id not in bot.v4cb_games or not bot.v4cb_games[channel_id].is_active:
        await interaction.response.send_message(
            "There's no active V4CB game in this channel!",
            ephemeral=True
        )
        return
    
    # Parse and update banned list
    new_banned_cards = [card.strip() for card in banned_list.split(',')]
    game = bot.v4cb_games[channel_id]
    
    # Store current banned list size
    old_size = len(game.banned_cards)
    
    # Update the banned list
    game.update_banned_list(new_banned_cards)
    
    # Calculate newly added cards
    cards_added = len(game.banned_cards) - old_size
    
    embed = discord.Embed(
        title="Banned List Updated",
        description=f"Added {cards_added} new card(s) to the banned list.",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="Current Banned List",
        value="\n".join(sorted(game.banned_cards)) if game.banned_cards else "No banned cards",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

@app_commands.command(name="v4cb_end", description="End the current V4CB game")
async def v4cb_end(interaction: discord.Interaction):
    """End the current V4CB game"""
    channel_id = interaction.channel_id
    
    if channel_id not in bot.v4cb_games or not bot.v4cb_games[channel_id].is_active:
        await interaction.response.send_message(
            "There's no active V4CB game in this channel!",
            ephemeral=True
        )
        return
    
    bot.v4cb_games[channel_id].end_game()
    await interaction.response.send_message("V4CB game ended!")

@app_commands.command(name="v4cb_status", description="Show the current game status")
async def v4cb_status(interaction: discord.Interaction):
    """Show the current game status, including submissions and banned list"""
    channel_id = interaction.channel_id
    
    if channel_id not in bot.v4cb_games or not bot.v4cb_games[channel_id].is_active:
        await interaction.response.send_message(
            "There's no active V4CB game in this channel!",
            ephemeral=True
        )
        return
    
    game = bot.v4cb_games[channel_id]
    
    # Create status message
    embed = discord.Embed(
        title="V4CB Game Status",
        color=discord.Color.blue()
    )
    
    # Add submitted players field
    submitted_players = [player.display_name for player in game.submissions.keys()]
    embed.add_field(
        name="Submitted Players",
        value="\n".join(submitted_players) if submitted_players else "No submissions yet",
        inline=False
    )
    
    # Add banned list field
    embed.add_field(
        name="Banned Cards",
        value="\n".join(sorted(game.banned_cards)) if game.banned_cards else "No banned cards",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

@app_commands.command(name="v4cb_set_banned", description="Overwrite the current banned list with a new one")
@app_commands.describe(banned_list="Comma-separated list of cards for the new banned list")
async def v4cb_set_banned(interaction: discord.Interaction, banned_list: str):
    """Overwrite the current banned list"""
    channel_id = interaction.channel_id
    
    if channel_id not in bot.v4cb_games or not bot.v4cb_games[channel_id].is_active:
        await interaction.response.send_message(
            "There's no active V4CB game in this channel!",
            ephemeral=True
        )
        return
    
    # Parse and set new banned list
    new_banned_list = [card.strip() for card in banned_list.split(',')]
    game = bot.v4cb_games[channel_id]
    
    # Store old list for comparison
    old_banned_list = set(game.banned_cards)
    
    # Set the new banned list
    game.set_banned_list(new_banned_list)
    
    # Create informative embed
    embed = discord.Embed(
        title="Banned List Overwritten",
        description="The banned list has been completely replaced.",
        color=discord.Color.orange()
    )
    
    # Show removed cards if any
    removed_cards = old_banned_list - game.banned_cards
    if removed_cards:
        embed.add_field(
            name="Removed Cards",
            value="\n".join(sorted(removed_cards)),
            inline=False
        )
    
    # Show added cards if any
    added_cards = game.banned_cards - old_banned_list
    if added_cards:
        embed.add_field(
            name="Added Cards",
            value="\n".join(sorted(added_cards)),
            inline=False
        )
    
    # Show current complete list
    embed.add_field(
        name="Current Banned List",
        value="\n".join(sorted(game.banned_cards)) if game.banned_cards else "No banned cards",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

def handle_sigterm(*args):
    """Handle termination signal"""
    logging.info("Received termination signal")
    asyncio.create_task(bot.close())

# Then define bot class and create instance
class DraftBot(commands.Bot):
    def __init__(self, *, test_mode: bool):
        super().__init__(command_prefix=commands.when_mentioned_or("drafty"), intents=intents)
        self.active_drafts: Dict[int, List[discord.Member]] = {}
        self.draft_sessions: Dict[int, RochesterDraft] = {}
        self.cube_parser = CubeCobraParser()
        self.test_mode = test_mode
        self.v4cb_games: Dict[int, V4CBGame] = {}
        
    async def setup_hook(self):
        """This is called when the bot is done preparing data"""
        print(f"Running in {'TEST' if self.test_mode else 'PRODUCTION'} mode")
        
        # Register commands
        self.tree.add_command(signup)
        self.tree.add_command(clear_signup)
        self.tree.add_command(pick)
        self.tree.add_command(show_pack)
        self.tree.add_command(startdraft)
        self.tree.add_command(viewpool)
        self.tree.add_command(quitdraft)
        self.tree.add_command(v4cb_start)
        self.tree.add_command(v4cb_submit)
        self.tree.add_command(v4cb_reveal)
        self.tree.add_command(v4cb_update_banned)
        self.tree.add_command(v4cb_end)
        self.tree.add_command(v4cb_status)
        self.tree.add_command(v4cb_set_banned)
        
        # Sync commands based on mode
        try:
            if self.test_mode and os.getenv('TEST_GUILD_ID'):
                test_guild = discord.Object(id=int(os.getenv('TEST_GUILD_ID')))
                self.tree.copy_global_to(guild=test_guild)
                await self.tree.sync(guild=test_guild)
                print(f"Test guild commands synced!")
            else:
                await self.tree.sync()
                print("Global commands synced!")
        except Exception as e:
            print(f"Failed to sync commands: {e}")

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print("------")

# Initialize bot with test mode flag
bot = DraftBot(test_mode=args.test)

# Run the bot
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Register signal handlers
    signal.signal(signal.SIGTERM, handle_sigterm)
    signal.signal(signal.SIGINT, handle_sigterm)
    
    try:
        # Run the bot
        bot.run(os.getenv('DISCORD_BOT_TOKEN'), log_handler=None)
    except Exception as e:
        logging.error(f"Bot crashed: {e}")
        # Ensure cleanup
        if not bot.is_closed():
            asyncio.run(bot.close())
