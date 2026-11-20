"""Playable Aethelgard Commanders and their Commander's Mandates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class CommanderDefinition:
    id: str
    name: str
    title: str
    portrait_filename: str
    base_health: int
    starting_armor: int
    mandate_name: str
    mandate_cost: int
    is_passive: bool
    mandate_description: str
    preferred_tribes: tuple[str, ...]


COMMANDER_CATALOG: Final[dict[str, CommanderDefinition]] = {
    "rowan": CommanderDefinition(
        id="rowan",
        name="Captain Rowan",
        title="Sunwarden Vanguard",
        portrait_filename="rowan.png",
        base_health=30,
        starting_armor=10,
        mandate_name="Solar Bulwark",
        mandate_cost=1,
        is_passive=False,
        mandate_description="1 Crown: Give a friendly unit +1/+2 and Vanguard.",
        preferred_tribes=("mercenary", "forge"),
    ),
    "rachel": CommanderDefinition(
        id="rachel",
        name="Rachel",
        title="Witch of the Orchid",
        portrait_filename="rachel.png",
        base_health=30,
        starting_armor=8,
        mandate_name="Violet Ember",
        mandate_cost=1,
        is_passive=False,
        mandate_description="1 Crown: Add a random Arcane Edict to hand and give a friendly unit +1/+1.",
        preferred_tribes=("cult", "crimson"),
    ),
    "lyra": CommanderDefinition(
        id="lyra",
        name="Lyra",
        title="Briar Botanist",
        portrait_filename="lyra.png",
        base_health=30,
        starting_armor=12,
        mandate_name="Root Symbiosis",
        mandate_cost=1,
        is_passive=False,
        mandate_description="1 Crown: Give a friendly unit +2/+2 (Sylvan units gain +3/+3).",
        preferred_tribes=("sylvan", "mercenary"),
    ),
    "caelen": CommanderDefinition(
        id="caelen",
        name="Caelen",
        title="Shadow Scout",
        portrait_filename="caelen.png",
        base_health=30,
        starting_armor=9,
        mandate_name="Ambush Ledger",
        mandate_cost=1,
        is_passive=False,
        mandate_description="1 Crown: Give a friendly unit +3 Attack and Shroud.",
        preferred_tribes=("astral", "crimson"),
    ),
    "melissa": CommanderDefinition(
        id="melissa",
        name="Melissa",
        title="Weave Archmage",
        portrait_filename="melissa.png",
        base_health=30,
        starting_armor=7,
        mandate_name="Astral Resonance",
        mandate_cost=0,
        is_passive=True,
        mandate_description="Passive: Your first Conclave Refresh each round costs 0 Crowns.",
        preferred_tribes=("astral", "cult"),
    ),
    "valora": CommanderDefinition(
        id="valora",
        name="Sister Valora",
        title="Solar Inquisitor",
        portrait_filename="valora.png",
        base_health=30,
        starting_armor=6,
        mandate_name="Judgment Aegis",
        mandate_cost=2,
        is_passive=False,
        mandate_description="2 Crowns: Grant a friendly unit Aegis and +2 Attack.",
        preferred_tribes=("forge", "cult"),
    ),
    "carmilla": CommanderDefinition(
        id="carmilla",
        name="High Lord Carmilla",
        title="Sanguine Matriarch",
        portrait_filename="carmilla.png",
        base_health=30,
        starting_armor=11,
        mandate_name="Sanguine Tithe",
        mandate_cost=0,
        is_passive=False,
        mandate_description="0 Crowns (Pay 1 Health): Gain 1 Aether Crown and 2 Blood Shards.",
        preferred_tribes=("crimson", "drowned"),
    ),
    "ironforge": CommanderDefinition(
        id="ironforge",
        name="The Ironforge Tyrant",
        title="Master of the Molten Vault",
        portrait_filename="ironforge.png",
        base_health=30,
        starting_armor=14,
        mandate_name="Master Forging",
        mandate_cost=0,
        is_passive=True,
        mandate_description="Passive: Every 2 rounds, add a Forge Plating (+2/+2 and Aegis) to your hand.",
        preferred_tribes=("forge", "drowned"),
    ),
}
