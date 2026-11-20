"""Full 8-Commander War Conclave tournament loop, AI turns, pairing, and Dawn Relics."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.core.enums import GamePhase, HandCardKind
from src.core.rng import SeededRNG
from src.data.commanders import COMMANDER_CATALOG
from src.data.edicts_and_relics import ARCANE_EDICTS, DAWN_RELICS
from src.data.tribes import select_lobby_tribes
from src.entities.commander import CommanderState
from src.systems.combat_resolver import CombatOutcome, resolve_combat
from src.systems.conclave_shop import ConclaveShopService, UnitPool


@dataclass
class RoundMatchRecord:
    """Pairing and combat outcome between two Commanders for one round."""

    round_number: int
    slot_a: int
    slot_b: int
    is_ghost_match: bool
    outcome: CombatOutcome


@dataclass
class LobbyManager:
    """Coordinates an 8-Commander War Conclave match from Commander pick to Top-1 victory."""

    rng: SeededRNG = field(default_factory=SeededRNG)
    phase: GamePhase = GamePhase.COMMANDER_SELECT
    round_number: int = 0
    active_tribes: tuple[str, ...] = ()
    exiled_tribe: str = ""
    commander_choices: list[str] = field(default_factory=list)
    commanders: list[CommanderState] = field(default_factory=list)
    pool: UnitPool | None = None
    shop: ConclaveShopService | None = None
    current_pairings: list[tuple[int, int, bool]] = field(default_factory=list)
    last_human_outcome: CombatOutcome | None = None
    last_human_opponent_slot: int | None = None
    round_history: list[RoundMatchRecord] = field(default_factory=list)
    _elimination_cursor: int = 8

    def __post_init__(self) -> None:
        if not self.active_tribes:
            self._initialize_lobby()

    def _initialize_lobby(self) -> None:
        self.active_tribes, self.exiled_tribe = select_lobby_tribes(self.rng)
        all_ids = list(COMMANDER_CATALOG.keys())
        self.rng.shuffle(all_ids)
        self.commander_choices = all_ids[:3]
        self.pool = UnitPool(self.active_tribes, self.rng.fork(101))
        self.shop = ConclaveShopService(
            pool=self.pool,
            rng=self.rng.fork(202),
            active_tribes=self.active_tribes,
        )
        self.phase = GamePhase.COMMANDER_SELECT
        self.round_number = 0
        self._elimination_cursor = 8

    @property
    def human(self) -> CommanderState:
        return self.commanders[0]

    def select_human_commander(self, commander_id: str) -> None:
        if commander_id not in COMMANDER_CATALOG:
            raise ValueError(f"Unknown commander: {commander_id}")
        if self.phase != GamePhase.COMMANDER_SELECT:
            raise RuntimeError("Commander already selected for this lobby.")

        human_def = COMMANDER_CATALOG[commander_id]
        others = [cid for cid in COMMANDER_CATALOG if cid != commander_id]
        self.rng.shuffle(others)

        self.commanders = [CommanderState.from_definition(0, human_def, is_human=True)]
        for idx, cid in enumerate(others[:7], start=1):
            self.commanders.append(
                CommanderState.from_definition(idx, COMMANDER_CATALOG[cid], is_human=False)
            )
        self.advance_to_next_round()

    def _offer_relics(self, commander: CommanderState, tier_kind: str) -> list[str]:
        candidates = [
            rid
            for rid, relic in DAWN_RELICS.items()
            if relic.tier_kind == tier_kind and rid not in commander.relics
        ]
        self.rng.shuffle(candidates)
        return candidates[:3]

    def _apply_relic_grant(self, commander: CommanderState, relic_id: str) -> None:
        if relic_id not in commander.relics:
            commander.relics.append(relic_id)
        if relic_id == "aether_sovereign_seal":
            commander.crowns_cap = 13
            commander.crowns += 3

    def pick_human_relic(self, choice_index: int) -> str:
        if self.phase != GamePhase.RELIC_SELECT:
            raise RuntimeError("Not currently selecting a Dawn Relic.")
        choices = self.human.pending_relic_choices
        if choice_index < 0 or choice_index >= len(choices):
            raise ValueError("Invalid Dawn Relic index.")
        chosen = choices[choice_index]
        self._apply_relic_grant(self.human, chosen)
        self.human.pending_relic_choices.clear()
        self.phase = GamePhase.RECRUIT
        return chosen

    def _pair_commanders(self) -> None:
        alive = [c for c in self.commanders if c.is_alive]
        if len(alive) <= 1:
            self.current_pairings = []
            return

        slots = [c.slot_index for c in alive]
        self.rng.shuffle(slots)

        pairings: list[tuple[int, int, bool]] = []
        # Pair even groups; if odd count, lowest-vitality living commander faces an eliminated ghost
        if len(slots) % 2 == 1:
            ghost_pool = [c for c in self.commanders if c.eliminated]
            if ghost_pool:
                ghost = self.rng.choice(ghost_pool)
            else:
                ghost = min(alive, key=lambda c: c.total_vitality)
            # Pick living player not equal to ghost when possible
            solo = min(alive, key=lambda c: c.total_vitality)
            slots.remove(solo.slot_index)
            pairings.append((solo.slot_index, ghost.slot_index, True))

        for i in range(0, len(slots), 2):
            pairings.append((slots[i], slots[i + 1], False))

        self.current_pairings = pairings
        for a, b, is_ghost in pairings:
            if not is_ghost:
                self.commanders[a].last_opponent_slot = b
                self.commanders[b].last_opponent_slot = a
            else:
                self.commanders[a].last_opponent_slot = b

    def get_human_opponent(self) -> tuple[CommanderState | None, bool]:
        for a, b, is_ghost in self.current_pairings:
            if a == 0:
                return self.commanders[b], is_ghost
            if b == 0:
                return self.commanders[a], is_ghost
        return None, False

    def _run_ai_turn(self, ai: CommanderState) -> None:
        if ai.eliminated or self.shop is None:
            return

        preferred = set(ai.definition.preferred_tribes)
        # 1. Play any existing cards in hand first
        safety = 0
        while ai.warband.hand and safety < 20:
            safety += 1
            played = False
            for idx, card in enumerate(ai.warband.hand):
                if card.kind == HandCardKind.ASCENSION_ORACLE:
                    res = self.shop.play_hand_card(ai, idx)
                    if res.oracle_triggered and ai.pending_oracle_choices:
                        best_i = max(
                            range(len(ai.pending_oracle_choices)),
                            key=lambda k: (
                                ai.pending_oracle_choices[k].tier * 5
                                + (4 if ai.pending_oracle_choices[k].tribe in preferred else 0)
                                + ai.pending_oracle_choices[k].attack
                                + ai.pending_oracle_choices[k].health
                            ),
                        )
                        self.shop.pick_oracle_choice(ai, best_i)
                    played = True
                    break
                elif card.kind in {
                    HandCardKind.BLOOD_SHARD,
                    HandCardKind.FORGE_PLATING,
                    HandCardKind.ARCANE_EDICT,
                }:
                    if ai.warband.board or card.kind == HandCardKind.ARCANE_EDICT:
                        self.shop.play_hand_card(ai, idx, target_board_index=0)
                        played = True
                        break
                elif card.kind == HandCardKind.UNIT and not ai.warband.is_board_full:
                    self.shop.play_hand_card(ai, idx)
                    played = True
                    break
            if not played:
                break

        # 2. Elevate Bastion Tier on standard tempo rounds
        if (
            ai.bastion_tier < 6
            and ai.crowns >= ai.upgrade_cost
            and (
                self.round_number in {2, 4, 6, 8, 10}
                or ai.upgrade_cost <= 3
                or (ai.crowns - ai.upgrade_cost >= 3 and self.round_number >= 3)
            )
        ):
            self.shop.elevate_bastion(ai)

        # 3. Buy units, upgrade weaker slots, and refresh thoughtfully
        actions = 0
        while ai.crowns >= 3 and actions < 8:
            actions += 1
            if not ai.shop_units:
                if ai.crowns >= 4 or ai.free_refreshes > 0:
                    self.shop.refresh_shop(ai)
                else:
                    break
            if not ai.shop_units:
                break

            def _score_shop_unit(idx: int) -> float:
                u = ai.shop_units[idx]
                score = u.tier * 3.0 + u.attack + u.health
                if u.tribe in preferred:
                    score += 3.5
                if ai.warband.count_non_ascended(u.unit_id) == 2:
                    score += 18.0
                elif ai.warband.count_non_ascended(u.unit_id) == 1:
                    score += 5.0
                return score

            best_shop_idx = max(range(len(ai.shop_units)), key=_score_shop_unit)
            best_unit = ai.shop_units[best_shop_idx]
            will_triple = ai.warband.count_non_ascended(best_unit.unit_id) >= 2

            # If board is full and we won't triple, check if we should dismiss weakest unit
            if ai.warband.is_board_full and not will_triple:
                weakest_idx = min(
                    range(len(ai.warband.board)),
                    key=lambda k: (
                        ai.warband.board[k].tier * 2
                        + ai.warband.board[k].attack
                        + ai.warband.board[k].health
                        + (10 if ai.warband.board[k].is_ascended else 0)
                    ),
                )
                weakest = ai.warband.board[weakest_idx]
                if (best_unit.tier * 3 + best_unit.attack + best_unit.health) > (
                    weakest.tier * 2 + weakest.attack + weakest.health + 2
                ):
                    self.shop.dismiss_unit(ai, weakest_idx)
                else:
                    break

            res = self.shop.recruit_unit(ai, best_shop_idx)
            if not res.ok:
                break

            # Immediately deploy any new units & open oracles
            inner = 0
            while ai.warband.hand and inner < 12:
                inner += 1
                progressed = False
                for h_idx, h_card in enumerate(ai.warband.hand):
                    if h_card.kind == HandCardKind.ASCENSION_ORACLE:
                        o_res = self.shop.play_hand_card(ai, h_idx)
                        if o_res.oracle_triggered and ai.pending_oracle_choices:
                            best_o = max(
                                range(len(ai.pending_oracle_choices)),
                                key=lambda k: ai.pending_oracle_choices[k].tier * 5
                                + ai.pending_oracle_choices[k].attack
                                + ai.pending_oracle_choices[k].health,
                            )
                            self.shop.pick_oracle_choice(ai, best_o)
                        progressed = True
                        break
                    elif h_card.kind == HandCardKind.UNIT and not ai.warband.is_board_full:
                        self.shop.play_hand_card(ai, h_idx)
                        progressed = True
                        break
                if not progressed:
                    break

            # Refresh if leftover crowns >= 4 and shop has nothing exciting
            if ai.crowns >= 4 and len(ai.shop_units) <= 1:
                self.shop.refresh_shop(ai)

        # 4. Spend leftover crowns on Arcane Edict or Commander Mandate
        if ai.shop_edict_id is not None:
            edict = ARCANE_EDICTS[ai.shop_edict_id]
            cost = max(0, edict.crown_cost - (1 if ai.commander_id == "rachel" else 0))
            if ai.crowns >= cost:
                self.shop.buy_shop_edict(ai)

        if not ai.definition.is_passive and not ai.mandate_used_this_round:
            if ai.crowns >= ai.definition.mandate_cost and (
                ai.warband.board or ai.commander_id == "carmilla"
            ):
                if ai.commander_id != "carmilla" or ai.health > 10:
                    self.shop.use_commander_mandate(ai, target_board_index=0)

        # Play any shards/platings/edicts gained from mandate or vow
        for idx in range(len(ai.warband.hand) - 1, -1, -1):
            card = ai.warband.hand[idx]
            if card.kind in {
                HandCardKind.BLOOD_SHARD,
                HandCardKind.FORGE_PLATING,
                HandCardKind.ARCANE_EDICT,
            }:
                if ai.warband.board or card.kind == HandCardKind.ARCANE_EDICT:
                    self.shop.play_hand_card(ai, idx, target_board_index=0)

    def advance_to_next_round(self) -> None:
        if self.phase == GamePhase.GAME_OVER:
            return
        assert self.shop is not None

        self.round_number += 1
        for comm in self.commanders:
            if comm.eliminated:
                continue
            comm.begin_recruitment_round(self.round_number)
            # Passive Commander & Relic round-start triggers
            if comm.commander_id == "ironforge" and self.round_number % 2 == 0:
                self.shop._add_forge_plating(comm)
            if comm.has_relic("crimson_chalice"):
                self.shop._add_blood_shards(comm, 2)

            self.shop.populate_shop(comm, preserve_frozen=True)

            # Dawn Relic awards on Round 6 (Lesser) and Round 9 (Greater)
            relic_tier: str | None = None
            if self.round_number == 6:
                relic_tier = "LESSER"
            elif self.round_number == 9:
                relic_tier = "GREATER"

            if relic_tier is not None:
                choices = self._offer_relics(comm, relic_tier)
                if comm.is_human and choices:
                    comm.pending_relic_choices = choices
                elif choices:
                    self._apply_relic_grant(comm, self.rng.choice(choices))

            if not comm.is_human:
                self._run_ai_turn(comm)

        self._pair_commanders()
        if self.human.pending_relic_choices:
            self.phase = GamePhase.RELIC_SELECT
        else:
            self.phase = GamePhase.RECRUIT

    def start_combat_phase(self) -> CombatOutcome | None:
        """Resolve all round pairings and update Commander Armor/Health/Placements."""
        if self.phase not in {GamePhase.RECRUIT, GamePhase.RELIC_SELECT}:
            raise RuntimeError(f"Cannot start combat from phase {self.phase}")
        if self.human.pending_relic_choices:
            # Safety fallback if invoked directly before picking relic
            self.pick_human_relic(0)

        self.phase = GamePhase.COMBAT
        # End-of-recruit triggers (e.g. Sanctum Reliquary)
        for comm in self.commanders:
            if comm.is_alive and comm.has_relic("sanctum_reliquary"):
                for u in comm.warband.board:
                    u.apply_buff(2, 2)

        human_outcome: CombatOutcome | None = None
        newly_eliminated: list[CommanderState] = []

        for slot_a, slot_b, is_ghost in self.current_pairings:
            ca = self.commanders[slot_a]
            cb = self.commanders[slot_b]
            outcome = resolve_combat(
                ca.warband.board,
                cb.warband.board,
                player_tier=ca.bastion_tier,
                opponent_tier=cb.bastion_tier,
                player_relics=ca.relics,
                opponent_relics=cb.relics,
                rng=self.rng.fork(self.round_number * 100 + slot_a * 10 + slot_b),
            )
            self.round_history.append(
                RoundMatchRecord(
                    round_number=self.round_number,
                    slot_a=slot_a,
                    slot_b=slot_b,
                    is_ghost_match=is_ghost,
                    outcome=outcome,
                )
            )

            if outcome.winner_side == "player":
                ca.wins += 1
                ca.win_streak += 1
                ca.last_damage_dealt = outcome.damage_to_loser
                if not is_ghost:
                    cb.losses += 1
                    cb.win_streak = 0
                    cb.apply_damage(outcome.damage_to_loser)
                    if cb.eliminated:
                        newly_eliminated.append(cb)
            elif outcome.winner_side == "opponent":
                ca.losses += 1
                ca.win_streak = 0
                ca.apply_damage(outcome.damage_to_loser)
                if ca.eliminated:
                    newly_eliminated.append(ca)
                if not is_ghost:
                    cb.wins += 1
                    cb.win_streak += 1
                    cb.last_damage_dealt = outcome.damage_to_loser
            else:
                ca.ties += 1
                ca.win_streak = 0
                if not is_ghost:
                    cb.ties += 1
                    cb.win_streak = 0

            if slot_a == 0:
                human_outcome = outcome
                self.last_human_opponent_slot = slot_b
            elif slot_b == 0:
                # Flip perspective if human happened to be slot_b
                flipped = CombatOutcome(
                    winner_side=(
                        "opponent"
                        if outcome.winner_side == "player"
                        else ("player" if outcome.winner_side == "opponent" else "tie")
                    ),
                    damage_to_loser=outcome.damage_to_loser,
                    surviving_player_units=outcome.surviving_opponent_units,
                    surviving_opponent_units=outcome.surviving_player_units,
                    events=outcome.events,
                )
                human_outcome = flipped
                self.last_human_opponent_slot = slot_a

        # Assign placements from 8th up; higher health/round prior tie-break
        newly_eliminated.sort(key=lambda c: c.total_vitality)
        for dead in newly_eliminated:
            if dead.placement == 0:
                dead.placement = self._elimination_cursor
                self._elimination_cursor -= 1
                # Return eliminated commander's board/hand units to shared pool
                if self.pool is not None:
                    for u in dead.warband.board:
                        if not u.is_token:
                            self.pool.return_unit(u.unit_id, 3 if u.is_ascended else 1)

        alive = [c for c in self.commanders if c.is_alive]
        if len(alive) <= 1 or self.human.eliminated:
            # Finalize placements for remaining commanders
            remaining_alive = sorted(alive, key=lambda c: c.total_vitality)
            for c in remaining_alive:
                if c.placement == 0:
                    c.placement = self._elimination_cursor
                    self._elimination_cursor -= 1
            if self.human.placement == 0:
                self.human.placement = 1
            self.phase = GamePhase.GAME_OVER

        self.last_human_outcome = human_outcome
        return human_outcome

    def leaderboard(self) -> list[CommanderState]:
        """Sort commanders: alive first by vitality desc, then eliminated by placement asc."""
        alive = sorted(
            [c for c in self.commanders if c.is_alive],
            key=lambda c: (c.total_vitality, c.bastion_tier, c.wins),
            reverse=True,
        )
        dead = sorted(
            [c for c in self.commanders if c.eliminated],
            key=lambda c: c.placement,
        )
        return alive + dead
