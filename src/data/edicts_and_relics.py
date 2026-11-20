"""Catalog of Arcane Edicts (Tavern Spells) and Dawn Relics (Trinkets)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class ArcaneEdictDefinition:
    id: str
    name: str
    tier: int
    crown_cost: int
    description: str
    effect_kind: str
    attack_delta: int = 0
    health_delta: int = 0
    crowns_delta: int = 0
    count: int = 1


@dataclass(frozen=True)
class DawnRelicDefinition:
    id: str
    name: str
    tier_kind: str  # "LESSER" (Round 6) or "GREATER" (Round 9)
    description: str
    effect_kind: str
    attack_delta: int = 0
    health_delta: int = 0
    crowns_per_round: int = 0


ARCANE_EDICTS: Final[dict[str, ArcaneEdictDefinition]] = {
    "oakhaven_ration": ArcaneEdictDefinition(
        id="oakhaven_ration",
        name="Oakhaven Ration",
        tier=1,
        crown_cost=1,
        description="Give a random friendly unit +2/+2.",
        effect_kind="buff_random_ally",
        attack_delta=2,
        health_delta=2,
    ),
    "crimson_draught": ArcaneEdictDefinition(
        id="crimson_draught",
        name="Crimson Draught",
        tier=1,
        crown_cost=1,
        description="Add 2 Blood Shards (+1/+1) to your hand.",
        effect_kind="add_blood_shards",
        count=2,
    ),
    "crown_minting": ArcaneEdictDefinition(
        id="crown_minting",
        name="Crown Minting",
        tier=2,
        crown_cost=2,
        description="Gain +1 Max Aether Crown for the rest of the match.",
        effect_kind="increase_max_crowns",
        crowns_delta=1,
    ),
    "stoneward_chant": ArcaneEdictDefinition(
        id="stoneward_chant",
        name="Stoneward Chant",
        tier=2,
        crown_cost=2,
        description="Give a random friendly unit +1/+4 and Vanguard.",
        effect_kind="buff_vanguard",
        attack_delta=1,
        health_delta=4,
    ),
    "bastion_bounty": ArcaneEdictDefinition(
        id="bastion_bounty",
        name="Bastion Bounty",
        tier=3,
        crown_cost=2,
        description="Recruit a random unit from your current Bastion Tier to hand.",
        effect_kind="recruit_random_tier",
    ),
    "sunfire_tempering": ArcaneEdictDefinition(
        id="sunfire_tempering",
        name="Sunfire Tempering",
        tier=3,
        crown_cost=3,
        description="Give all friendly units +2/+1.",
        effect_kind="buff_all_allies",
        attack_delta=2,
        health_delta=1,
    ),
    "solaris_aegis": ArcaneEdictDefinition(
        id="solaris_aegis",
        name="Solaris Aegis",
        tier=4,
        crown_cost=3,
        description="Grant Aegis and +2/+2 to a random friendly unit without Aegis.",
        effect_kind="grant_aegis",
        attack_delta=2,
        health_delta=2,
    ),
    "echoes_of_ossuary": ArcaneEdictDefinition(
        id="echoes_of_ossuary",
        name="Echoes of the Ossuary",
        tier=4,
        crown_cost=3,
        description="Grant Undying to a random friendly unit without Undying.",
        effect_kind="grant_undying",
    ),
    "astral_conjunction": ArcaneEdictDefinition(
        id="astral_conjunction",
        name="Astral Conjunction",
        tier=5,
        crown_cost=3,
        description="Give all units in the Conclave +3/+3 and refresh free once.",
        effect_kind="buff_shop",
        attack_delta=3,
        health_delta=3,
    ),
    "blood_tithe_ritual": ArcaneEdictDefinition(
        id="blood_tithe_ritual",
        name="Blood Tithe Ritual",
        tier=5,
        crown_cost=2,
        description="Gain 3 Aether Crowns and add 2 Blood Shards to your hand.",
        effect_kind="crowns_and_shards",
        crowns_delta=3,
        count=2,
    ),
    "elder_coronation": ArcaneEdictDefinition(
        id="elder_coronation",
        name="Elder Coronation",
        tier=6,
        crown_cost=4,
        description="Give all friendly units +4/+4.",
        effect_kind="buff_all_allies",
        attack_delta=4,
        health_delta=4,
    ),
    "sovereign_ascension_rite": ArcaneEdictDefinition(
        id="sovereign_ascension_rite",
        name="Sovereign Ascension Rite",
        tier=6,
        crown_cost=5,
        description="Add an Ascension Oracle (Discover Tier VI/next tier) to your hand.",
        effect_kind="add_oracle",
    ),
}


DAWN_RELICS: Final[dict[str, DawnRelicDefinition]] = {
    # Lesser Dawn Relics (Round 6)
    "briar_crown_band": DawnRelicDefinition(
        id="briar_crown_band",
        name="Briar Crown Band",
        tier_kind="LESSER",
        description="Start each Combat: Give all friendly units +2/+2.",
        effect_kind="combat_start_buff_all",
        attack_delta=2,
        health_delta=2,
    ),
    "sunwarden_banner": DawnRelicDefinition(
        id="sunwarden_banner",
        name="Sunwarden Banner",
        tier_kind="LESSER",
        description="Start each Combat: Grant Aegis to your leftmost unit.",
        effect_kind="combat_start_leftmost_aegis",
    ),
    "oakhaven_purse": DawnRelicDefinition(
        id="oakhaven_purse",
        name="Oakhaven Merchant Purse",
        tier_kind="LESSER",
        description="Start each Recruitment Round with +2 bonus Aether Crowns.",
        effect_kind="round_start_crowns",
        crowns_per_round=2,
    ),
    "crimson_chalice": DawnRelicDefinition(
        id="crimson_chalice",
        name="Crimson Chalice",
        tier_kind="LESSER",
        description="Start each Recruitment Round: Add 2 Blood Shards (+1/+1) to hand.",
        effect_kind="round_start_shards",
    ),
    "ossuary_lantern": DawnRelicDefinition(
        id="ossuary_lantern",
        name="Ossuary Lantern",
        tier_kind="LESSER",
        description="Whenever you summon a unit in combat, give it +2/+1.",
        effect_kind="combat_summon_buff",
        attack_delta=2,
        health_delta=1,
    ),
    "astral_astrolabe": DawnRelicDefinition(
        id="astral_astrolabe",
        name="Astral Astrolabe",
        tier_kind="LESSER",
        description="Whenever you Refresh the Conclave, give Conclave units +1/+1.",
        effect_kind="refresh_buff_shop",
        attack_delta=1,
        health_delta=1,
    ),
    # Greater Dawn Relics (Round 9)
    "solar_heartstone": DawnRelicDefinition(
        id="solar_heartstone",
        name="Solar Heartstone",
        tier_kind="GREATER",
        description="Start each Combat: Double the Attack of your leftmost unit (capped +30) & +0/+6.",
        effect_kind="combat_start_leftmost_surge",
        attack_delta=6,
        health_delta=6,
    ),
    "aether_sovereign_seal": DawnRelicDefinition(
        id="aether_sovereign_seal",
        name="Aether Sovereign Seal",
        tier_kind="GREATER",
        description="Your Max Aether Crowns becomes 13 and you gain +3 bonus Crowns each round.",
        effect_kind="sovereign_economy",
        crowns_per_round=3,
    ),
    "elder_root_effigy": DawnRelicDefinition(
        id="elder_root_effigy",
        name="Elder Root Effigy",
        tier_kind="GREATER",
        description="Start each Combat: Give all friendly units +5/+6.",
        effect_kind="combat_start_buff_all",
        attack_delta=5,
        health_delta=6,
    ),
    "sanctum_reliquary": DawnRelicDefinition(
        id="sanctum_reliquary",
        name="Sanctum Reliquary",
        tier_kind="GREATER",
        description="End of each Recruitment Round: Permanently give all warband units +2/+2.",
        effect_kind="round_end_buff_all",
        attack_delta=2,
        health_delta=2,
    ),
    "molten_anvil_core": DawnRelicDefinition(
        id="molten_anvil_core",
        name="Molten Anvil Core",
        tier_kind="GREATER",
        description="Start each Combat: Grant Aegis and +3/+0 to your two leftmost units.",
        effect_kind="combat_start_two_aegis",
        attack_delta=3,
        health_delta=0,
    ),
    "eternal_echo_bell": DawnRelicDefinition(
        id="eternal_echo_bell",
        name="Eternal Echo Bell",
        tier_kind="GREATER",
        description="Start each Combat: Give all friendly Last Echo and Undying units +4/+4.",
        effect_kind="combat_start_death_buff",
        attack_delta=4,
        health_delta=4,
    ),
}
