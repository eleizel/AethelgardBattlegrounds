"""Warband board and hand management including Ascension triples."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.core.enums import HandCardKind
from src.data.units import UNIT_CATALOG
from src.entities.unit import HandCard, UnitInstance

MAX_WARBAND_SIZE = 7
MAX_HAND_SIZE = 10


@dataclass
class Warband:
    """Commander's active 7-slot warband and 10-slot hand."""

    board: list[UnitInstance] = field(default_factory=list)
    hand: list[HandCard] = field(default_factory=list)

    @property
    def is_board_full(self) -> bool:
        return len(self.board) >= MAX_WARBAND_SIZE

    @property
    def is_hand_full(self) -> bool:
        return len(self.hand) >= MAX_HAND_SIZE

    def add_card_to_hand(self, card: HandCard) -> bool:
        if self.is_hand_full:
            return False
        self.hand.append(card)
        return True

    def get_board_unit(self, instance_id: str) -> UnitInstance | None:
        for unit in self.board:
            if unit.instance_id == instance_id:
                return unit
        return None

    def swap_positions(self, index_a: int, index_b: int) -> bool:
        if (
            index_a < 0
            or index_b < 0
            or index_a >= len(self.board)
            or index_b >= len(self.board)
            or index_a == index_b
        ):
            return False
        self.board[index_a], self.board[index_b] = self.board[index_b], self.board[index_a]
        return True

    def move_unit(self, from_index: int, to_index: int) -> bool:
        if (
            from_index < 0
            or to_index < 0
            or from_index >= len(self.board)
            or to_index >= len(self.board)
            or from_index == to_index
        ):
            return False
        unit = self.board.pop(from_index)
        self.board.insert(to_index, unit)
        return True

    def count_non_ascended(self, unit_id: str) -> int:
        board_count = sum(
            1 for u in self.board if u.unit_id == unit_id and not u.is_ascended
        )
        hand_count = sum(
            1
            for c in self.hand
            if c.kind == HandCardKind.UNIT
            and c.unit is not None
            and c.unit.unit_id == unit_id
            and not c.unit.is_ascended
        )
        return board_count + hand_count

    def check_and_fuse_ascension(
        self,
        unit_id: str,
        *,
        new_instance_id: str,
        oracle_card_id: str,
        current_bastion_tier: int,
    ) -> UnitInstance | None:
        """If 3 non-ascended copies exist across board+hand, fuse them into an Ascended copy."""
        board_matches = [
            (idx, u)
            for idx, u in enumerate(self.board)
            if u.unit_id == unit_id and not u.is_ascended
        ]
        hand_matches = [
            (idx, c)
            for idx, c in enumerate(self.hand)
            if c.kind == HandCardKind.UNIT
            and c.unit is not None
            and c.unit.unit_id == unit_id
            and not c.unit.is_ascended
        ]
        total = len(board_matches) + len(hand_matches)
        if total < 3:
            return None

        # Collect exactly 3 copies (prioritize board copies first so bonuses carry over)
        chosen: list[UnitInstance] = []
        board_indices_to_remove: list[int] = []
        hand_indices_to_remove: list[int] = []

        for idx, u in board_matches:
            if len(chosen) < 3:
                chosen.append(u)
                board_indices_to_remove.append(idx)
        for idx, c in hand_matches:
            if len(chosen) < 3 and c.unit is not None:
                chosen.append(c.unit)
                hand_indices_to_remove.append(idx)

        defn = UNIT_CATALOG[unit_id]
        # Sum extra buffs gained above base stats from all 3 copies onto the 2x Ascended base
        bonus_atk = sum(max(0, u.attack - defn.base_attack) for u in chosen)
        bonus_hp = sum(max(0, u.max_health - defn.base_health) for u in chosen)
        merged_keywords = set(defn.keywords)
        for u in chosen:
            merged_keywords |= u.keywords

        ascended = UnitInstance.from_definition(
            defn, new_instance_id, is_ascended=True
        )
        ascended.attack += bonus_atk
        ascended.health += bonus_hp
        ascended.max_health += bonus_hp
        ascended.keywords |= merged_keywords

        # Remove fused copies in reverse index order
        for idx in sorted(board_indices_to_remove, reverse=True):
            self.board.pop(idx)
        for idx in sorted(hand_indices_to_remove, reverse=True):
            self.hand.pop(idx)

        # Put Ascended unit in hand (classic BG behavior so player triggers Ascended Vow
        # and chooses placement; if hand was somehow full, place directly on board).
        oracle_tier = min(6, current_bastion_tier + 1)
        ascended_card = HandCard(
            card_id=f"card_{new_instance_id}",
            kind=HandCardKind.UNIT,
            title=ascended.name,
            unit=ascended,
        )
        if not self.is_hand_full:
            self.hand.append(ascended_card)
        elif not self.is_board_full:
            self.board.append(ascended)

        # Add Ascension Oracle (Discover 1 of 3 from next Bastion Tier)
        oracle_card = HandCard(
            card_id=oracle_card_id,
            kind=HandCardKind.ASCENSION_ORACLE,
            title=f"Ascension Oracle (Tier {oracle_tier})",
            discover_tier=oracle_tier,
        )
        self.add_card_to_hand(oracle_card)
        return ascended
