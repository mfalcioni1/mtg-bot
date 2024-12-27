from typing import Dict, List, Optional, Union
import random
import discord
from dataclasses import dataclass
from cube_parser import CardData
from draft_bots import DraftBot, create_bot
from pack_display import PackDisplay, PackState

@dataclass
class DraftState:
    """Represents the current state of a Rochester draft"""
    current_pack_number: int  # Which pack we're on (1-based)
    current_pack_index: int   # Which player's pack we're drafting (0-based)
    current_pick: int        # Which pick we're on in the current pack (1-based)
    direction: int           # 1 for clockwise, -1 for counterclockwise
    current_player: int      # Index of current player (0-based)

class RochesterDraft:
    """Manages a Rochester draft session"""
    def __init__(self, cards: List[CardData], num_players: int, cards_per_pack: int, num_packs: int, num_bots: int = 0):
        self.cards = cards
        self.num_players = num_players + num_bots
        self.num_human_players = num_players
        self.cards_per_pack = cards_per_pack
        self.num_packs = num_packs
        self.packs: List[List[CardData]] = []
        self.player_pools: Dict[Union[discord.Member, DraftBot], List[CardData]] = {}
        self.bots: List[DraftBot] = []
        self.pack_display = PackDisplay()
        self.picked_cards: Dict[str, CardData] = {}
        self.draft_channel: Optional[discord.TextChannel] = None
        self.active_players: List[discord.Member] = []
        
        # Rochester-specific state
        self.state = DraftState(
            current_pack_number=1,
            current_pack_index=0,
            current_pick=1,
            direction=1,
            current_player=0
        )
    
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
    
    def prepare_packs(self):
        """Create packs for the draft"""
        random.shuffle(self.cards)
        cards_needed = self.num_players * self.num_packs * self.cards_per_pack
        if len(self.cards) < cards_needed:
            raise ValueError(f"Not enough cards in cube. Need {cards_needed} but only have {len(self.cards)}")
        
        # Create packs - one pack at a time for each player
        for pack_num in range(self.num_packs):
            for player in range(self.num_players):
                start_idx = (pack_num * self.num_players + player) * self.cards_per_pack
                end_idx = start_idx + self.cards_per_pack
                pack = self.cards[start_idx:end_idx]
                self.packs.append(pack)
    
    def get_current_pack(self) -> Optional[List[CardData]]:
        """Get the current pack being drafted"""
        pack_idx = (self.state.current_pack_number - 1) * self.num_players + self.state.current_pack_index
        return self.packs[pack_idx] if pack_idx < len(self.packs) else None
    
    def get_current_player(self) -> Union[discord.Member, DraftBot]:
        """Get the current player or bot"""
        if self.is_bot_turn():
            return self.bots[self.state.current_player - self.num_human_players]
        return self.active_players[self.state.current_player]
    
    def is_bot_turn(self) -> bool:
        """Check if it's currently a bot's turn"""
        return self.state.current_player >= self.num_human_players
    
    def advance_draft(self):
        """Advance the draft state after a pick"""
        # Increment pick number
        self.state.current_pick += 1
        
        # Move to next player
        self.state.current_player = (self.state.current_player + self.state.direction) % self.num_players
        
        # If we've gone through all players twice (snake draft), move to next pack
        if self.state.current_pick > self.cards_per_pack:
            self.move_to_next_pack()
    
    def move_to_next_pack(self):
        """Move to the next pack in the draft"""
        self.state.current_pack_index += 1
        if self.state.current_pack_index >= self.num_players:
            self.state.current_pack_index = 0
            self.state.current_pack_number += 1
        
        # Reset pick counter and direction
        self.state.current_pick = 1
        self.state.current_player = self.state.current_pack_index
        self.picked_cards.clear()
    
    async def handle_pick(self, player: Union[discord.Member, DraftBot], card_name: str) -> Optional[CardData]:
        """Handle a player making a pick"""
        current_pack = self.get_current_pack()
        if not current_pack:
            return None
            
        picked_card = next((card for card in current_pack if card.name.lower() == card_name.lower()), None)
        if not picked_card:
            return None
            
        # Add to player's pool and remove from pack
        self.player_pools[player].append(picked_card)
        current_pack.remove(picked_card)
        self.picked_cards[player.name if isinstance(player, DraftBot) else player.display_name] = picked_card
        
        # Advance draft state
        self.advance_draft()
        
        return picked_card
    
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
            pack_number=self.state.current_pack_number,
            pick_number=self.state.current_pick,
            current_player=player_name
        )

        await self.pack_display.create_or_update_pack_display(
            self.draft_channel,
            pack_state,
            self.draft_channel.guild.id
        ) 