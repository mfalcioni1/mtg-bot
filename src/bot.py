import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import os
from typing import Dict, List, Optional, Union
import random
from cube_parser import CubeCobraParser, CardData
import argparse
from draft_bots import DraftBot, create_bot
from pack_display import PackDisplay, PackState

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

# Create a bot instance
class DraftBot(commands.Bot):
    def __init__(self, *, test_mode: bool):
        super().__init__(command_prefix=commands.when_mentioned_or("drafty"), intents=intents)
        self.active_drafts: Dict[int, List[discord.Member]] = {}
        self.draft_sessions: Dict[int, Draft] = {}
        self.cube_parser = CubeCobraParser()
        self.test_mode = test_mode
    
    async def setup_hook(self):
        print(f"Running in {'TEST' if self.test_mode else 'PRODUCTION'} mode")
        print("Syncing commands...")
        try:
            if self.test_mode:
                # Clear all global commands first
                await self.tree.sync()
                # Then sync to test guild
                test_guild = discord.Object(id=int(os.getenv('TEST_GUILD_ID')))
                # Clear existing guild commands
                self.tree.clear_commands(guild=test_guild)
                # Copy and sync new commands
                self.tree.copy_global_to(guild=test_guild)
                synced = await self.tree.sync(guild=test_guild)
                print(f"Test guild commands synced! Synced {len(synced)} commands")
            else:
                # Clear existing commands first
                self.tree.clear_commands()
                synced = await self.tree.sync()
                print(f"Global commands synced! Synced {len(synced)} commands")
            
            print(f"Available commands: {[cmd.name for cmd in self.tree.get_commands()]}")
        except Exception as e:
            print(f"Failed to sync commands: {e}")

class Draft:
    def __init__(self, cards: List[CardData], num_players: int, cards_per_pack: int, num_packs: int, num_bots: int = 0):
        self.cards = cards
        self.num_players = num_players + num_bots
        self.num_human_players = num_players
        self.cards_per_pack = cards_per_pack
        self.num_packs = num_packs
        self.packs: List[List[CardData]] = []
        self.current_pack = 0
        self.current_player = 0
        self.player_pools: Dict[Union[discord.Member, DraftBot], List[CardData]] = {}
        self.direction = 1  # 1 for left, -1 for right
        self.pack_number = 0  # Current pack number (0-based)
        self.bots: List[DraftBot] = []
        self.pack_display = PackDisplay()
        self.picked_cards: Dict[str, CardData] = {}  # Tracks picks for current pack
        self.draft_channel: Optional[discord.TextChannel] = None
        self.active_players: List[discord.Member] = []
    
    def add_bots(self, num_bots: int):
        """Add bot players to fill remaining seats"""
        for i in range(num_bots):
            bot = create_bot(name=f"Bot_{i+1}")
            self.bots.append(bot)
            self.player_pools[bot] = []
    
    def initialize_player_pools(self, players: List[discord.Member]):
        """Initialize empty card pools for all players and bots"""
        self.active_players = players
        self.player_pools = {player: [] for player in players}
        for bot in self.bots:
            self.player_pools[bot] = []
    
    def is_bot_turn(self) -> bool:
        """Check if it's currently a bot's turn"""
        return self.current_player >= self.num_human_players
    
    def get_current_player(self) -> Union[discord.Member, DraftBot]:
        """Get the current player or bot"""
        if self.is_bot_turn():
            return self.bots[self.current_player - self.num_human_players]
        return self.active_players[self.current_player]
    
    async def handle_bot_picks(self) -> Optional[CardData]:
        """Handle picks for bot players"""
        if not self.is_bot_turn():
            return None
            
        current_bot = self.get_current_player()
        current_pack = self.get_current_pack()
        
        if not current_pack:
            return None
            
        picked_card = current_bot.make_pick(current_pack)
        if picked_card:
            current_pack.remove(picked_card)
            self.player_pools[current_bot].append(picked_card)
            self.current_player = (self.current_player + self.direction) % self.num_players
            
            # Check if we need to move to next pack
            if (self.direction == 1 and self.current_player == 0) or \
               (self.direction == -1 and self.current_player == self.num_players - 1):
                self.pack_number += 1
                if self.pack_number % self.num_players == 0:
                    self.direction *= -1
                    
        return picked_card
    
    def prepare_packs(self):
        """Shuffle cards and create packs"""
        random.shuffle(self.cards)
        cards_needed = self.num_players * self.num_packs * self.cards_per_pack
        if len(self.cards) < cards_needed:
            raise ValueError(f"Not enough cards in cube. Need {cards_needed} but only have {len(self.cards)}")
        
        # Create packs
        for i in range(self.num_packs * self.num_players):
            pack = self.cards[i * self.cards_per_pack:(i + 1) * self.cards_per_pack]
            self.packs.append(pack)
    
    def get_current_pack(self) -> Optional[List[CardData]]:
        """Get the current pack for the current player"""
        if not self.packs:
            return None
        pack_index = self.current_player + (self.pack_number * self.num_players)
        return self.packs[pack_index] if pack_index < len(self.packs) else None
    
    def get_card_names(self) -> List[str]:
        """Get list of all card names in the cube"""
        return [card.name for card in self.cards]
    
    async def set_draft_channel(self, channel: discord.TextChannel):
        """Set the channel where pack displays will be shown"""
        self.draft_channel = channel
    
    async def update_pack_display(self):
        """Update the public pack display"""
        if not self.draft_channel:
            return

        current_pack = self.get_current_pack()
        if not current_pack:
            return

        current_player = self.get_current_player()
        player_name = current_player.name if isinstance(current_player, DraftBot) else current_player.display_name

        pack_state = PackState(
            available_cards=current_pack,
            picked_cards=self.picked_cards,
            pack_number=self.pack_number,
            pick_number=self.cards_per_pack - len(current_pack) + 1,
            current_player=player_name
        )

        await self.pack_display.create_or_update_pack_display(
            self.draft_channel,
            pack_state,
            self.draft_channel.guild.id
        )

# Initialize bot with test mode flag
bot = DraftBot(test_mode=args.test)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")

@bot.tree.command(name="signup", description="Sign up for the current draft")
async def signup(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    
    # Initialize the draft list for this guild if it doesn't exist
    if guild_id not in bot.active_drafts:
        bot.active_drafts[guild_id] = []
    
    # Check if the user is already signed up
    if interaction.user in bot.active_drafts[guild_id]:
        await interaction.response.send_message("You're already signed up for the draft!", ephemeral=True)
        return
    
    # Add the user to the draft
    bot.active_drafts[guild_id].append(interaction.user)
    
    # Create response message
    participant_list = "\n".join([f"{idx + 1}. {player.display_name}" 
                                for idx, player in enumerate(bot.active_drafts[guild_id])])
    
    embed = discord.Embed(
        title="Draft Signup",
        description=f"{interaction.user.display_name} has signed up for the draft!\n\n**Current Participants:**\n{participant_list}",
        color=discord.Color.green()
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="clear_signup", description="Clear all signups for the current draft (Admin only)")
async def clear_signup(interaction: discord.Interaction):
    # Check if user has admin permissions
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You need administrator permissions to use this command!", ephemeral=True)
        return
    
    guild_id = interaction.guild_id
    bot.active_drafts[guild_id] = []
    await interaction.response.send_message("Draft signups have been cleared!", ephemeral=True)

@bot.tree.command(
    name="startdraft",
    description="Start a new draft with a Cube Cobra cube"
)
@app_commands.describe(
    cube_url="Either a Cube Cobra URL or cube ID (default test cube provided in test mode)",
    cards_per_pack="Number of cards per pack (default: 15)",
    num_packs="Number of packs per player (default: 3)",
    total_players="Total number of players in draft (default: 8)"
)
async def startdraft(
    interaction: discord.Interaction,
    cube_url: str = None,
    cards_per_pack: int = 15,
    num_packs: int = 3,
    total_players: int = 8
):
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
        draft = Draft(cards, num_human_players, cards_per_pack, num_packs, num_bots)
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
                picked_card = await draft.handle_bot_picks()
                if picked_card:
                    await interaction.channel.send(f"Bot {draft.get_current_player().name} picked {picked_card.name}")
            
            # Notify first human player
            next_player = bot.active_drafts[guild_id][draft.current_player]
            await interaction.channel.send(f"{next_player.mention}, it's your turn to pick!")
        
        await draft.set_draft_channel(interaction.channel)
        await draft.update_pack_display()
        
    except Exception as e:
        print(f"Error in startdraft: {e}")  # Log the error
        await interaction.followup.send(
            "An unexpected error occurred while starting the draft. Please try again later.", 
            ephemeral=True
        )

@bot.tree.command(
    name="show_pack",
    description="Show your current pack"
)
async def show_pack(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    
    if guild_id not in bot.draft_sessions:
        await interaction.response.send_message("There's no active draft in this server!", ephemeral=True)
        return
    
    draft = bot.draft_sessions[guild_id]
    
    # Check if it's the player's turn
    if interaction.user != bot.active_drafts[guild_id][draft.current_player]:
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
        title=f"Pack {draft.pack_number + 1}, Pick {draft.cards_per_pack - len(current_pack) + 1}",
        description=f"Your current pack:\n{pack_contents}",
        color=discord.Color.blue()
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# First define the autocomplete function
async def pick_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    """Provide autocomplete suggestions for card names in the current pack"""
    guild_id = interaction.guild_id
    
    if guild_id not in bot.draft_sessions:
        return []
    
    draft = bot.draft_sessions[guild_id]
    current_pack = draft.get_current_pack()
    
    if not current_pack or interaction.user != bot.active_drafts[guild_id][draft.current_player]:
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

# Then define the pick command with autocomplete
@bot.tree.command(name="pick", description="Pick a card from your current pack")
@app_commands.describe(
    card_name="Start typing a card name to see available options"
)
@app_commands.autocomplete(card_name=pick_autocomplete)
async def pick(interaction: discord.Interaction, card_name: str):
    guild_id = interaction.guild_id
    
    if guild_id not in bot.draft_sessions:
        await interaction.response.send_message("There's no active draft in this server!", ephemeral=True)
        return
    
    draft = bot.draft_sessions[guild_id]
    current_pack = draft.get_current_pack()
    
    # Find the card in the current pack
    picked_card = next((card for card in current_pack if card.name.lower() == card_name.lower()), None)
    if not picked_card:
        await interaction.response.send_message(
            f"Couldn't find card '{card_name}' in the current pack!",
            ephemeral=True
        )
        return

    # Add to player's pool and record pick
    draft.player_pools[interaction.user].append(picked_card)
    current_pack.remove(picked_card)
    draft.picked_cards[interaction.user.display_name] = picked_card

    # Update the display
    await draft.update_pack_display()

    # Move to next player
    draft.current_player = (draft.current_player + draft.direction) % draft.num_players

    await interaction.response.send_message(
        f"You picked {picked_card.name}!",
        ephemeral=True
    )

    # Handle next player notification
    if draft.is_bot_turn():
        while draft.is_bot_turn():
            picked_card = await draft.handle_bot_picks()
            if picked_card:
                draft.picked_cards[draft.get_current_player().name] = picked_card
                await draft.update_pack_display()
    
    # Notify next human player
    next_player = bot.active_drafts[guild_id][draft.current_player]
    await interaction.channel.send(f"{next_player.mention}, it's your turn to pick!")

@bot.tree.command(
    name="viewpool",
    description="View a player's drafted cards"
)
@app_commands.describe(
    player="The player whose pool you want to view (defaults to yourself)"
)
async def viewpool(
    interaction: discord.Interaction,
    player: discord.Member = None
):
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

# Run the bot
if __name__ == "__main__":
    bot.run(os.getenv('DISCORD_BOT_TOKEN'))
