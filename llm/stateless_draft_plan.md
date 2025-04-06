This is our plan to implement a more stateless design to the draft management process of our bot. Let's break this down into several key components and phases.

## 1. Draft State Data Model

First, we need to define what draft state needs to be persisted. Looking at `RochesterDraft` class in `draft.py`, we need to store:

```python
class DraftStateStorage:
    """Represents the complete state of a draft that needs to be persisted"""
    def __init__(self):
        self.draft_config = {
            "num_players": int,
            "num_human_players": int,
            "cards_per_pack": int,
            "num_packs": int
        }
        
        self.current_state = {
            "current_pack_number": int,
            "current_pack_index": int,
            "current_pick": int,
            "direction": int,
            "current_player": int
        }
        
        self.player_data = {
            "active_players": List[str],  # Store Discord IDs
            "bot_players": List[str],     # Store bot names
            "player_order": List[str]     # Combined order of players/bots
        }
        
        self.draft_content = {
            "cards": List[CardData],      # All cards in draft
            "packs": List[List[CardData]], # Current pack state
            "player_pools": Dict[str, List[CardData]]  # Map player ID/name to their picks
        }
```

## 2. Storage Integration

We can leverage the existing `StorageManager` class from `storage_manager.py`. We'll need to:

1. Add a new game type "draft" alongside "v4cb":

```python
# In draft.py
class RochesterDraft:
    def __init__(self, cards: List[CardData], num_players: int, ...):
        self.storage = StorageManager("draft", str(guild_id), str(channel_id))
```

2. Create storage files for different aspects of state:
```
draft/
  {server_id}/
    {channel_id}/
      config.json        # Draft configuration
      current_state.json # Current draft state
      players.json       # Player information
      content.json       # Cards and packs
```

## 3. State Management Methods

Add these methods to `RochesterDraft`:

```python
class RochesterDraft:
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
                "current_player": self.state.current_player
            })
            
            # Save player data
            await self.storage.write_json("players.json", {
                "active_players": [str(p.id) for p in self.active_players],
                "bot_players": [b.name for b in self.bots],
                "player_order": self._get_serialized_player_order()
            })
            
            # Save draft content
            await self.storage.write_json("content.json", {
                "cards": [card.to_dict() for card in self.cards],
                "packs": [[card.to_dict() for card in pack] for pack in self.packs],
                "player_pools": self._get_serialized_player_pools()
            })
            
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
            
            if not all([config, current_state, players, content]):
                return None
                
            # Reconstruct draft instance
            draft = RochesterDraft(
                cards=[CardData.from_dict(c) for c in content["cards"]],
                num_players=config["num_players"],
                cards_per_pack=config["cards_per_pack"],
                num_packs=config["num_packs"],
                num_bots=config["num_players"] - config["num_human_players"]
            )
            
            # Restore state
            draft.state = DraftState(**current_state)
            
            # Restore players
            await draft._restore_players(players, client)
            
            # Restore draft content
            draft.packs = [[CardData.from_dict(c) for c in pack] for pack in content["packs"]]
            await draft._restore_player_pools(content["player_pools"], client)
            
            return draft
            
        except Exception as e:
            logging.error(f"Error loading draft state: {str(e)}")
            return None
```

## 4. Integration Points

We need to call `save_state()` at key points in the draft process:

1. After draft initialization:
```python
# In start_draft command
draft = RochesterDraft(cards, num_human_players, cards_per_pack, num_packs, num_bots)
draft.add_bots(num_bots)
draft.prepare_packs()
draft.initialize_player_pools(bot.active_drafts[guild_id])
await draft.save_state()  # Save initial state
```

2. After each pick:
```python
# In handle_pick method
async def handle_pick(self, player: Union[discord.Member, DraftBot], card_name: str):
    # ... existing pick handling ...
    
    self.advance_draft()
    await self.save_state()  # Save after state changes
```

3. When draft ends:
```python
# In handle_pick method
if self.is_draft_complete():
    await self.save_state()  # Final state save
    # ... existing completion handling ...
```

## 5. Recovery Process

Add recovery logic to the bot:

```python
# In bot.py
class DraftBot(commands.Bot):
    async def setup_hook(self):
        await self.recover_active_drafts()
    
    async def recover_active_drafts(self):
        """Recover any active drafts from storage"""
        for guild in self.guilds:
            for channel in guild.text_channels:
                storage = StorageManager("draft", str(guild.id), str(channel.id))
                
                # Check if draft exists
                if await storage.read_json("config.json"):
                    draft = await RochesterDraft.load_draft(guild.id, channel.id, self)
                    if draft:
                        self.draft_sessions[guild.id] = draft
                        await draft.set_draft_channel(channel)
                        await draft.update_pack_display()
                        logging.info(f"Recovered draft in channel {channel.id}")
```

## 6. Required Refactoring

1. Update `CardData` class to support serialization:
```python
# In cube_parser.py
@dataclass
class CardData:
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "type": self.type,
            "color_category": self.color_category
            # ... other fields ...
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CardData':
        return cls(**data)
```

2. Modify `DraftBot` class to support serialization:
```python
# In draft_bots.py
class DraftBot:
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "type": self.__class__.__name__
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'DraftBot':
        return create_bot(name=data["name"])
```

## 7. Testing Plan

1. Test state persistence:
   - Draft initialization
   - Mid-draft saves
   - Draft completion
   - Player pool accuracy

2. Test recovery scenarios:
   - Bot restart
   - Network interruption
   - Server disconnect

3. Test edge cases:
   - Partial state saves
   - Corrupted state files
   - Missing state components

This implementation leverages the existing `StorageManager` from the V4CB implementation while adapting it to the more complex state requirements of the draft system. The plan maintains compatibility with the existing draft logic while adding the necessary persistence layer.

The most challenging aspects will be:
1. Properly serializing/deserializing complex objects (CardData, DraftBot)
2. Maintaining player references across bot restarts
3. Ensuring state consistency during saves
