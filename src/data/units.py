"""Catalog of all 48+ recruitable units and summoned tokens across Bastion Tiers I-VI."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

from src.core.enums import Keyword


@dataclass(frozen=True)
class UnitEffectSpec:
    """Declarative trigger effect attached to Vow, Last Echo, Retribution, or Shop hooks."""

    kind: str
    attack_delta: int = 0
    health_delta: int = 0
    damage: int = 0
    count: int = 1
    token_id: str | None = None
    grant_keyword: Keyword | None = None
    target_tribe: str | None = None
    retribution_threshold: int = 0


@dataclass(frozen=True)
class UnitDefinition:
    """Immutable blueprint for a recruitable unit or summoned token."""

    id: str
    name: str
    tribe: str
    tier: int
    base_attack: int
    base_health: int
    sprite_filename: str
    description: str
    keywords: tuple[Keyword, ...] = ()
    vow: UnitEffectSpec | None = None
    last_echo: UnitEffectSpec | None = None
    retribution: UnitEffectSpec | None = None
    on_edict_cast: UnitEffectSpec | None = None
    on_shard_applied: UnitEffectSpec | None = None
    is_token: bool = False
    extra_tags: tuple[str, ...] = field(default_factory=tuple)


# Shared Bastion pool copy counts per Tier (mirrors classic autobattler scarcity)
TIER_POOL_COPIES: Final[dict[int, int]] = {
    1: 15,
    2: 15,
    3: 13,
    4: 11,
    5: 9,
    6: 7,
}


UNIT_CATALOG: Final[dict[str, UnitDefinition]] = {
    # =========================================================================
    # SYLVAN BLIGHT (The Wilted Arboretum)
    # =========================================================================
    "thornvein_creeper": UnitDefinition(
        id="thornvein_creeper",
        name="Thornvein Creeper",
        tribe="sylvan",
        tier=1,
        base_attack=2,
        base_health=2,
        sprite_filename="thornvein_creeper.png",
        description="Vow: Give a friendly Sylvan unit +1/+1.",
        keywords=(Keyword.VOW,),
        vow=UnitEffectSpec(
            kind="buff_random_ally", attack_delta=1, health_delta=1, target_tribe="sylvan"
        ),
    ),
    "spore_pod": UnitDefinition(
        id="spore_pod",
        name="Spore-Spitting Pod",
        tribe="sylvan",
        tier=1,
        base_attack=1,
        base_health=3,
        sprite_filename="spore_pod.png",
        description="Last Echo: Summon a 1/1 Briar Spore.",
        keywords=(Keyword.LAST_ECHO,),
        last_echo=UnitEffectSpec(kind="summon", count=1, token_id="briar_spore_token"),
    ),
    "bramble_hound": UnitDefinition(
        id="bramble_hound",
        name="Bramble Hound",
        tribe="sylvan",
        tier=2,
        base_attack=3,
        base_health=2,
        sprite_filename="bramble_hound.png",
        description="Frenzy: Attacks twice each combat turn.",
        keywords=(Keyword.FRENZY,),
    ),
    "rotting_woodwose": UnitDefinition(
        id="rotting_woodwose",
        name="Rotting Woodwose",
        tribe="sylvan",
        tier=3,
        base_attack=3,
        base_health=6,
        sprite_filename="rotting_woodwose.png",
        description="Vanguard. Retribution (2): Gain +1/+2 permanently.",
        keywords=(Keyword.VANGUARD, Keyword.RETRIBUTION),
        retribution=UnitEffectSpec(
            kind="buff_self", attack_delta=1, health_delta=2, retribution_threshold=2
        ),
    ),
    "mandragora_matron": UnitDefinition(
        id="mandragora_matron",
        name="Mandragora Matron",
        tribe="sylvan",
        tier=4,
        base_attack=4,
        base_health=5,
        sprite_filename="mandragora_matron.png",
        description="Blight: Destroys the first enemy damaged by its strike.",
        keywords=(Keyword.BLIGHT,),
    ),
    "corpse_treant": UnitDefinition(
        id="corpse_treant",
        name="Corpse-Root Treant",
        tribe="sylvan",
        tier=5,
        base_attack=6,
        base_health=8,
        sprite_filename="corpse_treant.png",
        description="Vanguard. Last Echo: Summon two 2/2 Briar Spores.",
        keywords=(Keyword.VANGUARD, Keyword.LAST_ECHO),
        last_echo=UnitEffectSpec(
            kind="summon", count=2, token_id="briar_spore_token", attack_delta=1, health_delta=1
        ),
    ),
    "verdant_abomination": UnitDefinition(
        id="verdant_abomination",
        name="Verdant Abomination",
        tribe="sylvan",
        tier=6,
        base_attack=8,
        base_health=10,
        sprite_filename="verdant_abomination.png",
        description="Blight. Last Echo: Give all friendly Sylvans +3/+4.",
        keywords=(Keyword.BLIGHT, Keyword.LAST_ECHO),
        last_echo=UnitEffectSpec(
            kind="buff_all_allies", attack_delta=3, health_delta=4, target_tribe="sylvan"
        ),
    ),
    # =========================================================================
    # DROWNED UNDEAD (The Drowned Ossuary)
    # =========================================================================
    "drowned_skulls": UnitDefinition(
        id="drowned_skulls",
        name="Drowned Skull-Cluster",
        tribe="drowned",
        tier=1,
        base_attack=2,
        base_health=1,
        sprite_filename="drowned_skulls.png",
        description="Undying: Revives once per combat with 1 Health.",
        keywords=(Keyword.UNDYING,),
    ),
    "mire_ghoul": UnitDefinition(
        id="mire_ghoul",
        name="Mire Ghoul",
        tribe="drowned",
        tier=1,
        base_attack=1,
        base_health=3,
        sprite_filename="mire_ghoul.png",
        description="Last Echo: Summon a 1/1 Risen Skull.",
        keywords=(Keyword.LAST_ECHO,),
        last_echo=UnitEffectSpec(kind="summon", count=1, token_id="risen_skull_token"),
    ),
    "leech_husk": UnitDefinition(
        id="leech_husk",
        name="Leech-Swarm Husk",
        tribe="drowned",
        tier=2,
        base_attack=3,
        base_health=3,
        sprite_filename="leech_husk.png",
        description="Retribution (2): Gain +1/+1 permanently.",
        keywords=(Keyword.RETRIBUTION,),
        retribution=UnitEffectSpec(
            kind="buff_self", attack_delta=1, health_delta=1, retribution_threshold=2
        ),
    ),
    "crypt_lurker": UnitDefinition(
        id="crypt_lurker",
        name="Crypt Lurker",
        tribe="drowned",
        tier=3,
        base_attack=4,
        base_health=3,
        sprite_filename="crypt_lurker.png",
        description="Undying, Shroud: Strikes unseen and rises again.",
        keywords=(Keyword.UNDYING, Keyword.SHROUD),
    ),
    "tide_gravekeeper": UnitDefinition(
        id="tide_gravekeeper",
        name="Tide-Risen Gravekeeper",
        tribe="drowned",
        tier=4,
        base_attack=4,
        base_health=6,
        sprite_filename="tide_gravekeeper.png",
        description="Vanguard. Retribution (3): Summon a 2/2 Risen Skull.",
        keywords=(Keyword.VANGUARD, Keyword.RETRIBUTION),
        retribution=UnitEffectSpec(
            kind="summon",
            count=1,
            token_id="risen_skull_token",
            attack_delta=1,
            health_delta=1,
            retribution_threshold=3,
        ),
    ),
    "carrion_behemoth": UnitDefinition(
        id="carrion_behemoth",
        name="Carrion Behemoth",
        tribe="drowned",
        tier=5,
        base_attack=7,
        base_health=8,
        sprite_filename="carrion_behemoth.png",
        description="Undying. Last Echo: Give all friendly Drowned +2/+2.",
        keywords=(Keyword.UNDYING, Keyword.LAST_ECHO),
        last_echo=UnitEffectSpec(
            kind="buff_all_allies", attack_delta=2, health_delta=2, target_tribe="drowned"
        ),
    ),
    "drowned_patriarch": UnitDefinition(
        id="drowned_patriarch",
        name="The Drowned Patriarch",
        tribe="drowned",
        tier=6,
        base_attack=8,
        base_health=9,
        sprite_filename="drowned_patriarch.png",
        description="Vanguard. Last Echo: Summon two 3/3 Risen Skulls.",
        keywords=(Keyword.VANGUARD, Keyword.LAST_ECHO),
        last_echo=UnitEffectSpec(
            kind="summon", count=2, token_id="risen_skull_token", attack_delta=2, health_delta=2
        ),
    ),
    # =========================================================================
    # INFERNAL FORGE (The Foundry of Torment)
    # =========================================================================
    "cinder_sprite": UnitDefinition(
        id="cinder_sprite",
        name="Cinder Sprite",
        tribe="forge",
        tier=1,
        base_attack=2,
        base_health=2,
        sprite_filename="cinder_sprite.png",
        description="Last Echo: Deal 2 damage to a random enemy.",
        keywords=(Keyword.LAST_ECHO,),
        last_echo=UnitEffectSpec(kind="damage_random_enemy", damage=2, count=1),
    ),
    "slag_homunculus": UnitDefinition(
        id="slag_homunculus",
        name="Slagforged Homunculus",
        tribe="forge",
        tier=1,
        base_attack=2,
        base_health=3,
        sprite_filename="slag_homunculus.png",
        description="Vanguard: Protects molten allies behind molten plating.",
        keywords=(Keyword.VANGUARD,),
    ),
    "clockwork_flayer": UnitDefinition(
        id="clockwork_flayer",
        name="Clockwork Flayer",
        tribe="forge",
        tier=2,
        base_attack=3,
        base_health=2,
        sprite_filename="clockwork_flayer.png",
        description="Aegis: Negates the first hit received in combat.",
        keywords=(Keyword.AEGIS,),
    ),
    "ashen_overseer": UnitDefinition(
        id="ashen_overseer",
        name="Ashen Overseer",
        tribe="forge",
        tier=3,
        base_attack=3,
        base_health=5,
        sprite_filename="ashen_overseer.png",
        description="Vow: Give a friendly Forge unit +2/+2 and Aegis.",
        keywords=(Keyword.VOW,),
        vow=UnitEffectSpec(
            kind="buff_random_ally",
            attack_delta=2,
            health_delta=2,
            grant_keyword=Keyword.AEGIS,
            target_tribe="forge",
        ),
    ),
    "inquisitor_automaton": UnitDefinition(
        id="inquisitor_automaton",
        name="Inquisitor Automaton",
        tribe="forge",
        tier=4,
        base_attack=5,
        base_health=4,
        sprite_filename="inquisitor_automaton.png",
        description="Aegis, Frenzy: Twin clockwork blades under an Aegis ward.",
        keywords=(Keyword.AEGIS, Keyword.FRENZY),
    ),
    "furnace_warden": UnitDefinition(
        id="furnace_warden",
        name="Furnace Warden",
        tribe="forge",
        tier=5,
        base_attack=5,
        base_health=9,
        sprite_filename="furnace_warden.png",
        description="Vanguard, Aegis. Retribution (2): Grant Aegis to a friendly Forge unit.",
        keywords=(Keyword.VANGUARD, Keyword.AEGIS, Keyword.RETRIBUTION),
        retribution=UnitEffectSpec(
            kind="grant_keyword_ally",
            grant_keyword=Keyword.AEGIS,
            target_tribe="forge",
            retribution_threshold=2,
        ),
    ),
    "ironforge_tyrant": UnitDefinition(
        id="ironforge_tyrant",
        name="The Ironforge Tyrant",
        tribe="forge",
        tier=6,
        base_attack=9,
        base_health=9,
        sprite_filename="ironforge_tyrant.png",
        description="Aegis, Sweep: Hammers primary and adjacent foes alike.",
        keywords=(Keyword.AEGIS, Keyword.SWEEP),
    ),
    # =========================================================================
    # CATHEDRAL CULT (The Desecrated Cathedral)
    # =========================================================================
    "cathedral_imp": UnitDefinition(
        id="cathedral_imp",
        name="Cathedral Imp",
        tribe="cult",
        tier=1,
        base_attack=2,
        base_health=1,
        sprite_filename="cathedral_imp.png",
        description="Vow: Deal 1 damage to your Commander and gain +2/+2.",
        keywords=(Keyword.VOW,),
        vow=UnitEffectSpec(kind="self_pact", attack_delta=2, health_delta=2, damage=1),
    ),
    "possessed_grimoire": UnitDefinition(
        id="possessed_grimoire",
        name="Possessed Grimoire",
        tribe="cult",
        tier=1,
        base_attack=1,
        base_health=3,
        sprite_filename="possessed_grimoire.png",
        description="Vow: Add a random Arcane Edict to your hand.",
        keywords=(Keyword.VOW,),
        vow=UnitEffectSpec(kind="add_edict", count=1),
    ),
    "candelabra_fiend": UnitDefinition(
        id="candelabra_fiend",
        name="Candelabra Fiend",
        tribe="cult",
        tier=2,
        base_attack=3,
        base_health=4,
        sprite_filename="candelabra_fiend.png",
        description="Vanguard. Gains +1/+2 whenever you cast an Arcane Edict.",
        keywords=(Keyword.VANGUARD,),
        on_edict_cast=UnitEffectSpec(kind="buff_self", attack_delta=1, health_delta=2),
    ),
    "penitent_zealot": UnitDefinition(
        id="penitent_zealot",
        name="Penitent Zealot",
        tribe="cult",
        tier=3,
        base_attack=4,
        base_health=4,
        sprite_filename="penitent_zealot.png",
        description="Retribution (2): Gain +2/+1 permanently.",
        keywords=(Keyword.RETRIBUTION,),
        retribution=UnitEffectSpec(
            kind="buff_self", attack_delta=2, health_delta=1, retribution_threshold=2
        ),
    ),
    "belltower_gargoyle": UnitDefinition(
        id="belltower_gargoyle",
        name="Belltower Gargoyle",
        tribe="cult",
        tier=4,
        base_attack=4,
        base_health=7,
        sprite_filename="belltower_gargoyle.png",
        description="Vanguard, Aegis: Granite sentinel guarding cathedral naves.",
        keywords=(Keyword.VANGUARD, Keyword.AEGIS),
    ),
    "chorus_of_damned": UnitDefinition(
        id="chorus_of_damned",
        name="Chorus of the Damned",
        tribe="cult",
        tier=5,
        base_attack=6,
        base_health=6,
        sprite_filename="chorus_of_damned.png",
        description="Last Echo: Deal 4 damage to all enemy units.",
        keywords=(Keyword.LAST_ECHO,),
        last_echo=UnitEffectSpec(kind="damage_all_enemies", damage=4),
    ),
    "blind_archbishop": UnitDefinition(
        id="blind_archbishop",
        name="The Blind Archbishop",
        tribe="cult",
        tier=6,
        base_attack=7,
        base_health=9,
        sprite_filename="blind_archbishop.png",
        description="Vow: Give all friendly Cult units +3/+3.",
        keywords=(Keyword.VOW,),
        vow=UnitEffectSpec(
            kind="buff_all_allies", attack_delta=3, health_delta=3, target_tribe="cult"
        ),
    ),
    # =========================================================================
    # CRIMSON COURT (The Blood Sanctum)
    # =========================================================================
    "sanguine_thrall": UnitDefinition(
        id="sanguine_thrall",
        name="Sanguine Thrall",
        tribe="crimson",
        tier=1,
        base_attack=2,
        base_health=2,
        sprite_filename="sanguine_thrall.png",
        description="Vow: Add 1 Blood Shard (+1/+1) to your hand.",
        keywords=(Keyword.VOW,),
        vow=UnitEffectSpec(kind="add_blood_shards", count=1),
    ),
    "crimson_gargoyle": UnitDefinition(
        id="crimson_gargoyle",
        name="Crimson Gargoyle",
        tribe="crimson",
        tier=1,
        base_attack=1,
        base_health=4,
        sprite_filename="crimson_gargoyle.png",
        description="Vanguard. Gains an extra +1 Attack when a Blood Shard is played on it.",
        keywords=(Keyword.VANGUARD,),
        on_shard_applied=UnitEffectSpec(kind="buff_self", attack_delta=1, health_delta=0),
    ),
    "hemomancer_acolyte": UnitDefinition(
        id="hemomancer_acolyte",
        name="Hemomancer Acolyte",
        tribe="crimson",
        tier=2,
        base_attack=3,
        base_health=2,
        sprite_filename="hemomancer_acolyte.png",
        description="Last Echo: Add 2 Blood Shards (+1/+1) to your hand.",
        keywords=(Keyword.LAST_ECHO,),
        last_echo=UnitEffectSpec(kind="add_blood_shards", count=2),
    ),
    "flayed_duelist": UnitDefinition(
        id="flayed_duelist",
        name="Flayed Duelist",
        tribe="crimson",
        tier=3,
        base_attack=4,
        base_health=3,
        sprite_filename="flayed_duelist.png",
        description="Frenzy: Strikes twice with crimson precision.",
        keywords=(Keyword.FRENZY,),
    ),
    "baroness_vespera": UnitDefinition(
        id="baroness_vespera",
        name="Baroness Vespera",
        tribe="crimson",
        tier=4,
        base_attack=5,
        base_health=5,
        sprite_filename="baroness_vespera.png",
        description="Frenzy, Shroud: Unseen until she unleashes twin slashes.",
        keywords=(Keyword.FRENZY, Keyword.SHROUD),
    ),
    "amalgam_of_veins": UnitDefinition(
        id="amalgam_of_veins",
        name="Amalgam of Veins",
        tribe="crimson",
        tier=5,
        base_attack=6,
        base_health=9,
        sprite_filename="amalgam_of_veins.png",
        description="Vanguard. Retribution (2): Give all friendly Crimson units +1/+1.",
        keywords=(Keyword.VANGUARD, Keyword.RETRIBUTION),
        retribution=UnitEffectSpec(
            kind="buff_all_allies",
            attack_delta=1,
            health_delta=1,
            target_tribe="crimson",
            retribution_threshold=2,
        ),
    ),
    "blood_god_avatar": UnitDefinition(
        id="blood_god_avatar",
        name="The Blood-God Avatar",
        tribe="crimson",
        tier=6,
        base_attack=9,
        base_health=8,
        sprite_filename="blood_god_avatar.png",
        description="Frenzy. Vow: Add 3 Blood Shards to hand and give all allies +2/+2.",
        keywords=(Keyword.FRENZY, Keyword.VOW),
        vow=UnitEffectSpec(kind="crimson_awakening", attack_delta=2, health_delta=2, count=3),
    ),
    # =========================================================================
    # ASTRAL VOID (The Astral Observatory)
    # =========================================================================
    "stareater_wisp": UnitDefinition(
        id="stareater_wisp",
        name="Star-Eater Wisp",
        tribe="astral",
        tier=1,
        base_attack=2,
        base_health=2,
        sprite_filename="stareater_wisp.png",
        description="Shroud: Cannot be attacked until it strikes first.",
        keywords=(Keyword.SHROUD,),
    ),
    "void_mirror": UnitDefinition(
        id="void_mirror",
        name="Void Mirror",
        tribe="astral",
        tier=1,
        base_attack=1,
        base_health=4,
        sprite_filename="void_mirror.png",
        description="Vanguard, Aegis: Refracts the opening blow in starlight.",
        keywords=(Keyword.VANGUARD, Keyword.AEGIS),
    ),
    "crystal_viper": UnitDefinition(
        id="crystal_viper",
        name="Crystal Viper",
        tribe="astral",
        tier=2,
        base_attack=3,
        base_health=2,
        sprite_filename="crystal_viper.png",
        description="Blight: Shatters the first enemy it damages.",
        keywords=(Keyword.BLIGHT,),
    ),
    "comet_stalker": UnitDefinition(
        id="comet_stalker",
        name="Comet Stalker",
        tribe="astral",
        tier=3,
        base_attack=4,
        base_health=3,
        sprite_filename="comet_stalker.png",
        description="Sweep: Also damages units adjacent to its target.",
        keywords=(Keyword.SWEEP,),
    ),
    "celestial_hermit": UnitDefinition(
        id="celestial_hermit",
        name="Celestial Hermit",
        tribe="astral",
        tier=4,
        base_attack=4,
        base_health=6,
        sprite_filename="celestial_hermit.png",
        description="Vow: Give all units currently in the Conclave +2/+2 and gain 1 free refresh.",
        keywords=(Keyword.VOW,),
        vow=UnitEffectSpec(kind="empower_conclave", attack_delta=2, health_delta=2, count=1),
    ),
    "rift_warden": UnitDefinition(
        id="rift_warden",
        name="Rift Warden",
        tribe="astral",
        tier=5,
        base_attack=6,
        base_health=5,
        sprite_filename="rift_warden.png",
        description="Sweep, Shroud: Cleaves enemy lines from dimensional shadow.",
        keywords=(Keyword.SWEEP, Keyword.SHROUD),
    ),
    "devouring_constellation": UnitDefinition(
        id="devouring_constellation",
        name="The Devouring Constellation",
        tribe="astral",
        tier=6,
        base_attack=8,
        base_health=8,
        sprite_filename="devouring_constellation.png",
        description="Sweep, Aegis: Starfire devastation shielded by cosmic glass.",
        keywords=(Keyword.SWEEP, Keyword.AEGIS),
    ),
    # =========================================================================
    # OAKHAVEN MERCENARIES (Neutral Cross-Tribe Support)
    # =========================================================================
    "oakhaven_watchman": UnitDefinition(
        id="oakhaven_watchman",
        name="Oakhaven Watchman",
        tribe="mercenary",
        tier=1,
        base_attack=2,
        base_health=3,
        sprite_filename="oakhaven_watchman.png",
        description="Vanguard: Steadfast guard of Oakhaven's timber palisades.",
        keywords=(Keyword.VANGUARD,),
    ),
    "briarwood_herbalist": UnitDefinition(
        id="briarwood_herbalist",
        name="Briarwood Herbalist",
        tribe="mercenary",
        tier=2,
        base_attack=2,
        base_health=4,
        sprite_filename="briarwood_herbalist.png",
        description="Vow: Give a friendly unit +2/+2.",
        keywords=(Keyword.VOW,),
        vow=UnitEffectSpec(kind="buff_random_ally", attack_delta=2, health_delta=2),
    ),
    "sunwarden_squire": UnitDefinition(
        id="sunwarden_squire",
        name="Sunwarden Squire",
        tribe="mercenary",
        tier=3,
        base_attack=4,
        base_health=4,
        sprite_filename="sunwarden_squire.png",
        description="Aegis: Anointed squire shielded by dawnlight.",
        keywords=(Keyword.AEGIS,),
    ),
    "weave_chronicler": UnitDefinition(
        id="weave_chronicler",
        name="Weave Chronicler",
        tribe="mercenary",
        tier=4,
        base_attack=4,
        base_health=5,
        sprite_filename="weave_chronicler.png",
        description="Vow: Add a random Arcane Edict to your hand.",
        keywords=(Keyword.VOW,),
        vow=UnitEffectSpec(kind="add_edict", count=1),
    ),
    "guild_quartermaster": UnitDefinition(
        id="guild_quartermaster",
        name="Guild Quartermaster",
        tribe="mercenary",
        tier=5,
        base_attack=5,
        base_health=6,
        sprite_filename="guild_quartermaster.png",
        description="Vow: Gain 2 Aether Crowns this round.",
        keywords=(Keyword.VOW,),
        vow=UnitEffectSpec(kind="gain_crowns", count=2),
    ),
    "elder_tomas": UnitDefinition(
        id="elder_tomas",
        name="Elder Tomas of Oakhaven",
        tribe="mercenary",
        tier=6,
        base_attack=7,
        base_health=7,
        sprite_filename="elder_tomas.png",
        description="Vow: Give one friendly unit of each tribe +3/+3.",
        keywords=(Keyword.VOW,),
        vow=UnitEffectSpec(kind="menagerie_buff", attack_delta=3, health_delta=3),
    ),
    # =========================================================================
    # SUMMONED TOKENS (Not in Conclave shop pool)
    # =========================================================================
    "briar_spore_token": UnitDefinition(
        id="briar_spore_token",
        name="Briar Spore",
        tribe="sylvan",
        tier=1,
        base_attack=1,
        base_health=1,
        sprite_filename="spore_pod.png",
        description="Summoned Sylvan spore token.",
        is_token=True,
    ),
    "risen_skull_token": UnitDefinition(
        id="risen_skull_token",
        name="Risen Skull",
        tribe="drowned",
        tier=1,
        base_attack=1,
        base_health=1,
        sprite_filename="drowned_skulls.png",
        description="Summoned Undead skeleton token.",
        is_token=True,
    ),
}


def get_recruitable_units(active_tribes: tuple[str, ...]) -> list[UnitDefinition]:
    """Return all non-token units belonging to the active tribes in this lobby."""
    active_set = set(active_tribes)
    return [
        u for u in UNIT_CATALOG.values() if not u.is_token and u.tribe in active_set
    ]
