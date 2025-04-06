from typing import Dict, List, Optional, Union
import random
import discord
from dataclasses import dataclass
from cube_parser import CardData
from draft_bots import DraftBot, create_bot
from pack_display import PackDisplay, PackState
from io import StringIO
import logging
from storage_manager import StorageManager

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
    def __init__(self, cards: List[CardData], num_players: int, cards_per_pack: int, num_packs: int, num_bots: int = 0, guild_id: Optional[int] = None, channel_id: Optional[int] = None):
        self.cards = cards
        self.num_players = num_players
        self.num_human_players = num_players - num_bots
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
        
        # Initialize storage if guild_id and channel_id are provided
        self.storage = StorageManager("draft", str(guild_id), str(channel_id)) if guild_id and channel_id else None
    
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
        
        # Save state after each pick
        if self.storage:
            await self.save_state()
        
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
                
                # Final state save
                if self.storage:
                    await self.save_state()
                
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

    async def save_state(self) -> None:
        """Save complete draft state"""
        try:
            # Save configuration
            await self.storage.write_json("config.json", {
                "num_players": self.num_players,
                "num_human_players": self.num_human_players,
                "cards_per_pack": self.cards_per_pack,
                "num_packs": self.num_packs
            })
            
            # Save current state
            await self.storage.write_json("current_state.json", {
                "current_pack_number": self.state.current_pack_number,
                "current_pack_index": self.state.current_pack_index,
                "current_pick": self.state.current_pick,
                "direction": self.state.direction,
                "current_player": self.state.current_player,
                # Add picked cards for current pack
                "picked_cards": {
                    player_name: [card.to_dict() for card in cards]
                    for player_name, cards in self.picked_cards.items()
                }
            })
            
            # Save player data
            await self.storage.write_json("players.json", {
                "active_players": [str(p.id) for p in self.active_players],
                "bot_players": [b.to_dict() for b in self.bots],
                "player_order": [str(p.id) if isinstance(p, discord.Member) else p.name 
                               for p in self.active_players + self.bots]
            })
            
            # Save draft content with all necessary data
            await self.storage.write_json("content.json", {
                "cards": [card.to_dict() for card in self.cards],
                "packs": [[card.to_dict() for card in pack] for pack in self.packs],
                "player_pools": {
                    str(player.id) if isinstance(player, discord.Member) else player.name: 
                    [card.to_dict() for card in cards]
                    for player, cards in self.player_pools.items()
                }
            })
            
            # Add player name mapping
            await self.storage.write_json("player_names.json", {
                str(player.id): player.display_name 
                for player in self.active_players
            })
            
            logging.info(f"Successfully saved draft state.")
            
        except Exception as e:
            logging.error(f"Error saving draft state: {str(e)}")

    @staticmethod
    async def load_draft(guild_id: int, channel_id: int, client: discord.Client) -> Optional['RochesterDraft']:
        """Load draft from storage"""
        storage = StorageManager("draft", str(guild_id), str(channel_id))
        
        try:
            # Load all state components
            config = await storage.read_json("config.json")
            current_state = await storage.read_json("current_state.json")
            players = await storage.read_json("players.json")
            content = await storage.read_json("content.json")
            player_names = await storage.read_json("player_names.json")
            
            logging.info(f"Attempting to load draft for guild {guild_id}, channel {channel_id}")
            logging.info(f"Found config: {bool(config)}, state: {bool(current_state)}, players: {bool(players)}, content: {bool(content)}, names: {bool(player_names)}")
            
            if not all([config, current_state, players, content]):
                logging.info("Missing some state components, skipping draft recovery")
                return None

            # Log player names if available
            if player_names:
                logging.info(f"Found player name mappings: {player_names}")

            # Get guild object
            guild = client.get_guild(guild_id)
            if not guild:
                logging.error(f"Could not find guild {guild_id}")
                return None

            # Initialize draft instance
            draft = RochesterDraft(
                cards=[CardData.from_dict(c) for c in content["cards"]],
                num_players=config["num_players"],
                cards_per_pack=config["cards_per_pack"],
                num_packs=config["num_packs"],
                num_bots=config["num_players"] - config["num_human_players"],
                guild_id=guild_id,
                channel_id=channel_id
            )

            # Set storage manager
            draft.storage = storage

            # Restore state
            draft.state = DraftState(**{k: v for k, v in current_state.items() 
                                      if k not in ['picked_cards']})
            
            # Restore picked cards
            if 'picked_cards' in current_state:
                draft.picked_cards = {
                    player_name: [CardData.from_dict(c) for c in cards]
                    for player_name, cards in current_state['picked_cards'].items()
                }
            
            # Restore players using guild.fetch_member
            draft.active_players = []
            for player_id in players["active_players"]:
                try:
                    member = await guild.fetch_member(int(player_id))
                    if member:
                        draft.active_players.append(member)
                        logging.info(f"Restored player {member.display_name}")
                    else:
                        logging.error(f"Could not find member {player_id} in guild {guild_id}")
                except discord.NotFound:
                    logging.error(f"Member {player_id} not found in guild {guild_id}")
                except Exception as e:
                    logging.error(f"Error fetching member {player_id}: {e}")
            
            # Restore bots
            draft.bots = [DraftBot.from_dict(b) for b in players["bot_players"]]
            
            # Restore draft content
            draft.packs = [[CardData.from_dict(c) for c in pack] for pack in content["packs"]]
            
            # Restore player pools using guild members
            draft.player_pools = {}
            for player_id, cards in content["player_pools"].items():
                if player_id.isdigit():
                    try:
                        member = await guild.fetch_member(int(player_id))
                        if member:
                            draft.player_pools[member] = [CardData.from_dict(c) for c in cards]
                            logging.info(f"Restored pool for {member.display_name}")
                        else:
                            logging.error(f"Could not find member {player_id} in guild {guild_id}")
                    except discord.NotFound:
                        logging.error(f"Member {player_id} not found in guild {guild_id}")
                    except Exception as e:
                        logging.error(f"Error fetching member {player_id}: {e}")
                else:
                    bot = next((b for b in draft.bots if b.name == player_id), None)
                    if bot:
                        draft.player_pools[bot] = [CardData.from_dict(c) for c in cards]
                        logging.info(f"Restored pool for bot {bot.name}")
            
            logging.info(f"Successfully loaded draft with {len(draft.active_players)} players and {len(draft.bots)} bots")
            
            # Validate that we have all required players
            if len(draft.active_players) != config["num_human_players"]:
                logging.error(f"Failed to restore all human players. Expected {config['num_human_players']}, got {len(draft.active_players)}")
                return None
            
            return draft
            
        except Exception as e:
            logging.error(f"Error loading draft state: {str(e)}")
            import traceback
            logging.error(traceback.format_exc())
            return None 