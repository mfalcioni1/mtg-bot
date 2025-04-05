from typing import Dict, List, Optional, Union, Any
import random
import discord
from dataclasses import dataclass
from cube_parser import CardData
from draft_bots import DraftBot, create_bot, RandomBot
from pack_display import PackDisplay, PackState
from io import StringIO
from storage_manager import StorageManager

@dataclass
class DraftState:
    """Represents the current state of a Rochester draft"""
    current_pack_number: int  # Which pack we're on (1-based)
    current_pack_index: int   # Which player's pack we're drafting (0-based)
    current_pick: int        # Which pick we're on in the current pack (1-based)
    direction: int           # 1 for clockwise, -1 for counterclockwise
    current_player: int      # Index of current player (0-based)

    def to_dict(self) -> Dict[str, Any]:
        """Convert DraftState to dictionary for serialization"""
        return {
            'current_pack_number': self.current_pack_number,
            'current_pack_index': self.current_pack_index,
            'current_pick': self.current_pick,
            'direction': self.direction,
            'current_player': self.current_player
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DraftState':
        """Create DraftState from dictionary"""
        return cls(
            current_pack_number=data['current_pack_number'],
            current_pack_index=data['current_pack_index'],
            current_pick=data['current_pick'],
            direction=data['direction'],
            current_player=data['current_player']
        )

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
        self.storage = StorageManager()
        
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
            bot_player = create_bot(name=f"Bot_{i+1}")
            self.bots.append(bot_player)
            self.player_pools[bot_player] = []
    
    def initialize_player_pools(self, human_players: List[discord.Member]):
        """Initialize empty card pools for all players and bots"""
        self.active_players = human_players
        self.player_pools = {player: [] for player in human_players}
        for bot_player in self.bots:
            self.player_pools[bot_player] = []
    
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
        
        # Then process bot players
        for bot_player in self.bots:
            results.append(f"\n{bot_player.name}'s Picks:")
            for card in self.player_pools[bot_player]:
                results.append(f"- {card.name}")
        
        return "\n".join(results)

    def to_dict(self) -> Dict[str, Any]:
        """Convert draft state to dictionary for serialization"""
        return {
            'cards': [card.to_dict() for card in self.cards],
            'num_players': self.num_players,
            'num_human_players': self.num_human_players,
            'cards_per_pack': self.cards_per_pack,
            'num_packs': self.num_packs,
            'packs': [[card.to_dict() for card in pack] for pack in self.packs],
            'player_pools': {
                (player.id if isinstance(player, discord.Member) else player.name): 
                [card.to_dict() for card in cards]
                for player, cards in self.player_pools.items()
            },
            'bots': [{'name': bot_player.name, 'type': type(bot_player).__name__} for bot_player in self.bots],
            'picked_cards': {
                player: [card.to_dict() for card in cards]
                for player, cards in self.picked_cards.items()
            },
            'draft_channel_id': self.draft_channel.id if self.draft_channel else None,
            'active_player_ids': [player.id for player in self.active_players],
            'state': self.state.to_dict()
        }

    @classmethod
    async def from_dict(cls, data: Dict[str, Any], draft_bot: discord.ext.commands.Bot) -> 'RochesterDraft':
        """Create RochesterDraft from dictionary"""
        # Recreate cards
        cards = [CardData.from_dict(card_data) for card_data in data['cards']]
        
        # Create draft instance
        draft = cls(
            cards=cards,
            num_players=data['num_players'],
            cards_per_pack=data['cards_per_pack'],
            num_packs=data['num_packs'],
            num_bots=len(data['bots'])
        )
        
        # Recreate packs
        draft.packs = [[CardData.from_dict(card_data) for card_data in pack] for pack in data['packs']]
        
        # Recreate bot players
        for bot_data in data['bots']:
            bot_type = bot_data['type']
            if bot_type == 'RandomBot':
                draft.bots.append(RandomBot(bot_data['name']))
        
        # Recreate player pools
        draft.player_pools = {}
        for player_id, cards_data in data['player_pools'].items():
            if player_id.isdigit():
                # Human player
                player = await draft_bot.fetch_user(int(player_id))
                draft.player_pools[player] = [CardData.from_dict(card_data) for card_data in cards_data]
            else:
                # Bot player
                bot_player = next(b for b in draft.bots if b.name == player_id)
                draft.player_pools[bot_player] = [CardData.from_dict(card_data) for card_data in cards_data]
        
        # Recreate picked cards
        draft.picked_cards = {
            player: [CardData.from_dict(card_data) for card_data in cards_data]
            for player, cards_data in data['picked_cards'].items()
        }
        
        # Recreate active players
        draft.active_players = []
        for player_id in data['active_player_ids']:
            player = await draft_bot.fetch_user(player_id)
            draft.active_players.append(player)
        
        # Set draft channel
        if data['draft_channel_id']:
            channel = await draft_bot.fetch_channel(data['draft_channel_id'])
            draft.draft_channel = channel
        
        # Set state
        draft.state = DraftState.from_dict(data['state'])
        
        return draft

    @classmethod
    async def load_state(cls, guild_id: int, channel_id: int, draft_bot: 'DraftBot') -> Optional['RochesterDraft']:
        """Load draft state from storage"""
        try:
            # Load state from storage
            state_data = await draft_bot.storage.load_game_state("rochester", guild_id, channel_id)
            if not state_data:
                return None
            
            # Create draft instance from state
            draft = await cls.from_dict(state_data, draft_bot)  # Use draft_bot directly
            draft.storage = draft_bot.storage
            draft.draft_channel = draft_bot.get_channel(channel_id)
            
            return draft
            
        except Exception as e:
            print(f"Error loading draft state: {e}")
            return None

    async def save_state(self, guild_id: int, channel_id: int) -> bool:
        """Save draft state to storage"""
        try:
            return await self.storage.save_game_state(
                game_type="rochester",
                guild_id=guild_id,
                channel_id=channel_id,
                state=self.to_dict()
            )
        except Exception as e:
            print(f"Error saving draft state: {e}")
            return False 