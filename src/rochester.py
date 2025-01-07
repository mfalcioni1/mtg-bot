import random

class RochesterDraft:
    def __init__(self, players: list[str], cards_per_pack: int, num_packs: int):
        self.players = players
        self.cards_per_pack = cards_per_pack
        self.num_packs = num_packs
        self.player_order = self.set_player_order()
        self.pick_order = self.set_pick_order(self.player_order)
        self.pack_pick = 1
        self.pick_number = 1
        self.pack_number = 1
        self.total_picks = self.cards_per_pack * self.num_packs * len(self.players)

    def advance_pick(self) -> None:
        self.pick_number += 1
        self.pack_pick += 1

    def set_player_order(self) -> list[str]:
        return random.sample(self.players, len(self.players))

    def set_pick_order(self, drafters: list[str]) -> dict[str, int]:
        pick_order = {}

        i = 1
        while i < self.cards_per_pack + 1:
            for player in drafters:
                pick_order[i] = player
                i += 1
            drafters.reverse()
        return pick_order

    def update_player_order(self, input_order: list[str]) -> list[str]:
        to_last = input_order.pop(0)
        input_order.append(to_last)
        return input_order

    def get_current_player(self) -> str:
        return self.pick_order[self.pack_pick]
    
    def run_draft(self) -> None:
        while self.pick_number <= self.total_picks:
            print(f"Pack {self.pack_number} player order: {self.player_order}")
            print(f"Pack {self.pack_number} pick order: {self.pick_order}")
            while self.pack_pick <= self.cards_per_pack:
                current_player = self.get_current_player()
                ## TODO: This is where the picking logic will go that manages player picks and the pack.
                self.advance_pick()
            print(f"Pack {self.pack_number} complete.")
            self.pack_number += 1
            self.pack_pick = 1
            self.player_order = self.update_player_order(self.player_order)
            self.pick_order = self.set_pick_order(self.player_order)
        print("Draft complete.")

if __name__ == "__main__":
    players = ["A", "B", "C"]
    cards_per_pack = 6
    num_packs = 3
    draft = RochesterDraft(players, cards_per_pack, num_packs)
    draft.run_draft()
