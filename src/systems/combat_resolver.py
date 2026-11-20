"""Deterministic step-by-step automated combat simulator."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.core.enums import Keyword
from src.core.rng import SeededRNG
from src.data.units import UNIT_CATALOG, UnitEffectSpec
from src.entities.unit import UnitInstance
from src.entities.warband import MAX_WARBAND_SIZE


@dataclass(frozen=True)
class CombatEvent:
    """Single atomic visual/telemetry step emitted during combat."""

    seq: int
    kind: str  # "START", "ATTACK", "AEGIS_POP", "BLIGHT_KILL", "DEATH", "LAST_ECHO", "UNDYING", "RETRIBUTION", "RESULT"
    side: str  # "player", "opponent", "both"
    source_id: str = ""
    target_id: str = ""
    value: int = 0
    description: str = ""


@dataclass
class CombatOutcome:
    """Full resolution of a round combat encounter."""

    winner_side: str  # "player", "opponent", "tie"
    damage_to_loser: int
    surviving_player_units: list[UnitInstance] = field(default_factory=list)
    surviving_opponent_units: list[UnitInstance] = field(default_factory=list)
    events: list[CombatEvent] = field(default_factory=list)


class _CombatRunner:
    def __init__(
        self,
        player_board: list[UnitInstance],
        opponent_board: list[UnitInstance],
        *,
        player_tier: int,
        opponent_tier: int,
        player_relics: list[str],
        opponent_relics: list[str],
        rng: SeededRNG,
    ) -> None:
        self.boards: dict[str, list[UnitInstance]] = {
            "player": [u.clone_for_combat("_p") for u in player_board],
            "opponent": [u.clone_for_combat("_o") for u in opponent_board],
        }
        self.tiers = {"player": player_tier, "opponent": opponent_tier}
        self.relics = {"player": set(player_relics), "opponent": set(opponent_relics)}
        self.rng = rng
        self.events: list[CombatEvent] = []
        self._seq = 0
        self._token_seq = 0
        self.next_attacker_idx = {"player": 0, "opponent": 0}

    def _emit(
        self,
        kind: str,
        side: str,
        *,
        source_id: str = "",
        target_id: str = "",
        value: int = 0,
        description: str = "",
    ) -> None:
        self._seq += 1
        self.events.append(
            CombatEvent(
                seq=self._seq,
                kind=kind,
                side=side,
                source_id=source_id,
                target_id=target_id,
                value=value,
                description=description,
            )
        )

    def _apply_start_relics(self, side: str) -> None:
        board = self.boards[side]
        relic_set = self.relics[side]
        if not board:
            return

        if "briar_crown_band" in relic_set:
            for u in board:
                u.apply_buff(2, 2)
        if "elder_root_effigy" in relic_set:
            for u in board:
                u.apply_buff(5, 6)
        if "sunwarden_banner" in relic_set:
            board[0].add_keyword(Keyword.AEGIS)
        if "molten_anvil_core" in relic_set:
            for u in board[:2]:
                u.apply_buff(3, 0)
                u.add_keyword(Keyword.AEGIS)
        if "solar_heartstone" in relic_set:
            first = board[0]
            boost = min(30, first.attack)
            first.apply_buff(boost, 6)
        if "eternal_echo_bell" in relic_set:
            for u in board:
                if u.has_keyword(Keyword.LAST_ECHO) or u.has_keyword(Keyword.UNDYING):
                    u.apply_buff(4, 4)

    def _spawn_token(
        self,
        side: str,
        token_id: str,
        insert_pos: int,
        *,
        atk_bonus: int = 0,
        hp_bonus: int = 0,
        is_ascended: bool = False,
    ) -> UnitInstance | None:
        board = self.boards[side]
        if len(board) >= MAX_WARBAND_SIZE:
            return None
        self._token_seq += 1
        defn = UNIT_CATALOG[token_id]
        token = UnitInstance.from_definition(
            defn,
            f"tok_{side}_{self._token_seq}",
            is_ascended=is_ascended,
        )
        if atk_bonus or hp_bonus:
            token.apply_buff(atk_bonus, hp_bonus)
        if "ossuary_lantern" in self.relics[side]:
            token.apply_buff(2, 1)
        pos = max(0, min(len(board), insert_pos))
        board.insert(pos, token)
        return token

    def _choose_target_index(self, defender_side: str) -> int | None:
        defenders = self.boards[defender_side]
        if not defenders:
            return None
        non_shroud = [i for i, u in enumerate(defenders) if not u.has_keyword(Keyword.SHROUD)]
        eligible = non_shroud if non_shroud else list(range(len(defenders)))
        vanguards = [i for i in eligible if defenders[i].has_keyword(Keyword.VANGUARD)]
        pool = vanguards if vanguards else eligible
        return self.rng.choice(pool)

    def _deal_strike_damage(self, attacker: UnitInstance, defender: UnitInstance, side: str, opp_side: str) -> None:
        if attacker.attack <= 0:
            return
        if defender.has_keyword(Keyword.AEGIS):
            defender.keywords.discard(Keyword.AEGIS)
            self._emit(
                "AEGIS_POP",
                opp_side,
                source_id=attacker.instance_id,
                target_id=defender.instance_id,
                description=f"{defender.name}'s Aegis absorbed the strike from {attacker.name}.",
            )
            return

        defender.health -= attacker.attack
        if attacker.has_keyword(Keyword.BLIGHT) and not attacker.blight_used:
            attacker.blight_used = True
            defender.health = 0
            self._emit(
                "BLIGHT_KILL",
                side,
                source_id=attacker.instance_id,
                target_id=defender.instance_id,
                value=attacker.attack,
                description=f"{attacker.name}'s Blight fatally poisoned {defender.name}!",
            )

    def _trigger_retribution(self, side: str, unit: UnitInstance, spec: UnitEffectSpec) -> None:
        mult = unit.effect_multiplier
        board = self.boards[side]
        if spec.kind == "buff_self":
            unit.apply_buff(spec.attack_delta * mult, spec.health_delta * mult)
        elif spec.kind == "summon" and spec.token_id:
            idx = board.index(unit) + 1 if unit in board else len(board)
            for _ in range(spec.count):
                self._spawn_token(
                    side,
                    spec.token_id,
                    idx,
                    atk_bonus=spec.attack_delta * mult,
                    hp_bonus=spec.health_delta * mult,
                    is_ascended=unit.is_ascended,
                )
        elif spec.kind == "grant_keyword_ally" and spec.grant_keyword is not None:
            candidates = [
                u
                for u in board
                if (spec.target_tribe is None or u.tribe == spec.target_tribe)
                and not u.has_keyword(spec.grant_keyword)
            ]
            if candidates:
                for _ in range(mult):
                    if not candidates:
                        break
                    chosen = self.rng.choice(candidates)
                    chosen.add_keyword(spec.grant_keyword)
                    candidates.remove(chosen)
        elif spec.kind == "buff_all_allies":
            for u in board:
                if spec.target_tribe is None or u.tribe == spec.target_tribe:
                    u.apply_buff(spec.attack_delta * mult, spec.health_delta * mult)
        self._emit(
            "RETRIBUTION",
            side,
            source_id=unit.instance_id,
            description=f"{unit.name} triggered Retribution!",
        )

    def _trigger_last_echo(self, side: str, unit: UnitInstance, death_slot: int) -> None:
        spec = unit.definition.last_echo
        if spec is None:
            return
        mult = unit.effect_multiplier
        opp_side = "opponent" if side == "player" else "player"
        if spec.kind == "summon" and spec.token_id:
            for offset in range(spec.count):
                tok = self._spawn_token(
                    side,
                    spec.token_id,
                    death_slot + offset,
                    atk_bonus=spec.attack_delta,
                    hp_bonus=spec.health_delta,
                    is_ascended=unit.is_ascended,
                )
                if tok is not None:
                    self._emit(
                        "LAST_ECHO",
                        side,
                        source_id=unit.instance_id,
                        target_id=tok.instance_id,
                        description=f"{unit.name}'s Last Echo summoned {tok.name}.",
                    )
        elif spec.kind == "buff_all_allies":
            for u in self.boards[side]:
                if spec.target_tribe is None or u.tribe == spec.target_tribe:
                    u.apply_buff(spec.attack_delta * mult, spec.health_delta * mult)
            self._emit(
                "LAST_ECHO",
                side,
                source_id=unit.instance_id,
                description=f"{unit.name}'s Last Echo empowered friendly units.",
            )
        elif spec.kind == "damage_random_enemy":
            for _ in range(spec.count * mult):
                living = [u for u in self.boards[opp_side] if u.health > 0]
                if not living:
                    break
                target = self.rng.choice(living)
                if target.has_keyword(Keyword.AEGIS):
                    target.keywords.discard(Keyword.AEGIS)
                else:
                    target.health -= spec.damage
                self._emit(
                    "LAST_ECHO",
                    side,
                    source_id=unit.instance_id,
                    target_id=target.instance_id,
                    value=spec.damage,
                    description=f"{unit.name} dealt {spec.damage} Last Echo damage to {target.name}.",
                )
        elif spec.kind == "damage_all_enemies":
            dmg = spec.damage * mult
            for target in self.boards[opp_side]:
                if target.health <= 0:
                    continue
                if target.has_keyword(Keyword.AEGIS):
                    target.keywords.discard(Keyword.AEGIS)
                else:
                    target.health -= dmg
            self._emit(
                "LAST_ECHO",
                side,
                source_id=unit.instance_id,
                value=dmg,
                description=f"{unit.name}'s Last Echo blasted all enemies for {dmg}.",
            )

    def _cleanup_deaths(self) -> None:
        """Process deaths, Retribution, Last Echoes, and Undying revives iteratively."""
        for _ in range(12):
            any_died = False
            for side in ("player", "opponent"):
                board = self.boards[side]
                dead_entries = [(idx, u) for idx, u in enumerate(board) if u.health <= 0]
                if not dead_entries:
                    continue
                any_died = True
                dead_ids = {u.instance_id for _, u in dead_entries}
                # Keep board index adjustment stable from right to left when popping
                for idx, u in reversed(dead_entries):
                    board.pop(idx)
                    self._emit(
                        "DEATH",
                        side,
                        source_id=u.instance_id,
                        description=f"{u.name} fell in combat.",
                    )
                    if idx < self.next_attacker_idx[side]:
                        self.next_attacker_idx[side] = max(0, self.next_attacker_idx[side] - 1)

                # Trigger Retribution for surviving allies
                for ally in list(board):
                    if ally.instance_id in dead_ids or ally.health <= 0:
                        continue
                    ret_spec = ally.definition.retribution
                    if ret_spec is not None and ret_spec.retribution_threshold > 0:
                        ally.retribution_counter += len(dead_entries)
                        while ally.retribution_counter >= ret_spec.retribution_threshold:
                            ally.retribution_counter -= ret_spec.retribution_threshold
                            self._trigger_retribution(side, ally, ret_spec)

                # Trigger Last Echo & Undying in left-to-right death order
                shift = 0
                for orig_idx, dead_unit in dead_entries:
                    insert_at = min(len(board), orig_idx + shift)
                    before_len = len(board)
                    self._trigger_last_echo(side, dead_unit, insert_at)
                    shift += len(board) - before_len

                    if (
                        dead_unit.has_keyword(Keyword.UNDYING)
                        and not dead_unit.undying_used
                        and len(board) < MAX_WARBAND_SIZE
                    ):
                        self._token_seq += 1
                        revived = UnitInstance.from_definition(
                            dead_unit.definition,
                            f"undying_{side}_{self._token_seq}",
                            is_ascended=dead_unit.is_ascended,
                        )
                        revived.health = 1
                        revived.max_health = 1
                        revived.undying_used = True
                        if "ossuary_lantern" in self.relics[side]:
                            revived.apply_buff(2, 1)
                        pos = min(len(board), orig_idx + shift)
                        board.insert(pos, revived)
                        shift += 1
                        self._emit(
                            "UNDYING",
                            side,
                            source_id=revived.instance_id,
                            description=f"{revived.name} rose again via Undying (1 HP)!",
                        )
            if not any_died:
                break

    def run(self) -> CombatOutcome:
        self._apply_start_relics("player")
        self._apply_start_relics("opponent")
        self._emit("START", "both", description="Combat commenced.")

        p_len = len(self.boards["player"])
        o_len = len(self.boards["opponent"])
        if p_len > o_len:
            turn_side = "player"
        elif o_len > p_len:
            turn_side = "opponent"
        else:
            turn_side = self.rng.choice(["player", "opponent"])

        steps = 0
        while self.boards["player"] and self.boards["opponent"] and steps < 250:
            steps += 1
            atk_board = self.boards[turn_side]
            opp_side = "opponent" if turn_side == "player" else "player"
            def_board = self.boards[opp_side]

            if not atk_board or not def_board:
                break

            idx = self.next_attacker_idx[turn_side] % len(atk_board)
            attacker = atk_board[idx]
            self.next_attacker_idx[turn_side] = (idx + 1) % max(1, len(atk_board))

            # Units with 0 attack pass their turn safely
            if attacker.attack > 0:
                strikes = 2 if attacker.has_keyword(Keyword.FRENZY) else 1
                for _ in range(strikes):
                    if attacker not in self.boards[turn_side] or attacker.health <= 0:
                        break
                    if not self.boards[opp_side]:
                        break
                    target_idx = self._choose_target_index(opp_side)
                    if target_idx is None:
                        break

                    attacker.shroud_broken = True
                    primary = self.boards[opp_side][target_idx]
                    targets = [primary]
                    if attacker.has_keyword(Keyword.SWEEP):
                        if target_idx - 1 >= 0:
                            targets.append(self.boards[opp_side][target_idx - 1])
                        if target_idx + 1 < len(self.boards[opp_side]):
                            targets.append(self.boards[opp_side][target_idx + 1])

                    self._emit(
                        "ATTACK",
                        turn_side,
                        source_id=attacker.instance_id,
                        target_id=primary.instance_id,
                        value=attacker.attack,
                        description=f"{attacker.name} ({attacker.attack}/{attacker.health}) strikes {primary.name} ({primary.attack}/{primary.health}).",
                    )

                    for t in targets:
                        self._deal_strike_damage(attacker, t, turn_side, opp_side)
                    self._deal_strike_damage(primary, attacker, opp_side, turn_side)
                    self._cleanup_deaths()

            turn_side = opp_side

        p_alive = self.boards["player"]
        o_alive = self.boards["opponent"]
        if p_alive and not o_alive:
            dmg = self.tiers["player"] + sum(u.tier for u in p_alive)
            self._emit("RESULT", "player", value=dmg, description=f"Player won, dealing {dmg} damage.")
            return CombatOutcome("player", dmg, p_alive, o_alive, self.events)
        if o_alive and not p_alive:
            dmg = self.tiers["opponent"] + sum(u.tier for u in o_alive)
            self._emit("RESULT", "opponent", value=dmg, description=f"Opponent won, dealing {dmg} damage.")
            return CombatOutcome("opponent", dmg, p_alive, o_alive, self.events)

        self._emit("RESULT", "tie", value=0, description="Combat ended in a draw.")
        return CombatOutcome("tie", 0, p_alive, o_alive, self.events)


def resolve_combat(
    player_board: list[UnitInstance],
    opponent_board: list[UnitInstance],
    *,
    player_tier: int,
    opponent_tier: int,
    player_relics: list[str] | None = None,
    opponent_relics: list[str] | None = None,
    rng: SeededRNG | None = None,
) -> CombatOutcome:
    """Resolve one deterministic round combat between two warbands."""
    runner = _CombatRunner(
        player_board,
        opponent_board,
        player_tier=player_tier,
        opponent_tier=opponent_tier,
        player_relics=player_relics or [],
        opponent_relics=opponent_relics or [],
        rng=rng or SeededRNG(),
    )
    return runner.run()
