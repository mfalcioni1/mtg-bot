from typing import Dict, List, Optional
import discord
from dataclasses import dataclass
from cube_parser import CardData

@dataclass
class PackState:
    available_cards: List[CardData]
    picked_cards: Dict[str, List[CardData]]  # player_name -> list of cards picked from this pack
    pack_number: int
    pack_opener: str  # Name of player who opened this pack
    current_player: str
    player_pack_number: int  # Which pack number this is for the opener (1-3 typically)

class PackDisplay:
    def __init__(self):
        self.active_messages: Dict[int, Dict[int, discord.Message]] = {}  # guild_id -> {pack_number -> message}
        
    async def create_or_update_pack_display(
        self,
        channel: discord.TextChannel,
        pack_state: PackState,
        guild_id: int
    ) -> discord.Message:
        """Create or update the pack display message"""
        # Create title showing overall pack number and which pack this is for the opener
        embed = discord.Embed(
            title=f"Pack {pack_state.pack_number} (Pack {pack_state.player_pack_number} for {pack_state.pack_opener})",
            description=f"Current player: {pack_state.current_player}",
            color=discord.Color.blue()
        )

        # Available cards section
        available_cards = "\n".join([
            f"{idx + 1}. {card.name} ({card.type}) - {card.color_category.upper()}"
            for idx, card in enumerate(pack_state.available_cards)
        ])
        embed.add_field(
            name="Available Cards",
            value=available_cards if available_cards else "No cards available",
            inline=False
        )

        # Show all picks for this pack in order
        if pack_state.picked_cards:
            all_picks = []
            for player, cards in pack_state.picked_cards.items():
                for card in cards:
                    all_picks.append(f"{player}: {card.name}")
            
            picks_text = "\n".join(all_picks)
            embed.add_field(
                name="Picks This Pack (In Order)",
                value=picks_text,
                inline=False
            )

        # Initialize guild's message tracking if needed
        if guild_id not in self.active_messages:
            self.active_messages[guild_id] = {}

        # If we don't have a message for this pack number, create one
        if pack_state.pack_number not in self.active_messages[guild_id]:
            message = await channel.send(embed=embed)
            self.active_messages[guild_id][pack_state.pack_number] = message
            return message
        else:
            # Update existing message for this pack
            try:
                message = self.active_messages[guild_id][pack_state.pack_number]
                await message.edit(embed=embed)
                return message
            except discord.NotFound:
                # If message was deleted, create new one
                message = await channel.send(embed=embed)
                self.active_messages[guild_id][pack_state.pack_number] = message
                return message

    def get_active_message(self, guild_id: int, pack_number: int) -> Optional[discord.Message]:
        """Get the active pack display message for a specific pack in a guild"""
        return self.active_messages.get(guild_id, {}).get(pack_number)

    async def clear_display(self, guild_id: int):
        """Clear all pack displays for a guild"""
        if guild_id in self.active_messages:
            for message in self.active_messages[guild_id].values():
                try:
                    await message.delete()
                except discord.NotFound:
                    pass
            del self.active_messages[guild_id] 