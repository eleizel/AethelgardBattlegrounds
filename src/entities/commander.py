"""Commander state, economy, Bastion tier progression, and relic tracking."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.data.commanders import COMMANDER_CATALOG, CommanderDefinition
from src.entities.unit import UnitInstance
from src.entities.warband import Warband

BASTION_UPGRADE_BASE_COST: dict[int, int] = {
    1: 5,
    2: 7,
    3: 8,
    4: 9,
    5: 10,
}

# Number of unit slots offered in the Conclave by Bastion Tier
CONCLAVE_SHOP_SLOTS: dict[int, int] = {
    1: 3,
    2: 4,
    3: 4,
    4: 5,
    5: 5,
    6: 6,
}


@dataclass
class CommanderState:
    """Full mutable state for one of the 8 Commanders in a War Conclave lobby."""

    slot_index: int
    commander_id: str
    name: str
    title: str
    portrait_filename: str
    health: int
    armor: int
    max_health: int
    is_human: bool = False
    bastion_tier: int = 1
    upgrade_cost: int = 5
    crowns: int = 3
    max_crowns: int = 3
    bonus_max_crowns: int = 0
    crowns_cap: int = 10
    warband: Warband = field(default_factory=Warband)
    shop_units: list[UnitInstance] = field(default_factory=list)
    shop_edict_id: str | None = None
    shop_edict_cost_override: int | None = None
    shop_frozen: bool = False
    free_refreshes: int = 0
    mandate_used_this_round: bool = False
    relics: list[str] = field(default_factory=list)
    pending_oracle_choices: list[UnitInstance] = field(default_factory=list)
    pending_relic_choices: list[str] = field(default_factory=list)
    eliminated: bool = False
    placement: int = 0
    win_streak: int = 0
    wins: int = 0
    losses: int = 0
    ties: int = 0
    last_opponent_slot: int | None = None
    last_damage_taken: int = 0
    last_damage_dealt: int = 0

    @classmethod
    def from_definition(
        cls,
        slot_index: int,
        defn: CommanderDefinition,
        *,
        is_human: bool = False,
    ) -> CommanderState:
        return cls(
            slot_index=slot_index,
            commander_id=defn.id,
            name=defn.name,
            title=defn.title,
            portrait_filename=defn.portrait_filename,
            health=defn.base_health,
            armor=defn.starting_armor,
            max_health=defn.base_health,
            is_human=is_human,
        )

    @property
    def definition(self) -> CommanderDefinition:
        return COMMANDER_CATALOG[self.commander_id]

    @property
    def total_vitality(self) -> int:
        return self.health + self.armor

    @property
    def is_alive(self) -> bool:
        return not self.eliminated and self.health > 0

    def has_relic(self, relic_id: str) -> bool:
        return relic_id in self.relics

    def apply_damage(self, amount: int) -> int:
        """Apply damage to Armor first, then Health. Returns actual damage dealt."""
        if amount <= 0 or self.eliminated:
            return 0
        remaining = amount
        if self.armor > 0:
            absorbed = min(self.armor, remaining)
            self.armor -= absorbed
            remaining -= absorbed
        if remaining > 0:
            self.health = max(0, self.health - remaining)
        self.last_damage_taken = amount
        if self.health <= 0:
            self.eliminated = True
        return amount

    def begin_recruitment_round(self, round_number: int) -> None:
        """Advance economy, Bastion tier cost decay, and passive Commander hooks."""
        if self.eliminated:
            return
        cap = 13 if self.has_relic("aether_sovereign_seal") else self.crowns_cap
        base_round_crowns = min(10, 2 + round_number)
        self.max_crowns = min(cap, base_round_crowns + self.bonus_max_crowns)

        bonus = 0
        if self.has_relic("oakhaven_purse"):
            bonus += 2
        if self.has_relic("aether_sovereign_seal"):
            bonus += 3
        self.crowns = self.max_crowns + bonus

        if self.bastion_tier < 6 and self.upgrade_cost > 0:
            self.upgrade_cost = max(0, self.upgrade_cost - 1)

        self.mandate_used_this_round = False
        self.free_refreshes = 1 if self.commander_id == "melissa" else 0
