from typing import Dict, List, Set, Optional
import discord

class V4CBGame:
    def __init__(self, channel_id: int):
        self.channel_id = channel_id
        self.banned_cards: Set[str] = set()
        self.submissions: Dict[discord.Member, List[str]] = {}
        self.is_active = False
        self.scores: Dict[str, int] = {}  # Track scores by player name
        self.current_round_revealed = False  # Track if current round is revealed
        
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
            return False, f"**Submission Refused:** Your submission contains banned card(s):\n**{', '.join(banned_cards)}**\n\nPlease submit a new set of cards that doesn't include banned cards."
            
        self.submissions[player] = cards
        return True, None
    
    def get_all_submissions(self) -> Dict[discord.Member, List[str]]:
        """Get all submissions for reveal"""
        return self.submissions
    
    def clear_submissions(self) -> None:
        """Clear all current submissions without ending the game"""
        self.submissions.clear()
    
    def reveal(self) -> Dict[discord.Member, List[str]]:
        """Get all submissions but don't clear them until winner is submitted"""
        submissions = self.submissions.copy()
        self.current_round_revealed = True
        return submissions
    
    def update_banned_list(self, new_banned_cards: List[str]) -> None:
        """Add new cards to the banned list"""
        # Convert new cards to lowercase and add them to existing banned cards
        self.banned_cards.update(card.lower() for card in new_banned_cards)
    
    def end_game(self) -> None:
        """End the current game"""
        self.is_active = False
        self.submissions.clear() 
    
    def set_banned_list(self, banned_list: List[str]) -> None:
        """Overwrite the current banned list with a new one"""
        self.banned_cards = set(card.lower() for card in banned_list) 
    
    def clear_banned_list(self) -> None:
        """Clear all cards from the banned list"""
        self.banned_cards.clear()
    
    def remove_banned_card(self, card: str) -> tuple[bool, Optional[str]]:
        """
        Remove a single card from the banned list
        Returns (success, error_message)
        """
        card = card.lower()
        if card not in self.banned_cards:
            return False, f"Card '{card}' is not in the banned list"
        
        self.banned_cards.remove(card)
        return True, None

    def submit_winner(self, winner_names: List[str]) -> tuple[bool, Optional[str]]:
        """
        Submit winner(s) for the current round and update scores
        Returns (success, error_message)
        """
        if not self.current_round_revealed:
            return False, "The current round hasn't been revealed yet!"
        
        # Validate all winners are current players
        current_players = {player.name for player in self.submissions.keys()} | {player.display_name for player in self.submissions.keys()}
        invalid_winners = [name for name in winner_names if name not in current_players]
        if invalid_winners:
            return False, f"Invalid player name(s): {', '.join(invalid_winners)}. Select a player from {current_players}"
        
        # Update scores
        for winner in winner_names:
            if winner not in self.scores:
                self.scores[winner] = 0
            self.scores[winner] += 1
        
        # Clear submissions for next round
        self.submissions.clear()
        self.current_round_revealed = False
        
        return True, None

    def get_scores(self) -> Dict[str, int]:
        """Get current game scores"""
        return self.scores

    def set_scores(self, new_scores: Dict[str, int]) -> None:
        """Overwrite the current scores"""
        self.scores = new_scores.copy() 