# Aethelgard: Conclave of War (`AethelgardBattlegrounds`)

An 8-Commander tactical autobattler set in the Aethelgard universe, built with **Godot 4.7.2** (3D/2.5D War Table arena), **Blender 5.3** (procedural `.glb` models verified via `blender-asset-qa`), and a pure-**Python** domain core with a **Pygame-CE** 1280x720 fallback client.

## Original Lore & Mechanics

Every system uses original Aethelgard terminology inspired by classic autobattler strategy:

- **War Conclave (8-Commander Lobby):** 1 Human Commander vs. 7 AI Commanders starting with 30 Health + Commander Armor (6–14). Eliminated Commanders return as **Fallen Spirits** for odd-player pairings.
- **Tribe Rotation:** 6 Biome Tribes + 1 Neutral Tribe. Each lobby activates **5 Biome Tribes + Oakhaven Mercenaries** and **Exiles** 1 Biome Tribe:
  1. **Sylvan Blight** (*The Wilted Arboretum*) — `BLIGHT`, Health growth, and spore `LAST_ECHO` spawns.
  2. **Drowned Undead** (*The Drowned Ossuary*) — `UNDYING` revives, `LAST_ECHO` swarms, and `RETRIBUTION`.
  3. **Infernal Forge** (*The Foundry of Torment*) — `AEGIS` refreshes, Forge Platings, and death shrapnel.
  4. **Cathedral Cult** (*The Desecrated Cathedral*) — `Arcane Edicts`, stone `VANGUARD`, and zealot scaling.
  5. **Crimson Court** (*The Blood Sanctum*) — `Blood Shards (+1/+1)`, `FRENZY` double strikes.
  6. **Astral Void** (*The Astral Observatory*) — `SWEEP` cleaves, `SHROUD` stealth, and Conclave refresh buffs.
  7. **Oakhaven Mercenaries** (*Oakhaven Village*, Neutral) — Cross-tribe support, Crowns, and menagerie buffs.
- **8 Playable Commanders:** Captain Rowan, Rachel (Witch of the Orchid), Lyra (Briar Botanist), Caelen (Shadow Scout), Melissa (Weave Archmage), Sister Valora, High Lord Carmilla, and The Ironforge Tyrant — each with a unique **Commander's Mandate**.
- **Conclave Phase:**
  - **Aether Crowns:** Start at 3 on Round 1, +1 max per round up to 10 (or 13 with *Aether Sovereign Seal*).
  - **Recruit (3g), Dismiss (+1g), Refresh (1g), Seal/Freeze (0g), Elevate Bastion (Tiers I–VI)** with per-round cost decay.
  - **Ascension (Triple):** Collecting 3 non-ascended copies fuses them into an **Ascended** unit (2x base stats + accumulated buffs + 2x effects) and grants an **Ascension Oracle** (Discover 1 of 3 units from the next Bastion Tier).
  - **Arcane Edicts:** 1 purchasable spell per Conclave refresh (Tiers I–VI).
  - **Dawn Relics:** Offered on **Round 6 (Lesser)** and **Round 9 (Greater)** for match-long passive build-arounds.
- **Keywords:** `VANGUARD`, `AEGIS`, `BLIGHT`, `FRENZY`, `UNDYING`, `VOW`, `LAST_ECHO`, `RETRIBUTION`, `SWEEP`, `SHROUD`.

## Quick Start

```powershell
# Launch Godot 4.7.2 3D/2.5D client (auto-detected)
.\.venv\Scripts\python.exe main.py

# Launch Pygame-CE 1280x720 fallback client
.\.venv\Scripts\python.exe main.py --pygame

# Run headless deterministic tournament simulation
.\.venv\Scripts\python.exe main.py --simulate --seed 42
```

## Asset & Verification Commands

```powershell
# Regenerate & QA-check Blender 5.3 .glb models
& "C:\Program Files\Blender Foundation\Blender 5.3\blender.exe" -b --factory-startup --python-exit-code 1 -P tools/blender_build_assets.py

# Run Python unit + integration + Godot smoke tests
.\.venv\Scripts\python.exe -m pytest -v

# Run Ruff linter
.\.venv\Scripts\python.exe -m ruff check src tests tools main.py
```
