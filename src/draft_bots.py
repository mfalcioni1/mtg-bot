import random
from typing import List, Optional
from cube_parser import CardData

class DraftBot:
    """Base class for draft bots"""
    def __init__(self, name: str):
        self.name = name
        self.picked_cards: List[CardData] = []
    
    def make_pick(self, pack: List[CardData]) -> Optional[CardData]:
        """Make a pick from the current pack"""
        raise NotImplementedError("Base DraftBot cannot make picks")

class RandomBot(DraftBot):
    """Bot that makes completely random picks"""
    def make_pick(self, pack: List[CardData]) -> Optional[CardData]:
        if not pack:
            return None
        return random.choice(pack)

def create_bot(bot_type: str = "random", name: str = None) -> DraftBot:
    """Factory function to create different types of draft bots"""
    if name is None:
        name = f"Bot_{random.randint(1000, 9999)}"
    
    if bot_type.lower() == "random":
        return RandomBot(name)
    else:
        raise ValueError(f"Unknown bot type: {bot_type}") 