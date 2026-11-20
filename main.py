"""Entrypoint for Aethelgard: Conclave of War (Godot 4.7.2 3D, Pygame-CE, or Headless Sim)."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path

from src.core.enums import GamePhase
from src.core.rng import SeededRNG
from src.systems.lobby_manager import LobbyManager


def _find_godot_exe() -> Path | None:
    env = os.environ.get("GODOT_EXE")
    if env and Path(env).is_file():
        return Path(env)
    on_path = shutil.which("godot") or shutil.which("godot4")
    if on_path:
        return Path(on_path)
    winget_root = Path(os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages"))
    if winget_root.is_dir():
        for exe in sorted(winget_root.rglob("Godot_v4.*_win64.exe"), reverse=True):
            if "_console" not in exe.name:
                return exe
    return None


def _run_simulation(seed: int) -> int:
    lobby = LobbyManager(rng=SeededRNG(seed))
    lobby.select_human_commander(lobby.commander_choices[0])
    while lobby.phase != GamePhase.GAME_OVER and lobby.round_number < 25:
        if lobby.phase == GamePhase.RELIC_SELECT:
            lobby.pick_human_relic(0)
        assert lobby.shop is not None
        if lobby.human.crowns >= 3 and lobby.human.shop_units:
            lobby.shop.recruit_unit(lobby.human, 0)
        while lobby.human.warband.hand:
            res = lobby.shop.play_hand_card(lobby.human, 0)
            if res.oracle_triggered and lobby.human.pending_oracle_choices:
                lobby.shop.pick_oracle_choice(lobby.human, 0)
            elif not res.ok:
                break
        lobby.start_combat_phase()
        if lobby.phase != GamePhase.GAME_OVER:
            lobby.advance_to_next_round()

    print(
        f"Simulated {lobby.round_number} rounds | Human placement: #{lobby.human.placement} | "
        f"Active tribes: {','.join(lobby.active_tribes)} | Exiled: {lobby.exiled_tribe}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Aethelgard: Conclave of War launcher")
    parser.add_argument("--pygame", action="store_true", help="Run the 1280x720 Pygame-CE frontend")
    parser.add_argument("--simulate", action="store_true", help="Run a headless lobby simulation")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic RNG seed")
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parent
    if args.simulate:
        return _run_simulation(args.seed)

    if not args.pygame:
        godot_exe = _find_godot_exe()
        if godot_exe is not None and (repo_root / "project.godot").is_file():
            proc = subprocess.run([str(godot_exe), "--path", str(repo_root)], check=False)
            return proc.returncode

    from src.frontends.pygame_ce.app import PygameConclaveApp

    return PygameConclaveApp(assets_dir=repo_root / "assets", seed=args.seed).run()


if __name__ == "__main__":
    raise SystemExit(main())
