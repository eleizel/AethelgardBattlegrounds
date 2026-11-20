"""Tribe definitions and per-match biome rotation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from src.core.rng import SeededRNG


@dataclass(frozen=True)
class TribeDefinition:
    id: str
    name: str
    es_name: str
    biome_origin: str
    focus: str
    color_hex: str
    is_neutral: bool = False


BIOME_TRIBE_IDS: Final[tuple[str, ...]] = (
    "sylvan",
    "drowned",
    "forge",
    "cult",
    "crimson",
    "astral",
)

NEUTRAL_TRIBE_ID: Final[str] = "mercenary"

TRIBE_REGISTRY: Final[dict[str, TribeDefinition]] = {
    "sylvan": TribeDefinition(
        id="sylvan",
        name="Sylvan Blight",
        es_name="Arboreto Marchito",
        biome_origin="The Wilted Arboretum",
        focus="Blight (Ponzoña), Health growth, and spore Last Echoes",
        color_hex="#3E9C5C",
    ),
    "drowned": TribeDefinition(
        id="drowned",
        name="Drowned Undead",
        es_name="Osario Ahogado",
        biome_origin="The Drowned Ossuary",
        focus="Undying revives, Last Echo swarms, and Retribution scaling",
        color_hex="#4D78A8",
    ),
    "forge": TribeDefinition(
        id="forge",
        name="Infernal Forge",
        es_name="Fundición del Tormento",
        biome_origin="The Foundry of Torment",
        focus="Aegis shields, plating attachments, and explosive shrapnel",
        color_hex="#D97B29",
    ),
    "cult": TribeDefinition(
        id="cult",
        name="Cathedral Cult",
        es_name="Catedral Profanada",
        biome_origin="The Desecrated Cathedral",
        focus="Arcane Edicts, stone Vanguard walls, and zealot Retribution",
        color_hex="#8A56B8",
    ),
    "crimson": TribeDefinition(
        id="crimson",
        name="Crimson Court",
        es_name="Sagrario de Sangre",
        biome_origin="The Blood Sanctum",
        focus="Blood Shards (+1/+1), Frenzy double strikes, and rapid scaling",
        color_hex="#B8323B",
    ),
    "astral": TribeDefinition(
        id="astral",
        name="Astral Void",
        es_name="Observatorio Astral",
        biome_origin="The Astral Observatory",
        focus="Sweep cleaves, Shroud ambushes, and Conclave refresh synergy",
        color_hex="#32B2CC",
    ),
    "mercenary": TribeDefinition(
        id="mercenary",
        name="Oakhaven Mercenaries",
        es_name="Mercenarios de Oakhaven",
        biome_origin="Oakhaven Village",
        focus="Cross-tribe support, Crowns economy, and tactical utility",
        color_hex="#C9A84C",
        is_neutral=True,
    ),
}


def select_lobby_tribes(rng: SeededRNG) -> tuple[tuple[str, ...], str]:
    """Select 5 active biome tribes + mercenary, exiling 1 biome tribe for the match."""
    exiled = rng.choice(BIOME_TRIBE_IDS)
    active = tuple(t for t in BIOME_TRIBE_IDS if t != exiled) + (NEUTRAL_TRIBE_ID,)
    return active, exiled
