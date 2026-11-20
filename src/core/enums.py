"""Canonical enums for Aethelgard: Conclave of War."""

from __future__ import annotations

from enum import StrEnum


class Keyword(StrEnum):
    """Original Aethelgard tactical combat and recruitment keywords."""

    VANGUARD = "VANGUARD"        # Enemies must attack Vanguard units first (Taunt)
    AEGIS = "AEGIS"              # Negates the first instance of damage taken (Divine Shield)
    BLIGHT = "BLIGHT"            # Destroys the first unit this damages in combat (Venomous)
    FRENZY = "FRENZY"            # Attacks twice per turn (Windfury)
    UNDYING = "UNDYING"          # Revives once per combat with 1 Health (Reborn)
    VOW = "VOW"                  # Triggers effect when deployed onto the warband (Battlecry)
    LAST_ECHO = "LAST_ECHO"      # Triggers effect upon dying in combat (Deathrattle)
    RETRIBUTION = "RETRIBUTION"  # Triggers after X friendly units die in combat (Avenge)
    SWEEP = "SWEEP"              # Also damages units adjacent to the primary target (Cleave)
    SHROUD = "SHROUD"            # Cannot be targeted by attacks until this unit attacks (Stealth)


class GamePhase(StrEnum):
    """Distinct phases of an autobattler match."""

    COMMANDER_SELECT = "COMMANDER_SELECT"
    RECRUIT = "RECRUIT"
    RELIC_SELECT = "RELIC_SELECT"
    COMBAT = "COMBAT"
    GAME_OVER = "GAME_OVER"


class HandCardKind(StrEnum):
    """Types of cards a commander can hold in hand."""

    UNIT = "UNIT"
    BLOOD_SHARD = "BLOOD_SHARD"
    FORGE_PLATING = "FORGE_PLATING"
    ASCENSION_ORACLE = "ASCENSION_ORACLE"
    ARCANE_EDICT = "ARCANE_EDICT"
