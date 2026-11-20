"""Runtime unit instance and hand card models."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.core.enums import HandCardKind, Keyword
from src.data.units import UNIT_CATALOG, UnitDefinition


@dataclass
class UnitInstance:
    """Mutable instance of a unit on the warband, in hand, or in the Conclave offer."""

    instance_id: str
    unit_id: str
    name: str
    tribe: str
    tier: int
    attack: int
    health: int
    max_health: int
    keywords: set[Keyword] = field(default_factory=set)
    is_ascended: bool = False
    is_token: bool = False
    # Per-combat transient flags
    blight_used: bool = False
    undying_used: bool = False
    shroud_broken: bool = False
    retribution_counter: int = 0

    @classmethod
    def from_definition(
        cls,
        defn: UnitDefinition,
        instance_id: str,
        *,
        is_ascended: bool = False,
    ) -> UnitInstance:
        mult = 2 if is_ascended else 1
        atk = defn.base_attack * mult
        hp = defn.base_health * mult
        return cls(
            instance_id=instance_id,
            unit_id=defn.id,
            name=f"Ascended {defn.name}" if is_ascended else defn.name,
            tribe=defn.tribe,
            tier=defn.tier,
            attack=atk,
            health=hp,
            max_health=hp,
            keywords=set(defn.keywords),
            is_ascended=is_ascended,
            is_token=defn.is_token,
        )

    @property
    def definition(self) -> UnitDefinition:
        return UNIT_CATALOG[self.unit_id]

    @property
    def effect_multiplier(self) -> int:
        return 2 if self.is_ascended else 1

    @property
    def is_alive(self) -> bool:
        return self.health > 0

    def has_keyword(self, kw: Keyword) -> bool:
        if kw == Keyword.SHROUD and self.shroud_broken:
            return False
        return kw in self.keywords

    def add_keyword(self, kw: Keyword) -> None:
        self.keywords.add(kw)
        if kw == Keyword.SHROUD:
            self.shroud_broken = False

    def apply_buff(self, attack_delta: int, health_delta: int) -> None:
        self.attack = max(0, self.attack + attack_delta)
        self.health = max(1, self.health + health_delta)
        self.max_health = max(1, self.max_health + health_delta)

    def clone_for_combat(self, suffix: str = "") -> UnitInstance:
        """Deep copy for deterministic combat resolution without mutating recruitment stats."""
        return UnitInstance(
            instance_id=f"{self.instance_id}{suffix}",
            unit_id=self.unit_id,
            name=self.name,
            tribe=self.tribe,
            tier=self.tier,
            attack=self.attack,
            health=self.max_health,
            max_health=self.max_health,
            keywords=set(self.keywords),
            is_ascended=self.is_ascended,
            is_token=self.is_token,
            blight_used=False,
            undying_used=False,
            shroud_broken=False,
            retribution_counter=0,
        )


@dataclass
class HandCard:
    """Card held in a Commander's hand before being played."""

    card_id: str
    kind: HandCardKind
    title: str
    unit: UnitInstance | None = None
    edict_id: str | None = None
    discover_tier: int = 1
