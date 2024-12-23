from typing import Dict, List, Optional
import discord
from dataclasses import dataclass
from cube_parser import CardData

@dataclass
class PackState:
    available_cards: List[CardData]
    picked_cards: Dict[str, CardData]  # player_name -> card
    pack_number: int
    pick_number: int
    current_player: str

class PackDisplay:
    def __init__(self):
        self.active_messages: Dict[int, discord.Message] = {}  # guild_id -> message
        
    async def create_or_update_pack_display(
        self,
        channel: discord.TextChannel,
        pack_state: PackState,
        guild_id: int
    ) -> discord.Message:
        """Create or update the pack display message"""
        embed = discord.Embed(
            title=f"Pack {pack_state.pack_number + 1}, Pick {pack_state.pick_number}",
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

        # Picked cards section
        if pack_state.picked_cards:
            picked_cards = "\n".join([
                f"{player}: {card.name}"
                for player, card in pack_state.picked_cards.items()
            ])
            embed.add_field(
                name="Picked Cards",
                value=picked_cards,
                inline=False
            )

        # Create new message or update existing one
        if guild_id in self.active_messages:
            try:
                message = self.active_messages[guild_id]
                await message.edit(embed=embed)
                return message
            except discord.NotFound:
                # Message was deleted, create new one
                self.active_messages[guild_id] = await channel.send(embed=embed)
                return self.active_messages[guild_id]
        else:
            self.active_messages[guild_id] = await channel.send(embed=embed)
            return self.active_messages[guild_id]

    def get_active_message(self, guild_id: int) -> Optional[discord.Message]:
        """Get the active pack display message for a guild"""
        return self.active_messages.get(guild_id)

    async def clear_display(self, guild_id: int):
        """Clear the pack display for a guild"""
        if guild_id in self.active_messages:
            try:
                await self.active_messages[guild_id].delete()
            except discord.NotFound:
                pass
            finally:
                del self.active_messages[guild_id] 