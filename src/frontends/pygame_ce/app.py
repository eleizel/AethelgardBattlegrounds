"""Playable 1280x720 Pygame-CE client for Aethelgard: Conclave of War."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pygame

from src.core.enums import GamePhase, HandCardKind, Keyword
from src.core.rng import SeededRNG
from src.data.commanders import COMMANDER_CATALOG
from src.data.edicts_and_relics import ARCANE_EDICTS, DAWN_RELICS
from src.data.tribes import TRIBE_REGISTRY
from src.entities.unit import UnitInstance
from src.systems.lobby_manager import LobbyManager

WINDOW_W = 1280
WINDOW_H = 720
BG_COLOR = (16, 14, 22)
PANEL_BG = (28, 24, 38)
PANEL_ALT = (38, 32, 52)
GOLD = (218, 174, 72)
TEXT_LIGHT = (242, 236, 224)
TEXT_MUTED = (168, 160, 184)
CRIMSON = (196, 56, 68)
AETHER_CYAN = (68, 198, 236)
EMERALD = (68, 186, 108)


@dataclass
class ClickTarget:
    rect: pygame.Rect
    action: str
    index: int = -1


class PygameConclaveApp:
    """Interactive 1280x720 Pygame-CE desktop client backed by LobbyManager."""

    def __init__(self, assets_dir: Path, seed: int | None = None) -> None:
        self.assets_dir = assets_dir
        self.seed = seed
        self.lobby = LobbyManager(rng=SeededRNG(seed))
        self.status_banner = "Select your Commander to enter the War Conclave."
        self.selected_board_index: int | None = None
        self.combat_log_lines: list[str] = []
        self._image_cache: dict[str, pygame.Surface] = {}
        self._click_targets: list[ClickTarget] = []

    def _load_image(self, rel_path: str, size: tuple[int, int]) -> pygame.Surface | None:
        key = f"{rel_path}:{size[0]}x{size[1]}"
        if key in self._image_cache:
            return self._image_cache[key]
        full = self.assets_dir / rel_path
        if not full.is_file():
            return None
        try:
            surf = pygame.image.load(str(full)).convert_alpha()
            scaled = pygame.transform.smoothscale(surf, size)
            self._image_cache[key] = scaled
            return scaled
        except pygame.error:
            return None

    def _draw_unit_card(
        self,
        screen: pygame.Surface,
        unit: UnitInstance,
        rect: pygame.Rect,
        font_sm: pygame.font.Font,
        font_xs: pygame.font.Font,
        *,
        selected: bool = False,
        action_name: str = "",
        action_index: int = -1,
    ) -> None:
        border_col = GOLD if unit.is_ascended else (AETHER_CYAN if selected else (112, 96, 132))
        fill_col = (54, 42, 22) if unit.is_ascended else PANEL_ALT
        pygame.draw.rect(screen, fill_col, rect, border_radius=8)
        pygame.draw.rect(screen, border_col, rect, width=3 if selected or unit.is_ascended else 2, border_radius=8)

        sprite = self._load_image(f"sprites/units/{unit.definition.sprite_filename}", (56, 56))
        if sprite is not None:
            screen.blit(sprite, (rect.centerx - 28, rect.y + 18))

        tier_txt = font_xs.render(f"T{unit.tier}", True, GOLD)
        screen.blit(tier_txt, (rect.x + 6, rect.y + 4))

        tribe_def = TRIBE_REGISTRY[unit.tribe]
        tribe_txt = font_xs.render(tribe_def.name[:8], True, TEXT_MUTED)
        screen.blit(tribe_txt, (rect.right - tribe_txt.get_width() - 6, rect.y + 4))

        name_txt = font_xs.render(unit.name[:15], True, TEXT_LIGHT)
        screen.blit(name_txt, (rect.centerx - name_txt.get_width() // 2, rect.y + 76))

        kw_codes = []
        for kw in sorted(unit.keywords, key=lambda k: k.value):
            if kw == Keyword.AEGIS:
                kw_codes.append("AEG")
            elif kw == Keyword.VANGUARD:
                kw_codes.append("VAN")
            elif kw == Keyword.BLIGHT:
                kw_codes.append("BLI")
            elif kw == Keyword.FRENZY:
                kw_codes.append("FRZ")
            elif kw == Keyword.UNDYING:
                kw_codes.append("UND")
            elif kw == Keyword.SWEEP:
                kw_codes.append("SWP")
            elif kw == Keyword.SHROUD:
                kw_codes.append("SHR")
            elif kw == Keyword.RETRIBUTION:
                kw_codes.append("RET")
        kw_str = " ".join(kw_codes[:3])
        if kw_str:
            kw_txt = font_xs.render(kw_str, True, AETHER_CYAN)
            screen.blit(kw_txt, (rect.centerx - kw_txt.get_width() // 2, rect.y + 92))

        atk_badge = pygame.Rect(rect.x + 6, rect.bottom - 26, 30, 20)
        hp_badge = pygame.Rect(rect.right - 36, rect.bottom - 26, 30, 20)
        pygame.draw.rect(screen, (165, 92, 24), atk_badge, border_radius=4)
        pygame.draw.rect(screen, (158, 34, 48), hp_badge, border_radius=4)
        atk_txt = font_sm.render(str(unit.attack), True, TEXT_LIGHT)
        hp_txt = font_sm.render(str(unit.health), True, TEXT_LIGHT)
        screen.blit(atk_txt, (atk_badge.centerx - atk_txt.get_width() // 2, atk_badge.y + 1))
        screen.blit(hp_txt, (hp_badge.centerx - hp_txt.get_width() // 2, hp_badge.y + 1))

        if action_name:
            self._click_targets.append(ClickTarget(rect, action_name, action_index))

    def _handle_click(self, pos: tuple[int, int]) -> None:
        for target in reversed(self._click_targets):
            if target.rect.collidepoint(pos):
                self._dispatch_action(target.action, target.index)
                return

    def _dispatch_action(self, action: str, index: int) -> None:
        if action == "pick_commander":
            cid = self.lobby.commander_choices[index]
            self.lobby.select_human_commander(cid)
            self.status_banner = "Round 1 — Recruit your opening warband!"
        elif action == "pick_relic":
            rid = self.lobby.pick_human_relic(index)
            self.status_banner = f"Dawn Relic claimed: {DAWN_RELICS[rid].name}."
        elif action == "pick_oracle":
            assert self.lobby.shop is not None
            res = self.lobby.shop.pick_oracle_choice(self.lobby.human, index)
            self.status_banner = res.message
        elif action == "buy_unit":
            assert self.lobby.shop is not None
            res = self.lobby.shop.recruit_unit(self.lobby.human, index)
            self.status_banner = res.message
        elif action == "buy_edict":
            assert self.lobby.shop is not None
            res = self.lobby.shop.buy_shop_edict(self.lobby.human)
            self.status_banner = res.message
        elif action == "refresh":
            assert self.lobby.shop is not None
            res = self.lobby.shop.refresh_shop(self.lobby.human)
            self.status_banner = res.message
        elif action == "freeze":
            assert self.lobby.shop is not None
            res = self.lobby.shop.toggle_freeze(self.lobby.human)
            self.status_banner = res.message
        elif action == "elevate":
            assert self.lobby.shop is not None
            res = self.lobby.shop.elevate_bastion(self.lobby.human)
            self.status_banner = res.message
        elif action == "mandate":
            assert self.lobby.shop is not None
            res = self.lobby.shop.use_commander_mandate(
                self.lobby.human, target_board_index=self.selected_board_index
            )
            self.status_banner = res.message
        elif action == "select_board":
            if self.selected_board_index is None:
                self.selected_board_index = index
                u = self.lobby.human.warband.board[index]
                self.status_banner = f"Selected {u.name}. Click another slot to swap or Dismiss to sell."
            elif self.selected_board_index == index:
                self.selected_board_index = None
            else:
                self.lobby.human.warband.swap_positions(self.selected_board_index, index)
                self.selected_board_index = None
                self.status_banner = "Warband formation updated."
        elif action == "dismiss_selected":
            if self.selected_board_index is not None and self.lobby.shop is not None:
                res = self.lobby.shop.dismiss_unit(self.lobby.human, self.selected_board_index)
                self.selected_board_index = None
                self.status_banner = res.message
        elif action == "play_hand":
            assert self.lobby.shop is not None
            res = self.lobby.shop.play_hand_card(
                self.lobby.human, index, target_board_index=self.selected_board_index
            )
            self.status_banner = res.message
        elif action == "start_combat":
            self.selected_board_index = None
            outcome = self.lobby.start_combat_phase()
            if outcome is not None:
                self.combat_log_lines = [ev.description for ev in outcome.events[-8:] if ev.description]
                if outcome.winner_side == "player":
                    self.status_banner = f"Victory! Dealt {outcome.damage_to_loser} damage to opponent."
                elif outcome.winner_side == "opponent":
                    self.status_banner = f"Defeat! Took {outcome.damage_to_loser} damage."
                else:
                    self.status_banner = "Stalemate! Neither Commander took damage."
            if self.lobby.phase != GamePhase.GAME_OVER:
                self.lobby.advance_to_next_round()
        elif action == "new_run":
            self.lobby = LobbyManager(rng=SeededRNG())
            self.selected_board_index = None
            self.combat_log_lines.clear()
            self.status_banner = "Select your Commander for a new War Conclave."

    def run(self) -> int:
        pygame.init()
        pygame.display.set_caption("Aethelgard: Conclave of War")
        screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        clock = pygame.time.Clock()

        font_path = self.assets_dir / "fonts" / "CinzelDecorative-Bold.ttf"
        if font_path.is_file():
            font_lg = pygame.font.Font(str(font_path), 24)
            font_md = pygame.font.Font(str(font_path), 16)
        else:
            font_lg = pygame.font.SysFont("georgia", 24, bold=True)
            font_md = pygame.font.SysFont("georgia", 16, bold=True)
        font_sm = pygame.font.SysFont("consolas", 15, bold=True)
        font_xs = pygame.font.SysFont("consolas", 12)

        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self._handle_click(event.pos)

            self._click_targets.clear()
            screen.fill(BG_COLOR)

            if self.lobby.phase == GamePhase.COMMANDER_SELECT:
                self._render_commander_select(screen, font_lg, font_md, font_sm, font_xs)
            elif self.lobby.phase == GamePhase.GAME_OVER:
                self._render_game_over(screen, font_lg, font_md, font_sm)
            else:
                self._render_conclave(screen, font_lg, font_md, font_sm, font_xs)

            pygame.display.flip()
            clock.tick(60)

        pygame.quit()
        return 0

    def _render_commander_select(
        self,
        screen: pygame.Surface,
        font_lg: pygame.font.Font,
        font_md: pygame.font.Font,
        font_sm: pygame.font.Font,
        font_xs: pygame.font.Font,
    ) -> None:
        title = font_lg.render("AETHELGARD: CONCLAVE OF WAR", True, GOLD)
        screen.blit(title, (WINDOW_W // 2 - title.get_width() // 2, 34))

        active_names = ", ".join(TRIBE_REGISTRY[t].name for t in self.lobby.active_tribes if t != "mercenary")
        exiled_name = TRIBE_REGISTRY[self.lobby.exiled_tribe].name
        info = font_sm.render(f"Active Tribes: {active_names}  |  Exiled: {exiled_name}", True, TEXT_MUTED)
        screen.blit(info, (WINDOW_W // 2 - info.get_width() // 2, 80))

        for idx, cid in enumerate(self.lobby.commander_choices):
            defn = COMMANDER_CATALOG[cid]
            card = pygame.Rect(140 + idx * 345, 140, 310, 460)
            pygame.draw.rect(screen, PANEL_BG, card, border_radius=12)
            pygame.draw.rect(screen, GOLD, card, width=2, border_radius=12)

            portrait = self._load_image(f"portraits/{defn.portrait_filename}", (140, 140))
            if portrait is not None:
                screen.blit(portrait, (card.centerx - 70, card.y + 22))

            n_surf = font_md.render(defn.name, True, GOLD)
            screen.blit(n_surf, (card.centerx - n_surf.get_width() // 2, card.y + 178))
            t_surf = font_xs.render(defn.title, True, TEXT_MUTED)
            screen.blit(t_surf, (card.centerx - t_surf.get_width() // 2, card.y + 206))

            hp_surf = font_sm.render(f"HP: {defn.base_health}   Armor: {defn.starting_armor}", True, EMERALD)
            screen.blit(hp_surf, (card.centerx - hp_surf.get_width() // 2, card.y + 236))

            m_surf = font_sm.render(defn.mandate_name, True, AETHER_CYAN)
            screen.blit(m_surf, (card.centerx - m_surf.get_width() // 2, card.y + 275))

            # Simple wrap for mandate description
            words = defn.mandate_description.split()
            line = ""
            y_off = card.y + 305
            for w in words:
                test = f"{line} {w}".strip()
                if font_xs.size(test)[0] > 270:
                    s = font_xs.render(line, True, TEXT_LIGHT)
                    screen.blit(s, (card.x + 20, y_off))
                    y_off += 18
                    line = w
                else:
                    line = test
            if line:
                screen.blit(font_xs.render(line, True, TEXT_LIGHT), (card.x + 20, y_off))

            btn = pygame.Rect(card.x + 45, card.bottom - 62, 220, 42)
            pygame.draw.rect(screen, (92, 68, 22), btn, border_radius=8)
            pygame.draw.rect(screen, GOLD, btn, width=2, border_radius=8)
            b_txt = font_sm.render("CHOOSE COMMANDER", True, TEXT_LIGHT)
            screen.blit(b_txt, (btn.centerx - b_txt.get_width() // 2, btn.centery - 9))
            self._click_targets.append(ClickTarget(btn, "pick_commander", idx))

    def _render_conclave(
        self,
        screen: pygame.Surface,
        font_lg: pygame.font.Font,
        font_md: pygame.font.Font,
        font_sm: pygame.font.Font,
        font_xs: pygame.font.Font,
    ) -> None:
        human = self.lobby.human

        # Left sidebar: 8-Commander Leaderboard
        sidebar = pygame.Rect(12, 12, 240, WINDOW_H - 24)
        pygame.draw.rect(screen, PANEL_BG, sidebar, border_radius=10)
        pygame.draw.rect(screen, (88, 76, 110), sidebar, width=2, border_radius=10)
        screen.blit(font_md.render("CONCLAVE LOBBY", True, GOLD), (26, 22))
        screen.blit(
            font_xs.render(
                f"Round {self.lobby.round_number} | Exiled: {TRIBE_REGISTRY[self.lobby.exiled_tribe].name[:10]}",
                True,
                TEXT_MUTED,
            ),
            (26, 48),
        )

        opp, is_ghost = self.lobby.get_human_opponent()
        for row_idx, comm in enumerate(self.lobby.leaderboard()):
            row_r = pygame.Rect(22, 74 + row_idx * 68, 220, 60)
            is_opp = opp is not None and comm.slot_index == opp.slot_index
            bg = (48, 40, 74) if comm.is_human else ((68, 30, 38) if is_opp else PANEL_ALT)
            if comm.eliminated:
                bg = (24, 22, 30)
            pygame.draw.rect(screen, bg, row_r, border_radius=6)
            if comm.is_human or is_opp:
                pygame.draw.rect(screen, GOLD if comm.is_human else CRIMSON, row_r, width=2, border_radius=6)

            tag = "(YOU)" if comm.is_human else ("(NEXT)" if is_opp else ("(DEAD)" if comm.eliminated else ""))
            screen.blit(font_xs.render(f"{comm.name[:14]} {tag}", True, TEXT_LIGHT), (row_r.x + 8, row_r.y + 6))
            screen.blit(
                font_xs.render(f"HP {comm.health}+{comm.armor}  Tier {comm.bastion_tier}", True, GOLD if not comm.eliminated else TEXT_MUTED),
                (row_r.x + 8, row_r.y + 24),
            )
            if is_ghost and is_opp:
                screen.blit(font_xs.render("Fallen Spirit", True, AETHER_CYAN), (row_r.x + 8, row_r.y + 40))

        # Top Bar: Controls & Status
        top_r = pygame.Rect(264, 12, WINDOW_W - 276, 62)
        pygame.draw.rect(screen, PANEL_BG, top_r, border_radius=10)
        screen.blit(font_sm.render(self.status_banner[:88], True, TEXT_LIGHT), (278, 22))
        screen.blit(
            font_xs.render(
                f"Crowns: {human.crowns}/{human.max_crowns}   Bastion Tier {human.bastion_tier}   Units: {len(human.warband.board)}/7",
                True,
                GOLD,
            ),
            (278, 46),
        )

        # Action Buttons
        btn_specs = [
            ("elevate", f"Elevate ({human.upgrade_cost}g)" if human.bastion_tier < 6 else "Tier MAX", 760),
            ("refresh", "Refresh (Free)" if human.free_refreshes > 0 else "Refresh (1g)", 900),
            ("freeze", "Unseal" if human.shop_frozen else "Seal (0g)", 1030),
            ("start_combat", "COMBAT!", 1142),
        ]
        for act, label, bx in btn_specs:
            bw = 128 if act != "freeze" else 102
            r = pygame.Rect(bx, 22, bw, 40)
            col = CRIMSON if act == "start_combat" else (58, 48, 80)
            pygame.draw.rect(screen, col, r, border_radius=6)
            pygame.draw.rect(screen, GOLD, r, width=2, border_radius=6)
            t = font_xs.render(label, True, TEXT_LIGHT)
            screen.blit(t, (r.centerx - t.get_width() // 2, r.centery - 7))
            self._click_targets.append(ClickTarget(r, act))

        # Conclave Shop Row
        shop_r = pygame.Rect(264, 84, WINDOW_W - 276, 178)
        pygame.draw.rect(screen, PANEL_BG, shop_r, border_radius=10)
        screen.blit(font_sm.render("CONCLAVE OFFER (Click unit to Recruit - 3 Crowns)", True, GOLD), (278, 92))
        for i, unit in enumerate(human.shop_units):
            card_r = pygame.Rect(278 + i * 134, 118, 126, 134)
            self._draw_unit_card(screen, unit, card_r, font_sm, font_xs, action_name="buy_unit", action_index=i)

        if human.shop_edict_id is not None:
            edict = ARCANE_EDICTS[human.shop_edict_id]
            cost = max(0, edict.crown_cost - (1 if human.commander_id == "rachel" else 0))
            er = pygame.Rect(WINDOW_W - 182, 118, 156, 134)
            pygame.draw.rect(screen, (42, 28, 66), er, border_radius=8)
            pygame.draw.rect(screen, AETHER_CYAN, er, width=2, border_radius=8)
            screen.blit(font_xs.render("ARCANE EDICT", True, AETHER_CYAN), (er.x + 10, er.y + 8))
            screen.blit(font_xs.render(edict.name[:19], True, GOLD), (er.x + 10, er.y + 30))
            screen.blit(font_sm.render(f"Cost: {cost}g", True, TEXT_LIGHT), (er.x + 10, er.bottom - 28))
            self._click_targets.append(ClickTarget(er, "buy_edict"))

        # Warband Row (Your 7 units)
        board_r = pygame.Rect(264, 272, WINDOW_W - 276, 198)
        pygame.draw.rect(screen, PANEL_BG, board_r, border_radius=10)
        screen.blit(font_sm.render("YOUR WARBAND (Click to Select / Swap Position)", True, GOLD), (278, 280))
        if self.selected_board_index is not None:
            dismiss_r = pygame.Rect(WINDOW_W - 170, 278, 144, 28)
            pygame.draw.rect(screen, (112, 36, 42), dismiss_r, border_radius=6)
            pygame.draw.rect(screen, GOLD, dismiss_r, width=1, border_radius=6)
            dt = font_xs.render("DISMISS (+1g)", True, TEXT_LIGHT)
            screen.blit(dt, (dismiss_r.centerx - dt.get_width() // 2, dismiss_r.y + 7))
            self._click_targets.append(ClickTarget(dismiss_r, "dismiss_selected"))

        for i, unit in enumerate(human.warband.board):
            card_r = pygame.Rect(278 + i * 138, 314, 130, 144)
            self._draw_unit_card(
                screen,
                unit,
                card_r,
                font_sm,
                font_xs,
                selected=(self.selected_board_index == i),
                action_name="select_board",
                action_index=i,
            )

        # Bottom Bar: Commander Mandate + Hand Cards + Last Combat Log
        bot_r = pygame.Rect(264, 480, WINDOW_W - 276, 228)
        pygame.draw.rect(screen, PANEL_BG, bot_r, border_radius=10)

        defn = human.definition
        portrait = self._load_image(f"portraits/{human.portrait_filename}", (84, 84))
        if portrait is not None:
            screen.blit(portrait, (278, 494))
        screen.blit(font_sm.render(f"{human.name} ({human.health}+{human.armor})", True, GOLD), (372, 494))
        m_btn = pygame.Rect(372, 522, 230, 48)
        pygame.draw.rect(screen, (52, 42, 78) if not human.mandate_used_this_round else (32, 30, 40), m_btn, border_radius=6)
        pygame.draw.rect(screen, AETHER_CYAN, m_btn, width=2, border_radius=6)
        screen.blit(font_xs.render(f"Mandate: {defn.mandate_name} ({defn.mandate_cost}g)", True, TEXT_LIGHT), (m_btn.x + 8, m_btn.y + 6))
        screen.blit(font_xs.render(defn.mandate_description[:34], True, TEXT_MUTED), (m_btn.x + 8, m_btn.y + 26))
        if not defn.is_passive and not human.mandate_used_this_round:
            self._click_targets.append(ClickTarget(m_btn, "mandate"))

        # Hand row
        screen.blit(font_sm.render(f"HAND ({len(human.warband.hand)}/10) — Click card to Play", True, GOLD), (278, 586))
        for i, card in enumerate(human.warband.hand):
            hr = pygame.Rect(278 + i * 96, 612, 90, 86)
            pygame.draw.rect(screen, PANEL_ALT, hr, border_radius=6)
            pygame.draw.rect(screen, GOLD if card.kind == HandCardKind.ASCENSION_ORACLE else (120, 110, 148), hr, width=2, border_radius=6)
            if card.unit is not None:
                sp = self._load_image(f"sprites/units/{card.unit.definition.sprite_filename}", (40, 40))
                if sp is not None:
                    screen.blit(sp, (hr.centerx - 20, hr.y + 6))
                screen.blit(font_xs.render(card.unit.name[:11], True, TEXT_LIGHT), (hr.x + 5, hr.y + 48))
                screen.blit(font_xs.render(f"{card.unit.attack}/{card.unit.health}", True, GOLD), (hr.x + 5, hr.y + 65))
            else:
                screen.blit(font_xs.render(card.title[:11], True, AETHER_CYAN), (hr.x + 5, hr.y + 20))
                screen.blit(font_xs.render("PLAY", True, GOLD), (hr.x + 28, hr.y + 54))
            self._click_targets.append(ClickTarget(hr, "play_hand", i))

        # Modal Overlay for Dawn Relics or Ascension Oracle
        if self.lobby.phase == GamePhase.RELIC_SELECT and human.pending_relic_choices:
            overlay = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)
            overlay.fill((8, 6, 14, 210))
            screen.blit(overlay, (0, 0))
            title = font_lg.render("CHOOSE A DAWN RELIC", True, GOLD)
            screen.blit(title, (WINDOW_W // 2 - title.get_width() // 2, 120))
            for idx, rid in enumerate(human.pending_relic_choices):
                relic = DAWN_RELICS[rid]
                rr = pygame.Rect(160 + idx * 330, 200, 300, 260)
                pygame.draw.rect(screen, PANEL_BG, rr, border_radius=12)
                pygame.draw.rect(screen, GOLD, rr, width=3, border_radius=12)
                screen.blit(font_md.render(relic.name, True, GOLD), (rr.x + 20, rr.y + 28))
                screen.blit(font_xs.render(relic.tier_kind, True, AETHER_CYAN), (rr.x + 20, rr.y + 60))
                screen.blit(font_xs.render(relic.description[:40], True, TEXT_LIGHT), (rr.x + 20, rr.y + 110))
                screen.blit(font_xs.render(relic.description[40:80], True, TEXT_LIGHT), (rr.x + 20, rr.y + 132))
                self._click_targets.append(ClickTarget(rr, "pick_relic", idx))
        elif human.pending_oracle_choices:
            overlay = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)
            overlay.fill((8, 6, 14, 210))
            screen.blit(overlay, (0, 0))
            title = font_lg.render("ASCENSION ORACLE — DISCOVER A UNIT", True, GOLD)
            screen.blit(title, (WINDOW_W // 2 - title.get_width() // 2, 120))
            for idx, unit in enumerate(human.pending_oracle_choices):
                cr = pygame.Rect(280 + idx * 250, 210, 210, 220)
                self._draw_unit_card(screen, unit, cr, font_sm, font_xs, action_name="pick_oracle", action_index=idx)

    def _render_game_over(
        self,
        screen: pygame.Surface,
        font_lg: pygame.font.Font,
        font_md: pygame.font.Font,
        font_sm: pygame.font.Font,
    ) -> None:
        place = self.lobby.human.placement
        banner = "VICTORY! CONCLAVE CHAMPION" if place == 1 else f"FINISHED PLACE #{place}"
        title = font_lg.render(banner, True, GOLD if place == 1 else CRIMSON)
        screen.blit(title, (WINDOW_W // 2 - title.get_width() // 2, 110))

        for idx, comm in enumerate(self.lobby.leaderboard()):
            line = font_sm.render(
                f"#{idx + 1}  {comm.name:24s}  Tier {comm.bastion_tier}  HP {comm.health}+{comm.armor}",
                True,
                GOLD if comm.is_human else TEXT_LIGHT,
            )
            screen.blit(line, (WINDOW_W // 2 - 260, 190 + idx * 36))

        btn = pygame.Rect(WINDOW_W // 2 - 120, 540, 240, 48)
        pygame.draw.rect(screen, (88, 66, 22), btn, border_radius=8)
        pygame.draw.rect(screen, GOLD, btn, width=2, border_radius=8)
        t = font_md.render("NEW CONCLAVE", True, TEXT_LIGHT)
        screen.blit(t, (btn.centerx - t.get_width() // 2, btn.centery - 10))
        self._click_targets.append(ClickTarget(btn, "new_run"))
