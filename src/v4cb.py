from typing import Dict, List, Set, Optional
import discord
from storage_manager import StorageManager
import logging
from discord.ext import commands

class V4CBGame:
    def __init__(self, channel_id: int, server_id: int):
        self.channel_id = str(channel_id)  # Convert to string for storage
        self.server_id = str(server_id)    # Convert to string for storage
        self.banned_cards: Set[str] = set()
        self.submissions: Dict[discord.Member, List[str]] = {}
        self.is_active = False
        self.scores: Dict[str, int] = {}
        self.current_round_revealed = False
        self.storage = StorageManager("v4cb", self.server_id, self.channel_id)
        
    @staticmethod
    async def game_exists(server_id: str, channel_id: str) -> bool:
        """Check if a game exists in storage for this channel"""
        try:
            storage_instance = StorageManager("v4cb", server_id, channel_id)
            banned_data = await storage_instance.read_json("banned_list.json")
            scores_data = await storage_instance.read_json("scores.json")
            return banned_data is not None or scores_data is not None
        except Exception as e:
            logging.error(f"Error checking game existence: {str(e)}")
            return False

    async def load_state(self) -> None:
        """Load game state from storage"""
        try:
            # Load banned list
            banned_data = await self.storage.read_json("banned_list.json")
            if banned_data:
                self.banned_cards = set(banned_data.get("cards", []))
                self.is_active = True  # If we have data, the game is active
            
            # Load scores
            scores_data = await self.storage.read_json("scores.json")
            if scores_data:
                self.scores = scores_data.get("scores", {})
                
        except Exception as e:
            logging.error(f"Error loading game state: {str(e)}")

    async def save_state(self) -> None:
        """Save current game state to storage"""
        try:
            # Save banned list
            await self.storage.write_json(
                "banned_list.json",
                {"cards": list(self.banned_cards)}
            )
            
            # Save scores
            await self.storage.write_json(
                "scores.json",
                {"scores": self.scores}
            )
            
        except Exception as e:
            logging.error(f"Error saving game state: {str(e)}")

    async def start_game(self, banned_list: List[str]) -> None:
        """Start a new game with the given banned list"""
        self.banned_cards = set(card.lower() for card in banned_list)
        self.submissions.clear()
        self.is_active = True
        await self.save_state()
    
    def submit_cards(self, player: discord.Member, cards: List[str]) -> tuple[bool, Optional[str]]:
        """
        Submit cards for a player. Returns (success, error_message)
        """
        if not self.is_active:
            return False, "No active game in this channel!"
            
        # Convert to lowercase for comparison
        cards = [card.lower() for card in cards]
        
        # Check if exactly 4 cards
        if len(cards) != 4:
            return False, "You must submit exactly 4 cards!"
            
        # Check for duplicates
        if len(set(cards)) != 4:
            return False, "All cards must be unique!"
            
        # Check against banned list
        banned_cards = [card for card in cards if card in self.banned_cards]
        if banned_cards:
            return False, f"**Submission Refused:** Your submission contains banned card(s):\n**{', '.join(banned_cards)}**\n\nPlease submit a new set of cards that doesn't include banned cards."
            
        self.submissions[player] = cards
        return True, None
    
    def get_all_submissions(self) -> Dict[discord.Member, List[str]]:
        """Get all submissions for reveal"""
        return self.submissions
    
    async def clear_submissions(self) -> None:
        """Clear all current submissions without ending the game"""
        self.submissions.clear()
        # No need to save state as submissions are temporary

    def reveal(self) -> Dict[discord.Member, List[str]]:
        """Get all submissions but don't clear them until winner is submitted"""
        submissions = self.submissions.copy()
        self.current_round_revealed = True
        return submissions
    
    async def update_banned_list(self, new_banned_cards: List[str]) -> None:
        """Add new cards to the banned list"""
        self.banned_cards.update(card.lower() for card in new_banned_cards)
        await self.save_state()
    
    async def end_game(self) -> None:
        """End the current game"""
        self.is_active = False
        self.submissions.clear()
        await self.save_state()
    
    async def set_banned_list(self, banned_list: List[str]) -> None:
        """Overwrite the current banned list with a new one"""
        self.banned_cards = set(card.lower() for card in banned_list)
        await self.save_state()
    
    async def clear_banned_list(self) -> None:
        """Clear all cards from the banned list"""
        self.banned_cards.clear()
        await self.save_state()
    
    async def remove_banned_card(self, card: str) -> tuple[bool, Optional[str]]:
        """
        Remove a single card from the banned list
        Returns (success, error_message)
        """
        card = card.lower()
        if card not in self.banned_cards:
            return False, f"Card '{card}' is not in the banned list"
        
        self.banned_cards.remove(card)
        await self.save_state()
        return True, None

    async def submit_winner(self, winner_names: List[str]) -> tuple[bool, Optional[str]]:
        """
        Submit winner(s) for the current round and update scores
        Returns (success, error_message)
        """
        if not self.current_round_revealed:
            return False, "The current round hasn't been revealed yet!"
        
        # Create mapping of both name and display_name to the display_name
        name_mapping = {}
        for player in self.submissions.keys():
            name_mapping[player.name.lower()] = player.display_name
            name_mapping[player.display_name.lower()] = player.display_name
        
        # Validate all winners are current players and convert to display_names
        display_names = []
        invalid_winners = []
        for name in winner_names:
            name_lower = name.strip().lower()
            if name_lower in name_mapping:
                display_names.append(name_mapping[name_lower])
            else:
                invalid_winners.append(name)
        
        if invalid_winners:
            valid_names = sorted(set(name_mapping.values()))  # Get unique display_names
            return False, f"Invalid player name(s): {', '.join(invalid_winners)}. Select a player from: {', '.join(valid_names)}"
        
        # Update scores using display_names
        for display_name in display_names:
            if display_name not in self.scores:
                self.scores[display_name] = 0
            self.scores[display_name] += 1
        
        # Clear submissions for next round
        self.submissions.clear()
        self.current_round_revealed = False
        
        # Save the updated scores
        await self.save_state()
        return True, None

    def get_scores(self) -> Dict[str, int]:
        """Get current game scores"""
        return self.scores

    async def set_scores(self, new_scores: Dict[str, int]) -> None:
        """Overwrite the current scores"""
        self.scores = new_scores.copy()
        await self.save_state()

    async def get_banned_list_pages(self) -> List[str]:
        """Get the banned list formatted into pages"""
        if not self.banned_cards:
            return ["No cards are currently banned."]
            
        # Sort the banned cards alphabetically
        sorted_cards = sorted(self.banned_cards)
        
        # Create a paginator with appropriate line length for embeds
        paginator = commands.Paginator(prefix="", suffix="", max_size=1024)
        
        # Add each card on its own line with a bullet point
        for card in sorted_cards:
            paginator.add_line(f"• {card}")
        
        return paginator.pages

    async def create_banned_list_embeds(self) -> List[discord.Embed]:
        """Create a list of embeds for the banned list"""
        pages = await self.get_banned_list_pages()
        embeds = []
        
        for i, page in enumerate(pages, 1):
            embed = discord.Embed(
                title=f"Banned Cards ({len(self.banned_cards)} total)",  # Added total count
                description=page,
                color=discord.Color.red()
            )
            embed.set_footer(text=f"Page {i}/{len(pages)}")
            embeds.append(embed)
            
        return embeds

class BannedListPaginator(discord.ui.View):
    def __init__(self, embeds: List[discord.Embed]):
        super().__init__(timeout=180)  # 3 minute timeout
        self.embeds = embeds
        self.current_page = 0
        
        # Disable buttons if there's only one page
        if len(self.embeds) == 1:
            self.children[0].disabled = True
            self.children[1].disabled = True

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.gray)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = (self.current_page - 1) % len(self.embeds)
        await interaction.response.edit_message(embed=self.embeds[self.current_page])

    @discord.ui.button(label="Next", style=discord.ButtonStyle.gray)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = (self.current_page + 1) % len(self.embeds)
        await interaction.response.edit_message(embed=self.embeds[self.current_page])

    async def on_timeout(self):
        # Disable all buttons when the view times out
        for item in self.children:
            item.disabled = True
        # Try to update the message with disabled buttons
        try:
            await self.message.edit(view=self)
        except:
            pass 