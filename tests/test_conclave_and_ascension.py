"""Tests for Conclave economy, Bastion elevation, Ascension triples, Edicts, and Relics."""

from __future__ import annotations

from src.core.enums import GamePhase, HandCardKind, Keyword
from src.core.rng import SeededRNG
from src.data.commanders import COMMANDER_CATALOG
from src.data.tribes import BIOME_TRIBE_IDS, NEUTRAL_TRIBE_ID
from src.data.units import TIER_POOL_COPIES, UNIT_CATALOG
from src.entities.commander import CommanderState
from src.entities.unit import HandCard, UnitInstance
from src.systems.conclave_shop import ConclaveShopService, UnitPool
from src.systems.lobby_manager import LobbyManager


def _make_shop_and_commander(seed: int = 77) -> tuple[ConclaveShopService, CommanderState]:
    rng = SeededRNG(seed)
    active = tuple(BIOME_TRIBE_IDS[:5]) + (NEUTRAL_TRIBE_ID,)
    pool = UnitPool(active, rng)
    shop = ConclaveShopService(pool=pool, rng=rng, active_tribes=active)
    comm = CommanderState.from_definition(0, COMMANDER_CATALOG["rowan"], is_human=True)
    return shop, comm


def test_crown_economy_and_bastion_tier_cost_decay() -> None:
    shop, comm = _make_shop_and_commander()
    comm.begin_recruitment_round(1)
    assert comm.crowns == 3
    assert comm.max_crowns == 3
    assert comm.upgrade_cost == 4  # decayed 5 -> 4 on first round tick

    comm.begin_recruitment_round(8)
    assert comm.max_crowns == 10
    assert comm.crowns == 10

    res = shop.elevate_bastion(comm)
    assert res.ok
    assert comm.bastion_tier == 2
    assert comm.upgrade_cost == 7


def test_unit_pool_depletion_and_return_on_dismiss() -> None:
    shop, comm = _make_shop_and_commander()
    assert shop.pool.counts["oakhaven_watchman"] == TIER_POOL_COPIES[1]

    u = UnitInstance.from_definition(UNIT_CATALOG["oakhaven_watchman"], "u_test_1")
    shop.pool.counts["oakhaven_watchman"] -= 1
    comm.shop_units = [u]
    comm.crowns = 5

    rec = shop.recruit_unit(comm, 0)
    assert rec.ok
    assert comm.crowns == 2
    assert len(comm.warband.hand) == 1

    play = shop.play_hand_card(comm, 0)
    assert play.ok
    assert len(comm.warband.board) == 1

    dis = shop.dismiss_unit(comm, 0)
    assert dis.ok
    assert comm.crowns == 3
    assert shop.pool.counts["oakhaven_watchman"] == TIER_POOL_COPIES[1]


def test_three_copy_ascension_fusion_and_oracle_discover() -> None:
    shop, comm = _make_shop_and_commander()
    comm.bastion_tier = 2
    comm.crowns = 10

    defn = UNIT_CATALOG["thornvein_creeper"]
    # Two buffed copies already on board
    u1 = UnitInstance.from_definition(defn, "u1")
    u1.apply_buff(2, 1)  # 4/3 (+2/+1 over 2/2)
    u2 = UnitInstance.from_definition(defn, "u2")
    u2.apply_buff(0, 2)  # 2/4 (+0/+2 over 2/2)
    comm.warband.board.extend([u1, u2])

    # Third copy in Conclave shop
    u3 = UnitInstance.from_definition(defn, "u3")
    comm.shop_units = [u3]

    res = shop.recruit_unit(comm, 0)
    assert res.ok
    assert res.ascended_unit is not None
    assert res.ascended_unit.is_ascended is True
    # Base 2/2 * 2 = 4/4 + accumulated (+2/+3) = 6/7
    assert res.ascended_unit.attack == 6
    assert res.ascended_unit.health == 7
    assert len(comm.warband.board) == 0
    assert any(c.kind == HandCardKind.ASCENSION_ORACLE and c.discover_tier == 3 for c in comm.warband.hand)

    # Open the Ascension Oracle and pick option 0
    oracle_idx = next(i for i, c in enumerate(comm.warband.hand) if c.kind == HandCardKind.ASCENSION_ORACLE)
    o_res = shop.play_hand_card(comm, oracle_idx)
    assert o_res.ok and o_res.oracle_triggered
    assert len(comm.pending_oracle_choices) == 3
    assert all(choice.tier == 3 for choice in comm.pending_oracle_choices)

    pick = shop.pick_oracle_choice(comm, 1)
    assert pick.ok
    assert not comm.pending_oracle_choices


def test_arcane_edict_and_candelabra_synergy() -> None:
    shop, comm = _make_shop_and_commander()
    comm.crowns = 10
    fiend = UnitInstance.from_definition(UNIT_CATALOG["candelabra_fiend"], "fiend_1")
    comm.warband.board.append(fiend)
    comm.shop_edict_id = "oakhaven_ration"  # costs 1, gives random ally +2/+2

    res = shop.buy_shop_edict(comm)
    assert res.ok
    assert comm.crowns == 9
    # +2/+2 from ration + +1/+2 from Candelabra Fiend passive => base 3/4 becomes 6/8
    assert fiend.attack == 6
    assert fiend.health == 8


def test_blood_shard_and_forge_plating_application() -> None:
    shop, comm = _make_shop_and_commander()
    garg = UnitInstance.from_definition(UNIT_CATALOG["crimson_gargoyle"], "garg_1")
    comm.warband.board.append(garg)
    comm.warband.hand.append(HandCard("c1", HandCardKind.BLOOD_SHARD, "Blood Shard"))
    comm.warband.hand.append(HandCard("c2", HandCardKind.FORGE_PLATING, "Forge Plating"))

    assert shop.play_hand_card(comm, 0, target_board_index=0).ok
    # Base 1/4 + Blood Shard (+1/+1) + Crimson Gargoyle bonus (+1/+0) = 3/5
    assert garg.attack == 3
    assert garg.health == 5

    assert shop.play_hand_card(comm, 0, target_board_index=0).ok
    # +2/+2 & Aegis => 5/7 with Aegis
    assert garg.attack == 5
    assert garg.health == 7
    assert garg.has_keyword(Keyword.AEGIS)


def test_dawn_relics_triggered_on_rounds_6_and_9() -> None:
    lobby = LobbyManager(rng=SeededRNG(2026))
    lobby.select_human_commander(lobby.commander_choices[0])

    for expected_round in range(2, 7):
        lobby.start_combat_phase()
        if lobby.phase == GamePhase.GAME_OVER:
            break
        lobby.advance_to_next_round()
        if expected_round == 6 and lobby.phase != GamePhase.GAME_OVER:
            assert lobby.phase == GamePhase.RELIC_SELECT
            assert len(lobby.human.pending_relic_choices) == 3
            lobby.pick_human_relic(0)
            assert lobby.phase == GamePhase.RECRUIT
            assert len(lobby.human.relics) == 1
