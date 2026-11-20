"""Shared Conclave unit pool, shop actions, Ascension fusion, and Arcane Edicts."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.core.enums import HandCardKind, Keyword
from src.core.rng import SeededRNG
from src.data.edicts_and_relics import ARCANE_EDICTS
from src.data.units import (
    TIER_POOL_COPIES,
    UNIT_CATALOG,
    UnitEffectSpec,
    get_recruitable_units,
)
from src.entities.commander import (
    BASTION_UPGRADE_BASE_COST,
    CONCLAVE_SHOP_SLOTS,
    CommanderState,
)
from src.entities.unit import HandCard, UnitInstance
from src.entities.warband import MAX_WARBAND_SIZE


@dataclass
class ShopActionResult:
    """Structured result returned by every recruitment-phase action."""

    ok: bool
    message: str
    ascended_unit: UnitInstance | None = None
    oracle_triggered: bool = False


class UnitPool:
    """Shared lobby unit pool with per-tier scarcity."""

    def __init__(self, active_tribes: tuple[str, ...], rng: SeededRNG) -> None:
        self.active_tribes = active_tribes
        self.rng = rng
        self.counts: dict[str, int] = {}
        for defn in get_recruitable_units(active_tribes):
            self.counts[defn.id] = TIER_POOL_COPIES[defn.tier]

    def available_unit_ids(self, max_tier: int, exact_tier: int | None = None) -> list[str]:
        pool: list[str] = []
        for uid, remaining in self.counts.items():
            if remaining <= 0:
                continue
            tier = UNIT_CATALOG[uid].tier
            if exact_tier is not None:
                if tier == exact_tier:
                    pool.extend([uid] * remaining)
            elif tier <= max_tier:
                pool.extend([uid] * remaining)
        return pool

    def draw(self, max_tier: int, count: int, *, exact_tier: int | None = None) -> list[str]:
        drawn: list[str] = []
        for _ in range(count):
            candidates = self.available_unit_ids(max_tier, exact_tier=exact_tier)
            if not candidates:
                break
            uid = self.rng.choice(candidates)
            self.counts[uid] -= 1
            drawn.append(uid)
        return drawn

    def draw_distinct_choices(self, exact_tier: int, count: int = 3) -> list[str]:
        """Draw up to `count` distinct unit IDs of `exact_tier` for Discover / Oracle."""
        available = [
            uid
            for uid, remaining in self.counts.items()
            if remaining > 0 and UNIT_CATALOG[uid].tier == exact_tier
        ]
        if len(available) < count:
            available = [
                uid
                for uid, remaining in self.counts.items()
                if remaining > 0 and UNIT_CATALOG[uid].tier <= exact_tier
            ]
        if not available:
            return []
        self.rng.shuffle(available)
        chosen = available[: min(count, len(available))]
        for uid in chosen:
            self.counts[uid] = max(0, self.counts[uid] - 1)
        return chosen

    def return_unit(self, unit_id: str, copies: int = 1) -> None:
        if unit_id in self.counts:
            cap = TIER_POOL_COPIES[UNIT_CATALOG[unit_id].tier]
            self.counts[unit_id] = min(cap, self.counts[unit_id] + copies)


@dataclass
class ConclaveShopService:
    """Executes player and AI recruitment actions cleanly and deterministically."""

    pool: UnitPool
    rng: SeededRNG
    active_tribes: tuple[str, ...]
    _seq: int = field(default=0)

    def _next_id(self, prefix: str) -> str:
        self._seq += 1
        return f"{prefix}_{self._seq}"

    def _make_unit(self, unit_id: str, *, is_ascended: bool = False) -> UnitInstance:
        return UnitInstance.from_definition(
            UNIT_CATALOG[unit_id],
            self._next_id("u"),
            is_ascended=is_ascended,
        )

    def _random_edict_id(self, max_tier: int) -> str:
        eligible = [eid for eid, ed in ARCANE_EDICTS.items() if ed.tier <= max_tier]
        if not eligible:
            eligible = list(ARCANE_EDICTS.keys())
        return self.rng.choice(eligible)

    def populate_shop(self, commander: CommanderState, *, preserve_frozen: bool = False) -> None:
        """Populate shop units and 1 Arcane Edict; respects Frozen Conclave at round start."""
        if preserve_frozen and commander.shop_frozen and commander.shop_units:
            commander.shop_frozen = False
            if commander.shop_edict_id is None:
                commander.shop_edict_id = self._random_edict_id(commander.bastion_tier)
                commander.shop_edict_cost_override = None
            return

        # Return existing unbought shop units to shared pool
        for existing in commander.shop_units:
            self.pool.return_unit(existing.unit_id, 1)
        commander.shop_units.clear()
        commander.shop_frozen = False

        slot_count = CONCLAVE_SHOP_SLOTS[commander.bastion_tier]
        drawn_ids = self.pool.draw(commander.bastion_tier, slot_count)
        for uid in drawn_ids:
            unit = self._make_unit(uid)
            if commander.has_relic("astral_astrolabe"):
                unit.apply_buff(1, 1)
            commander.shop_units.append(unit)

        commander.shop_edict_id = self._random_edict_id(commander.bastion_tier)
        commander.shop_edict_cost_override = None

    def refresh_shop(self, commander: CommanderState, *, ignore_cost: bool = False) -> ShopActionResult:
        if ignore_cost or commander.free_refreshes > 0:
            if not ignore_cost and commander.free_refreshes > 0:
                commander.free_refreshes -= 1
            cost = 0
        else:
            cost = 1
            if commander.crowns < cost:
                return ShopActionResult(False, "Not enough Aether Crowns to refresh.")
            commander.crowns -= cost

        self.populate_shop(commander, preserve_frozen=False)
        return ShopActionResult(True, "Conclave refreshed.")

    def toggle_freeze(self, commander: CommanderState) -> ShopActionResult:
        commander.shop_frozen = not commander.shop_frozen
        state = "sealed" if commander.shop_frozen else "unsealed"
        return ShopActionResult(True, f"Conclave {state}.")

    def elevate_bastion(self, commander: CommanderState) -> ShopActionResult:
        if commander.bastion_tier >= 6:
            return ShopActionResult(False, "Bastion is already at Tier VI.")
        if commander.crowns < commander.upgrade_cost:
            return ShopActionResult(False, "Not enough Aether Crowns to elevate Bastion.")
        commander.crowns -= commander.upgrade_cost
        commander.bastion_tier += 1
        commander.upgrade_cost = BASTION_UPGRADE_BASE_COST.get(commander.bastion_tier, 0)
        return ShopActionResult(True, f"Bastion elevated to Tier {commander.bastion_tier}.")

    def recruit_unit(self, commander: CommanderState, shop_index: int) -> ShopActionResult:
        if shop_index < 0 or shop_index >= len(commander.shop_units):
            return ShopActionResult(False, "Invalid Conclave slot.")
        if commander.crowns < 3:
            return ShopActionResult(False, "Recruiting a unit costs 3 Aether Crowns.")

        candidate = commander.shop_units[shop_index]
        # Allow recruitment even with full hand ONLY if this completes a 3-copy Ascension fusion
        will_triple = commander.warband.count_non_ascended(candidate.unit_id) >= 2
        if commander.warband.is_hand_full and not will_triple:
            return ShopActionResult(False, "Your hand is full (max 10 cards).")

        commander.crowns -= 3
        unit = commander.shop_units.pop(shop_index)
        card = HandCard(
            card_id=self._next_id("card"),
            kind=HandCardKind.UNIT,
            title=unit.name,
            unit=unit,
        )
        commander.warband.hand.append(card)

        ascended = commander.warband.check_and_fuse_ascension(
            unit.unit_id,
            new_instance_id=self._next_id("asc"),
            oracle_card_id=self._next_id("oracle"),
            current_bastion_tier=commander.bastion_tier,
        )
        if ascended is not None:
            return ShopActionResult(
                True,
                f"Ascension! 3x {unit.name} fused into {ascended.name} + Ascension Oracle!",
                ascended_unit=ascended,
            )
        return ShopActionResult(True, f"Recruited {unit.name}.")

    def dismiss_unit(self, commander: CommanderState, board_index: int) -> ShopActionResult:
        if board_index < 0 or board_index >= len(commander.warband.board):
            return ShopActionResult(False, "Invalid warband slot.")
        unit = commander.warband.board.pop(board_index)
        if not unit.is_token:
            copies = 3 if unit.is_ascended else 1
            self.pool.return_unit(unit.unit_id, copies=copies)
        commander.crowns += 1
        return ShopActionResult(True, f"Dismissed {unit.name} (+1 Crown).")

    def _add_blood_shards(self, commander: CommanderState, count: int) -> None:
        for _ in range(count):
            if commander.warband.is_hand_full:
                break
            commander.warband.hand.append(
                HandCard(
                    card_id=self._next_id("shard"),
                    kind=HandCardKind.BLOOD_SHARD,
                    title="Blood Shard (+1/+1)",
                )
            )

    def _add_forge_plating(self, commander: CommanderState) -> None:
        if not commander.warband.is_hand_full:
            commander.warband.hand.append(
                HandCard(
                    card_id=self._next_id("plate"),
                    kind=HandCardKind.FORGE_PLATING,
                    title="Forge Plating (+2/+2 & Aegis)",
                )
            )

    def _add_edict_card(self, commander: CommanderState, edict_id: str) -> None:
        if not commander.warband.is_hand_full:
            edict = ARCANE_EDICTS[edict_id]
            commander.warband.hand.append(
                HandCard(
                    card_id=self._next_id("edict"),
                    kind=HandCardKind.ARCANE_EDICT,
                    title=edict.name,
                    edict_id=edict_id,
                )
            )

    def _apply_vow_effect(
        self,
        commander: CommanderState,
        source: UnitInstance,
        spec: UnitEffectSpec,
        target_board_index: int | None = None,
    ) -> None:
        mult = source.effect_multiplier
        allies = [u for u in commander.warband.board if u.instance_id != source.instance_id]
        if spec.target_tribe:
            allies = [u for u in allies if u.tribe == spec.target_tribe]

        if spec.kind == "buff_random_ally":
            target: UnitInstance | None = None
            if target_board_index is not None and 0 <= target_board_index < len(commander.warband.board):
                cand = commander.warband.board[target_board_index]
                if cand.instance_id != source.instance_id and (
                    spec.target_tribe is None or cand.tribe == spec.target_tribe
                ):
                    target = cand
            if target is None and allies:
                target = self.rng.choice(allies)
            if target is not None:
                target.apply_buff(spec.attack_delta * mult, spec.health_delta * mult)
                if spec.grant_keyword is not None:
                    target.add_keyword(spec.grant_keyword)
        elif spec.kind == "buff_all_allies":
            for u in commander.warband.board:
                if spec.target_tribe is None or u.tribe == spec.target_tribe:
                    u.apply_buff(spec.attack_delta * mult, spec.health_delta * mult)
        elif spec.kind == "self_pact":
            commander.apply_damage(spec.damage)
            source.apply_buff(spec.attack_delta * mult, spec.health_delta * mult)
        elif spec.kind == "add_edict":
            for _ in range(spec.count * mult):
                self._add_edict_card(commander, self._random_edict_id(commander.bastion_tier))
        elif spec.kind == "add_blood_shards":
            self._add_blood_shards(commander, spec.count * mult)
        elif spec.kind == "gain_crowns":
            commander.crowns += spec.count * mult
        elif spec.kind == "crimson_awakening":
            self._add_blood_shards(commander, spec.count * mult)
            for u in commander.warband.board:
                if u.instance_id != source.instance_id:
                    u.apply_buff(spec.attack_delta * mult, spec.health_delta * mult)
        elif spec.kind == "empower_conclave":
            commander.free_refreshes += spec.count * mult
            for u in commander.shop_units:
                u.apply_buff(spec.attack_delta * mult, spec.health_delta * mult)
        elif spec.kind == "menagerie_buff":
            by_tribe: dict[str, list[UnitInstance]] = {}
            for u in commander.warband.board:
                if u.instance_id != source.instance_id:
                    by_tribe.setdefault(u.tribe, []).append(u)
            for group in by_tribe.values():
                chosen = self.rng.choice(group)
                chosen.apply_buff(spec.attack_delta * mult, spec.health_delta * mult)

    def _trigger_edict_synergies(self, commander: CommanderState) -> None:
        for u in commander.warband.board:
            spec = u.definition.on_edict_cast
            if spec is not None:
                mult = u.effect_multiplier
                u.apply_buff(spec.attack_delta * mult, spec.health_delta * mult)
        if commander.commander_id == "rachel" and commander.warband.board:
            ally = self.rng.choice(commander.warband.board)
            ally.apply_buff(1, 1)

    def _resolve_edict_effect(self, commander: CommanderState, edict_id: str) -> str:
        edict = ARCANE_EDICTS[edict_id]
        board = commander.warband.board
        if edict.effect_kind == "buff_random_ally" and board:
            self.rng.choice(board).apply_buff(edict.attack_delta, edict.health_delta)
        elif edict.effect_kind == "add_blood_shards":
            self._add_blood_shards(commander, edict.count)
        elif edict.effect_kind == "increase_max_crowns":
            commander.bonus_max_crowns += edict.crowns_delta
            commander.max_crowns = min(13, commander.max_crowns + edict.crowns_delta)
            commander.crowns += edict.crowns_delta
        elif edict.effect_kind == "buff_vanguard" and board:
            target = self.rng.choice(board)
            target.apply_buff(edict.attack_delta, edict.health_delta)
            target.add_keyword(Keyword.VANGUARD)
        elif edict.effect_kind == "recruit_random_tier":
            drawn = self.pool.draw(commander.bastion_tier, 1, exact_tier=commander.bastion_tier)
            if not drawn:
                drawn = self.pool.draw(commander.bastion_tier, 1)
            if drawn and not commander.warband.is_hand_full:
                u = self._make_unit(drawn[0])
                commander.warband.hand.append(
                    HandCard(
                        card_id=self._next_id("card"),
                        kind=HandCardKind.UNIT,
                        title=u.name,
                        unit=u,
                    )
                )
        elif edict.effect_kind == "buff_all_allies":
            for u in board:
                u.apply_buff(edict.attack_delta, edict.health_delta)
        elif edict.effect_kind == "grant_aegis":
            no_aegis = [u for u in board if not u.has_keyword(Keyword.AEGIS)]
            target = self.rng.choice(no_aegis or board) if board else None
            if target is not None:
                target.add_keyword(Keyword.AEGIS)
                target.apply_buff(edict.attack_delta, edict.health_delta)
        elif edict.effect_kind == "grant_undying":
            no_undying = [u for u in board if not u.has_keyword(Keyword.UNDYING)]
            target = self.rng.choice(no_undying or board) if board else None
            if target is not None:
                target.add_keyword(Keyword.UNDYING)
        elif edict.effect_kind == "buff_shop":
            commander.free_refreshes += 1
            for u in commander.shop_units:
                u.apply_buff(edict.attack_delta, edict.health_delta)
        elif edict.effect_kind == "crowns_and_shards":
            commander.crowns += edict.crowns_delta
            self._add_blood_shards(commander, edict.count)
        elif edict.effect_kind == "add_oracle":
            if not commander.warband.is_hand_full:
                tier = min(6, commander.bastion_tier + 1)
                commander.warband.hand.append(
                    HandCard(
                        card_id=self._next_id("oracle"),
                        kind=HandCardKind.ASCENSION_ORACLE,
                        title=f"Ascension Oracle (Tier {tier})",
                        discover_tier=tier,
                    )
                )

        self._trigger_edict_synergies(commander)
        return f"Cast Arcane Edict: {edict.name}."

    def buy_shop_edict(self, commander: CommanderState) -> ShopActionResult:
        if commander.shop_edict_id is None:
            return ShopActionResult(False, "No Arcane Edict available in the Conclave.")
        edict = ARCANE_EDICTS[commander.shop_edict_id]
        base_cost = (
            commander.shop_edict_cost_override
            if commander.shop_edict_cost_override is not None
            else edict.crown_cost
        )
        discount = 1 if commander.commander_id == "rachel" else 0
        cost = max(0, base_cost - discount)
        if commander.crowns < cost:
            return ShopActionResult(False, f"{edict.name} costs {cost} Crowns.")
        commander.crowns -= cost
        edict_id = commander.shop_edict_id
        commander.shop_edict_id = None
        commander.shop_edict_cost_override = None
        msg = self._resolve_edict_effect(commander, edict_id)
        return ShopActionResult(True, msg)

    def play_hand_card(
        self,
        commander: CommanderState,
        hand_index: int,
        *,
        insert_index: int | None = None,
        target_board_index: int | None = None,
    ) -> ShopActionResult:
        if hand_index < 0 or hand_index >= len(commander.warband.hand):
            return ShopActionResult(False, "Invalid hand slot.")
        card = commander.warband.hand[hand_index]

        if card.kind == HandCardKind.UNIT:
            if card.unit is None:
                return ShopActionResult(False, "Missing unit data on card.")
            if commander.warband.is_board_full:
                return ShopActionResult(False, f"Warband is full (max {MAX_WARBAND_SIZE} units).")
            commander.warband.hand.pop(hand_index)
            unit = card.unit
            pos = (
                len(commander.warband.board)
                if insert_index is None
                else max(0, min(len(commander.warband.board), insert_index))
            )
            commander.warband.board.insert(pos, unit)
            if unit.definition.vow is not None:
                self._apply_vow_effect(
                    commander, unit, unit.definition.vow, target_board_index=target_board_index
                )
            return ShopActionResult(True, f"Deployed {unit.name}.")

        if card.kind == HandCardKind.BLOOD_SHARD:
            if not commander.warband.board:
                return ShopActionResult(False, "No units on warband to receive Blood Shard.")
            idx = (
                target_board_index
                if target_board_index is not None and 0 <= target_board_index < len(commander.warband.board)
                else 0
            )
            target = commander.warband.board[idx]
            commander.warband.hand.pop(hand_index)
            target.apply_buff(1, 1)
            if target.definition.on_shard_applied is not None:
                spec = target.definition.on_shard_applied
                mult = target.effect_multiplier
                target.apply_buff(spec.attack_delta * mult, spec.health_delta * mult)
            return ShopActionResult(True, f"Applied Blood Shard (+1/+1) to {target.name}.")

        if card.kind == HandCardKind.FORGE_PLATING:
            if not commander.warband.board:
                return ShopActionResult(False, "No units on warband to receive Forge Plating.")
            idx = (
                target_board_index
                if target_board_index is not None and 0 <= target_board_index < len(commander.warband.board)
                else 0
            )
            target = commander.warband.board[idx]
            commander.warband.hand.pop(hand_index)
            target.apply_buff(2, 2)
            target.add_keyword(Keyword.AEGIS)
            return ShopActionResult(True, f"Applied Forge Plating (+2/+2 & Aegis) to {target.name}.")

        if card.kind == HandCardKind.ARCANE_EDICT:
            if card.edict_id is None:
                return ShopActionResult(False, "Invalid Arcane Edict card.")
            commander.warband.hand.pop(hand_index)
            msg = self._resolve_edict_effect(commander, card.edict_id)
            return ShopActionResult(True, msg)

        if card.kind == HandCardKind.ASCENSION_ORACLE:
            if commander.pending_oracle_choices:
                return ShopActionResult(False, "Resolve current Ascension Oracle first.")
            commander.warband.hand.pop(hand_index)
            option_ids = self.pool.draw_distinct_choices(card.discover_tier, count=3)
            if not option_ids:
                return ShopActionResult(False, "No units remaining in the Conclave pool.")
            commander.pending_oracle_choices = [self._make_unit(uid) for uid in option_ids]
            return ShopActionResult(
                True,
                f"Ascension Oracle opened (Tier {card.discover_tier}).",
                oracle_triggered=True,
            )

        return ShopActionResult(False, "Unsupported card kind.")

    def pick_oracle_choice(self, commander: CommanderState, choice_index: int) -> ShopActionResult:
        if not commander.pending_oracle_choices:
            return ShopActionResult(False, "No pending Ascension Oracle choices.")
        if choice_index < 0 or choice_index >= len(commander.pending_oracle_choices):
            return ShopActionResult(False, "Invalid Oracle choice.")

        chosen = commander.pending_oracle_choices.pop(choice_index)
        for leftover in commander.pending_oracle_choices:
            self.pool.return_unit(leftover.unit_id, 1)
        commander.pending_oracle_choices.clear()

        if not commander.warband.is_hand_full or commander.warband.count_non_ascended(chosen.unit_id) >= 2:
            commander.warband.hand.append(
                HandCard(
                    card_id=self._next_id("card"),
                    kind=HandCardKind.UNIT,
                    title=chosen.name,
                    unit=chosen,
                )
            )
            ascended = commander.warband.check_and_fuse_ascension(
                chosen.unit_id,
                new_instance_id=self._next_id("asc"),
                oracle_card_id=self._next_id("oracle"),
                current_bastion_tier=commander.bastion_tier,
            )
            if ascended is not None:
                return ShopActionResult(
                    True,
                    f"Oracle discovered {chosen.name} -> Triple Ascension into {ascended.name}!",
                    ascended_unit=ascended,
                )
            return ShopActionResult(True, f"Oracle discovered {chosen.name}.")

        self.pool.return_unit(chosen.unit_id, 1)
        return ShopActionResult(False, "Hand full; Oracle choice returned to Conclave pool.")

    def use_commander_mandate(
        self,
        commander: CommanderState,
        *,
        target_board_index: int | None = None,
    ) -> ShopActionResult:
        defn = commander.definition
        if defn.is_passive:
            return ShopActionResult(False, f"{defn.mandate_name} is a passive mandate.")
        if commander.mandate_used_this_round:
            return ShopActionResult(False, "Commander's Mandate already used this round.")
        if commander.crowns < defn.mandate_cost:
            return ShopActionResult(False, f"{defn.mandate_name} costs {defn.mandate_cost} Crowns.")

        board = commander.warband.board
        if commander.commander_id in {"rowan", "lyra", "caelen", "valora"} and not board:
            return ShopActionResult(False, "Deploy at least one unit before activating this Mandate.")

        def _pick_target() -> UnitInstance | None:
            if not board:
                return None
            if target_board_index is not None and 0 <= target_board_index < len(board):
                return board[target_board_index]
            return self.rng.choice(board)

        if commander.commander_id == "carmilla":
            if commander.health <= 1:
                return ShopActionResult(False, "Not enough Health for Sanguine Tithe.")
            commander.health -= 1
            commander.crowns += 1
            self._add_blood_shards(commander, 2)
            commander.mandate_used_this_round = True
            return ShopActionResult(True, "Sanguine Tithe: Paid 1 Health for +1 Crown & 2 Blood Shards.")

        commander.crowns -= defn.mandate_cost
        commander.mandate_used_this_round = True

        if commander.commander_id == "rowan":
            t = _pick_target()
            if t is not None:
                t.apply_buff(1, 2)
                t.add_keyword(Keyword.VANGUARD)
                return ShopActionResult(True, f"Solar Bulwark empowered {t.name} (+1/+2 & Vanguard).")

        if commander.commander_id == "rachel":
            self._add_edict_card(commander, self._random_edict_id(commander.bastion_tier))
            t = _pick_target()
            if t is not None:
                t.apply_buff(1, 1)
            return ShopActionResult(True, "Violet Ember conjured an Arcane Edict.")

        if commander.commander_id == "lyra":
            t = _pick_target()
            if t is not None:
                bonus = 3 if t.tribe == "sylvan" else 2
                t.apply_buff(bonus, bonus)
                return ShopActionResult(True, f"Root Symbiosis gave {t.name} +{bonus}/+{bonus}.")

        if commander.commander_id == "caelen":
            t = _pick_target()
            if t is not None:
                t.apply_buff(3, 0)
                t.add_keyword(Keyword.SHROUD)
                return ShopActionResult(True, f"Ambush Ledger granted {t.name} +3 ATK & Shroud.")

        if commander.commander_id == "valora":
            t = _pick_target()
            if t is not None:
                t.apply_buff(2, 0)
                t.add_keyword(Keyword.AEGIS)
                return ShopActionResult(True, f"Judgment Aegis shielded {t.name} (+2 ATK & Aegis).")

        return ShopActionResult(False, "Mandate could not be resolved.")
