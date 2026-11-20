"""Tests for all tactical keywords and deterministic combat resolution."""

from __future__ import annotations

from src.core.enums import Keyword
from src.core.rng import SeededRNG
from src.data.units import UNIT_CATALOG
from src.entities.unit import UnitInstance
from src.systems.combat_resolver import resolve_combat


def _unit(uid: str, atk: int | None = None, hp: int | None = None, *kws: Keyword, instance: str = "") -> UnitInstance:
    u = UnitInstance.from_definition(UNIT_CATALOG[uid], instance or f"{uid}_test")
    if atk is not None:
        u.attack = atk
    if hp is not None:
        u.health = hp
        u.max_health = hp
    for kw in kws:
        u.add_keyword(kw)
    return u


def test_vanguard_absorbs_attacks_before_backline() -> None:
    # Player has 1 attacker; opponent has fragile backline + tough Vanguard
    p = [_unit("oakhaven_watchman", 5, 20)]
    backline = _unit("stareater_wisp", 1, 2)
    backline.keywords.discard(Keyword.SHROUD)
    vanguard = _unit("slag_homunculus", 1, 10, Keyword.VANGUARD)
    o = [backline, vanguard]

    outcome = resolve_combat(p, o, player_tier=1, opponent_tier=1, rng=SeededRNG(10))
    # First strike must hit Vanguard, so backline survives the opening blow
    attack_events = [e for e in outcome.events if e.kind == "ATTACK" and e.side == "player"]
    assert attack_events[0].target_id == vanguard.instance_id + "_o"


def test_aegis_blocks_damage_and_blight_and_blight_kills_non_aegis() -> None:
    # Attacker with Blight (1 ATK) hits defender with Aegis (10 HP) -> Aegis pops, defender lives, Blight NOT used
    blighter = _unit("mandragora_matron", 1, 20)  # has BLIGHT
    shielded = _unit("clockwork_flayer", 1, 10, Keyword.AEGIS)
    outcome = resolve_combat([blighter], [shielded], player_tier=1, opponent_tier=1, rng=SeededRNG(1))
    assert any(e.kind == "AEGIS_POP" for e in outcome.events)
    assert any(e.kind == "BLIGHT_KILL" for e in outcome.events)
    assert outcome.winner_side == "player"


def test_frenzy_strikes_twice_and_sweep_hits_adjacent() -> None:
    sweeper = _unit("comet_stalker", 4, 20, Keyword.SWEEP)
    enemies = [
        _unit("mire_ghoul", 0, 3, instance="left"),
        _unit("slag_homunculus", 0, 4, Keyword.VANGUARD, instance="mid"),
        _unit("cinder_sprite", 0, 3, instance="right"),
    ]
    # Vanguard is in the middle, so sweeper clears all 3 on first swing (1 player attack; mire_ghoul spawns a skull)
    outcome = resolve_combat([sweeper], enemies, player_tier=1, opponent_tier=1, rng=SeededRNG(5))
    assert outcome.winner_side == "player"
    player_attacks = [e for e in outcome.events if e.kind == "ATTACK" and e.side == "player"]
    assert len(player_attacks) == 1
    assert any(e.kind == "LAST_ECHO" for e in outcome.events)

    # Frenzy hits twice on single turn
    frenzy_unit = _unit("flayed_duelist", 3, 20, Keyword.FRENZY)
    brick = _unit("slag_homunculus", 0, 6)
    f_out = resolve_combat([frenzy_unit], [brick], player_tier=1, opponent_tier=1, rng=SeededRNG(2))
    assert f_out.winner_side == "player"
    assert len([e for e in f_out.events if e.kind == "ATTACK"]) == 2


def test_undying_and_last_echo_and_retribution_trigger() -> None:
    # Two fragile allies die -> triggers Rotting Woodwose Retribution (2)
    p = [
        _unit("mire_ghoul", 2, 1),          # Last Echo: summon 1/1 Risen Skull
        _unit("drowned_skulls", 2, 1),      # Undying: revives as 1/1
        _unit("rotting_woodwose", 3, 20),   # Vanguard + Retribution (2): +1/+2
    ]
    o = [_unit("sunwarden_squire", 4, 30)]
    outcome = resolve_combat(p, o, player_tier=2, opponent_tier=2, rng=SeededRNG(33))
    kinds = {e.kind for e in outcome.events}
    assert "LAST_ECHO" in kinds
    assert "UNDYING" in kinds
    assert "RETRIBUTION" in kinds


def test_shroud_prevents_targeting_while_non_shroud_ally_exists() -> None:
    shrouded = _unit("stareater_wisp", 1, 2)  # has SHROUD
    exposed = _unit("oakhaven_watchman", 1, 8)  # Vanguard & non-Shroud
    attacker = _unit("slag_homunculus", 4, 20)
    attacker.keywords.discard(Keyword.VANGUARD)

    outcome = resolve_combat([attacker], [shrouded, exposed], player_tier=1, opponent_tier=1, rng=SeededRNG(9))
    first_atk = next(e for e in outcome.events if e.kind == "ATTACK" and e.side == "player")
    assert first_atk.target_id == exposed.instance_id + "_o"


def test_combat_is_deterministic_with_same_seed() -> None:
    p = [_unit("thornvein_creeper"), _unit("spore_pod"), _unit("bramble_hound")]
    o = [_unit("drowned_skulls"), _unit("mire_ghoul"), _unit("leech_husk")]
    out_a = resolve_combat(p, o, player_tier=2, opponent_tier=2, rng=SeededRNG(999))
    out_b = resolve_combat(p, o, player_tier=2, opponent_tier=2, rng=SeededRNG(999))
    assert out_a.winner_side == out_b.winner_side
    assert out_a.damage_to_loser == out_b.damage_to_loser
    assert [(e.kind, e.source_id, e.target_id, e.value) for e in out_a.events] == [
        (e.kind, e.source_id, e.target_id, e.value) for e in out_b.events
    ]
