"""End-to-end 8-Commander lobby simulation and Blender/Godot asset verification."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from PIL import Image

from src.core.enums import GamePhase
from src.core.rng import SeededRNG
from src.data.commanders import COMMANDER_CATALOG
from src.data.units import UNIT_CATALOG
from src.systems.lobby_manager import LobbyManager

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_full_eight_commander_lobby_completes_cleanly() -> None:
    lobby = LobbyManager(rng=SeededRNG(42))
    assert len(lobby.active_tribes) == 6  # 5 biome tribes + mercenary
    assert lobby.exiled_tribe not in lobby.active_tribes
    assert len(lobby.commander_choices) == 3

    lobby.select_human_commander(lobby.commander_choices[0])
    assert len(lobby.commanders) == 8
    assert lobby.phase == GamePhase.RECRUIT

    max_rounds = 40
    while lobby.phase != GamePhase.GAME_OVER and lobby.round_number < max_rounds:
        if lobby.phase == GamePhase.RELIC_SELECT:
            lobby.pick_human_relic(0)
        assert lobby.shop is not None
        # Basic greedy human bot to drive full match progression
        if lobby.human.bastion_tier < 6 and lobby.human.crowns >= lobby.human.upgrade_cost and lobby.round_number in {2, 4, 6}:
            lobby.shop.elevate_bastion(lobby.human)
        while lobby.human.crowns >= 3 and lobby.human.shop_units and not lobby.human.warband.is_hand_full:
            lobby.shop.recruit_unit(lobby.human, 0)
        for idx in range(len(lobby.human.warband.hand) - 1, -1, -1):
            if not lobby.human.warband.is_board_full or lobby.human.warband.hand[idx].kind.value != "UNIT":
                res = lobby.shop.play_hand_card(lobby.human, idx)
                if res.oracle_triggered and lobby.human.pending_oracle_choices:
                    lobby.shop.pick_oracle_choice(lobby.human, 0)

        lobby.start_combat_phase()
        if lobby.phase != GamePhase.GAME_OVER:
            lobby.advance_to_next_round()

    assert lobby.phase == GamePhase.GAME_OVER
    assert 1 <= lobby.human.placement <= 8
    placements = sorted(c.placement for c in lobby.commanders)
    assert placements == [1, 2, 3, 4, 5, 6, 7, 8]


def test_all_unit_sprites_and_commander_portraits_are_valid_images() -> None:
    assets_dir = REPO_ROOT / "assets"
    for uid, defn in UNIT_CATALOG.items():
        img_path = assets_dir / "sprites" / "units" / defn.sprite_filename
        assert img_path.is_file(), f"Missing sprite for {uid}: {img_path}"
        with Image.open(img_path) as im:
            im.verify()

    for cid, defn in COMMANDER_CATALOG.items():
        port_path = assets_dir / "portraits" / defn.portrait_filename
        assert port_path.is_file(), f"Missing portrait for {cid}: {port_path}"
        with Image.open(port_path) as im:
            im.verify()


def test_all_blender_glb_models_exist_and_have_gltf_header() -> None:
    models_dir = REPO_ROOT / "assets" / "models"
    expected_glbs = (
        "conclave_war_table.glb",
        "unit_medallion.glb",
        "unit_medallion_ascended.glb",
        "aether_crown.glb",
        "dawn_relic_pedestal.glb",
    )
    for filename in expected_glbs:
        path = models_dir / filename
        assert path.is_file(), f"Missing GLB export: {path}"
        data = path.read_bytes()
        assert len(data) > 1000
        assert data[:4] == b"glTF"


def _find_godot_console() -> Path | None:
    on_path = shutil.which("godot_console") or shutil.which("godot")
    if on_path:
        return Path(on_path)
    winget_root = Path(os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages"))
    if winget_root.is_dir():
        for exe in sorted(winget_root.rglob("Godot_v4.*_win64_console.exe"), reverse=True):
            return exe
    return None


def test_godot_project_and_headless_smoke() -> None:
    assert (REPO_ROOT / "project.godot").is_file()
    assert (REPO_ROOT / "scenes" / "MainConclave.tscn").is_file()
    assert (REPO_ROOT / "scripts" / "core" / "conclave_engine.gd").is_file()

    godot = _find_godot_console()
    if godot is None:
        return

    proc = subprocess.run(
        [
            str(godot),
            "--headless",
            "--path",
            str(REPO_ROOT),
            "--script",
            "res://tools/godot_smoke_test.gd",
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, f"Godot smoke failed:\n{proc.stdout}\n{proc.stderr}"
    assert "GODOT_SMOKE_OK" in proc.stdout
