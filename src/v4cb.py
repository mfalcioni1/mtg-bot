from typing import Dict, List, Set, Optional
import discord

class V4CBGame:
    def __init__(self, channel_id: int):
        self.channel_id = channel_id
        self.banned_cards: Set[str] = set()
        self.submissions: Dict[discord.Member, List[str]] = {}
        self.is_active = False
        
    def start_game(self, banned_list: List[str]) -> None:
        """Start a new game with the given banned list"""
        self.banned_cards = set(card.lower() for card in banned_list)
        self.submissions.clear()
        self.is_active = True
    
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
            return False, f"The following cards are banned: {', '.join(banned_cards)}"
            
        self.submissions[player] = cards
        return True, None
    
    def get_all_submissions(self) -> Dict[discord.Member, List[str]]:
        """Get all submissions for reveal"""
        return self.submissions
    
    def update_banned_list(self, new_banned_cards: List[str]) -> None:
        """Update the banned list with new cards"""
        self.banned_cards = set(card.lower() for card in new_banned_cards)
    
    def end_game(self) -> None:
        """End the current game"""
        self.is_active = False
        self.submissions.clear() 