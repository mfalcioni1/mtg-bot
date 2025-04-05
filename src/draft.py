from typing import Dict, List, Optional, Union
import random
import discord
from dataclasses import dataclass
from cube_parser import CardData
from draft_bots import DraftBot, create_bot
from pack_display import PackDisplay, PackState
from io import StringIO

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
        self.picked_cards: Dict[str, List[CardData]] = {}
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
        self.bots = [create_bot(name=f"Bot_{i+1}") for i in range(num_bots)]
        # Don't initialize player pools here anymore, it will be done in initialize_player_pools
    
    def initialize_player_pools(self, players: List[discord.Member]):
        """Initialize empty card pools for all players and bots"""
        # First store the players temporarily
        self.active_players = players
        
        # Create combined list of all players (human and bots)
        all_players = players + self.bots
        
        # Randomize the complete player order
        randomized_players = random.sample(all_players, len(all_players))
        
        # Update active_players and player_pools based on the randomized order
        self.active_players = [p for p in randomized_players if isinstance(p, discord.Member)]
        self.bots = [p for p in randomized_players if isinstance(p, DraftBot)]
        
        # Initialize pools in randomized order
        self.player_pools = {player: [] for player in randomized_players}
    
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
        all_players = self.active_players + self.bots
        return all_players[self.state.current_player % len(all_players)]
    
    def is_bot_turn(self) -> bool:
        """Check if it's currently a bot's turn"""
        current_player = self.get_current_player()
        return isinstance(current_player, DraftBot)
    
    def advance_draft(self):
        """Advance the draft state after a pick"""
        # Increment pick number
        self.state.current_pick += 1
        
        # If we've completed a pack
        if self.state.current_pick > self.cards_per_pack:
            self.move_to_next_pack()
            return
        
        # Within a pack, snake back and forth
        if self.state.current_pick <= self.cards_per_pack // 2:
            # First half of pack - go forward
            self.state.current_player = (self.state.current_pack_index + self.state.current_pick - 1) % self.num_players
        else:
            # Second half of pack - go backward
            reverse_pick = self.cards_per_pack - self.state.current_pick + 1
            self.state.current_player = (self.state.current_pack_index + reverse_pick - 1) % self.num_players
    
    def move_to_next_pack(self):
        """Move to the next pack in the draft"""
        # Clear the picked cards before moving to next pack
        self.picked_cards = {}
        
        self.state.current_pack_index = (self.state.current_pack_index + 1) % self.num_players
        
        if self.state.current_pack_index == 0:
            self.state.current_pack_number += 1
        
        # Reset pick counter for new pack
        self.state.current_pick = 1
        
        # First player of new pack is determined by current_pack_index
        self.state.current_player = self.state.current_pack_index
    
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
        
        # Add to picked cards list for this pack
        player_name = player.name if isinstance(player, DraftBot) else player.display_name
        if player_name not in self.picked_cards:
            self.picked_cards[player_name] = []
        self.picked_cards[player_name].append(picked_card)
        
        # Update the display before advancing the draft state
        await self.update_pack_display()
        
        # Advance draft state
        self.advance_draft()
        
        if self.is_draft_complete():
            if self.draft_channel:
                results = await self.generate_draft_results()
                await self.draft_channel.send(
                    "Draft complete! Here are the results:",
                    file=discord.File(
                        fp=StringIO(results),
                        filename="draft_results.txt"
                    )
                )
            return picked_card
        
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
        
        # Get pack opener
        pack_opener = self.active_players[self.state.current_pack_index].display_name \
            if self.state.current_pack_index < self.num_human_players \
            else self.bots[self.state.current_pack_index - self.num_human_players].name

        # Calculate which pack number this is for the opener
        player_pack_number = (self.state.current_pack_index + 1) % self.num_players
        if player_pack_number == 0:
            player_pack_number = self.num_players

        # Calculate unique pack ID based on both pack number and pack index
        unique_pack_id = (self.state.current_pack_number - 1) * self.num_players + self.state.current_pack_index + 1

        pack_state = PackState(
            available_cards=current_pack,
            picked_cards=self.picked_cards,
            pack_number=unique_pack_id,  # Use unique pack ID here
            pack_opener=pack_opener,
            current_player=player_name,
            player_pack_number=player_pack_number
        )

        await self.pack_display.create_or_update_pack_display(
            self.draft_channel,
            pack_state,
            self.draft_channel.guild.id
        ) 
    
    def is_draft_complete(self) -> bool:
        """Check if the draft is complete"""
        return (self.state.current_pack_number > self.num_packs or 
                (self.state.current_pack_number == self.num_packs and 
                 self.state.current_pack_index >= self.num_players))
    
    async def generate_draft_results(self) -> str:
        """Generate a simple text format of draft results"""
        results = ["=== Draft Results ===\n"]
        
        # Process human players first
        for player in self.active_players:
            results.append(f"\n{player.display_name}'s Picks:")
            for card in self.player_pools[player]:
                results.append(f"- {card.name}")
        
        # Then process bots
        for bot in self.bots:
            results.append(f"\n{bot.name}'s Picks:")
            for card in self.player_pools[bot]:
                results.append(f"- {card.name}")
        
        return "\n".join(results) 