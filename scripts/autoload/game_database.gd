extends Node
## Canonical read-only data catalog mirroring AethelgardBattlegrounds Python definitions.

const BIOME_TRIBES: Array[String] = [
	"sylvan",
	"drowned",
	"forge",
	"cult",
	"crimson",
	"astral",
]
const NEUTRAL_TRIBE: String = "mercenary"

const TIER_POOL_COPIES: Dictionary = {
	1: 15,
	2: 15,
	3: 13,
	4: 11,
	5: 9,
	6: 7,
}

const BASTION_UPGRADE_COSTS: Dictionary = {
	1: 5,
	2: 7,
	3: 8,
	4: 9,
	5: 10,
}

const CONCLAVE_SHOP_SLOTS: Dictionary = {
	1: 3,
	2: 4,
	3: 4,
	4: 5,
	5: 5,
	6: 6,
}

var _texture_cache: Dictionary = {}

var tribes: Dictionary = {
	"sylvan": {
		"id": "sylvan",
		"name": "Sylvan Blight",
		"es_name": "Arboreto Marchito",
		"color": Color("#3E9C5C"),
		"focus": "Blight, Health growth, Spore Last Echoes",
	},
	"drowned": {
		"id": "drowned",
		"name": "Drowned Undead",
		"es_name": "Osario Ahogado",
		"color": Color("#4D78A8"),
		"focus": "Undying revives, Last Echo swarms, Retribution",
	},
	"forge": {
		"id": "forge",
		"name": "Infernal Forge",
		"es_name": "Fundicion del Tormento",
		"color": Color("#D97B29"),
		"focus": "Aegis shields, plating, explosive shrapnel",
	},
	"cult": {
		"id": "cult",
		"name": "Cathedral Cult",
		"es_name": "Catedral Profanada",
		"color": Color("#8A56B8"),
		"focus": "Arcane Edicts, Vanguard walls, Retribution",
	},
	"crimson": {
		"id": "crimson",
		"name": "Crimson Court",
		"es_name": "Sagrario de Sangre",
		"color": Color("#B8323B"),
		"focus": "Blood Shards (+1/+1), Frenzy double strikes",
	},
	"astral": {
		"id": "astral",
		"name": "Astral Void",
		"es_name": "Observatorio Astral",
		"color": Color("#32B2CC"),
		"focus": "Sweep cleaves, Shroud ambushes, Shop buffs",
	},
	"mercenary": {
		"id": "mercenary",
		"name": "Oakhaven Mercenaries",
		"es_name": "Mercenarios de Oakhaven",
		"color": Color("#C9A84C"),
		"focus": "Cross-tribe utility and Aether Crowns",
	},
}

var commanders: Dictionary = {
	"rowan": {
		"id": "rowan",
		"name": "Captain Rowan",
		"title": "Sunwarden Vanguard",
		"portrait": "rowan.png",
		"health": 30,
		"armor": 10,
		"mandate_name": "Solar Bulwark",
		"mandate_cost": 1,
		"is_passive": false,
		"mandate_desc": "1 Crown: Give a friendly unit +1/+2 and Vanguard.",
		"preferred": ["mercenary", "forge"],
	},
	"rachel": {
		"id": "rachel",
		"name": "Rachel",
		"title": "Witch of the Orchid",
		"portrait": "rachel.png",
		"health": 30,
		"armor": 8,
		"mandate_name": "Violet Ember",
		"mandate_cost": 1,
		"is_passive": false,
		"mandate_desc": "1 Crown: Add an Arcane Edict to hand and give an ally +1/+1.",
		"preferred": ["cult", "crimson"],
	},
	"lyra": {
		"id": "lyra",
		"name": "Lyra",
		"title": "Briar Botanist",
		"portrait": "lyra.png",
		"health": 30,
		"armor": 12,
		"mandate_name": "Root Symbiosis",
		"mandate_cost": 1,
		"is_passive": false,
		"mandate_desc": "1 Crown: Give a friendly unit +2/+2 (Sylvan +3/+3).",
		"preferred": ["sylvan", "mercenary"],
	},
	"caelen": {
		"id": "caelen",
		"name": "Caelen",
		"title": "Shadow Scout",
		"portrait": "caelen.png",
		"health": 30,
		"armor": 9,
		"mandate_name": "Ambush Ledger",
		"mandate_cost": 1,
		"is_passive": false,
		"mandate_desc": "1 Crown: Give a friendly unit +3 Attack and Shroud.",
		"preferred": ["astral", "crimson"],
	},
	"melissa": {
		"id": "melissa",
		"name": "Melissa",
		"title": "Weave Archmage",
		"portrait": "melissa.png",
		"health": 30,
		"armor": 7,
		"mandate_name": "Astral Resonance",
		"mandate_cost": 0,
		"is_passive": true,
		"mandate_desc": "Passive: First Conclave Refresh each round is free.",
		"preferred": ["astral", "cult"],
	},
	"valora": {
		"id": "valora",
		"name": "Sister Valora",
		"title": "Solar Inquisitor",
		"portrait": "valora.png",
		"health": 30,
		"armor": 6,
		"mandate_name": "Judgment Aegis",
		"mandate_cost": 2,
		"is_passive": false,
		"mandate_desc": "2 Crowns: Grant a friendly unit Aegis and +2 Attack.",
		"preferred": ["forge", "cult"],
	},
	"carmilla": {
		"id": "carmilla",
		"name": "High Lord Carmilla",
		"title": "Sanguine Matriarch",
		"portrait": "carmilla.png",
		"health": 30,
		"armor": 11,
		"mandate_name": "Sanguine Tithe",
		"mandate_cost": 0,
		"is_passive": false,
		"mandate_desc": "Pay 1 Health: Gain 1 Crown and 2 Blood Shards.",
		"preferred": ["crimson", "drowned"],
	},
	"ironforge": {
		"id": "ironforge",
		"name": "The Ironforge Tyrant",
		"title": "Master of the Vault",
		"portrait": "ironforge.png",
		"health": 30,
		"armor": 14,
		"mandate_name": "Master Forging",
		"mandate_cost": 0,
		"is_passive": true,
		"mandate_desc": "Passive: Every 2 rounds gain a Forge Plating (+2/+2 & Aegis).",
		"preferred": ["forge", "drowned"],
	},
}

var units: Dictionary = {
	# SYLVAN
	"thornvein_creeper": _u("thornvein_creeper", "Thornvein Creeper", "sylvan", 1, 2, 2, "thornvein_creeper.png", ["VOW"], "Vow: Give a friendly Sylvan +1/+1.", {"kind": "buff_random_ally", "atk": 1, "hp": 1, "tribe": "sylvan"}),
	"spore_pod": _u("spore_pod", "Spore-Spitting Pod", "sylvan", 1, 1, 3, "spore_pod.png", ["LAST_ECHO"], "Last Echo: Summon a 1/1 Briar Spore.", {}, {"kind": "summon", "count": 1, "token": "briar_spore_token"}),
	"bramble_hound": _u("bramble_hound", "Bramble Hound", "sylvan", 2, 3, 2, "bramble_hound.png", ["FRENZY"], "Frenzy: Attacks twice."),
	"rotting_woodwose": _u("rotting_woodwose", "Rotting Woodwose", "sylvan", 3, 3, 6, "rotting_woodwose.png", ["VANGUARD", "RETRIBUTION"], "Vanguard. Retribution(2): Gain +1/+2.", {}, {}, {"kind": "buff_self", "atk": 1, "hp": 2, "thresh": 2}),
	"mandragora_matron": _u("mandragora_matron", "Mandragora Matron", "sylvan", 4, 4, 5, "mandragora_matron.png", ["BLIGHT"], "Blight: Destroys first enemy damaged."),
	"corpse_treant": _u("corpse_treant", "Corpse-Root Treant", "sylvan", 5, 6, 8, "corpse_treant.png", ["VANGUARD", "LAST_ECHO"], "Vanguard. Last Echo: Summon two 2/2 Spores.", {}, {"kind": "summon", "count": 2, "token": "briar_spore_token", "atk": 1, "hp": 1}),
	"verdant_abomination": _u("verdant_abomination", "Verdant Abomination", "sylvan", 6, 8, 10, "verdant_abomination.png", ["BLIGHT", "LAST_ECHO"], "Blight. Last Echo: Friendly Sylvans +3/+4.", {}, {"kind": "buff_all_allies", "atk": 3, "hp": 4, "tribe": "sylvan"}),
	# DROWNED
	"drowned_skulls": _u("drowned_skulls", "Drowned Skull-Cluster", "drowned", 1, 2, 1, "drowned_skulls.png", ["UNDYING"], "Undying: Revives once with 1 Health."),
	"mire_ghoul": _u("mire_ghoul", "Mire Ghoul", "drowned", 1, 1, 3, "mire_ghoul.png", ["LAST_ECHO"], "Last Echo: Summon a 1/1 Risen Skull.", {}, {"kind": "summon", "count": 1, "token": "risen_skull_token"}),
	"leech_husk": _u("leech_husk", "Leech-Swarm Husk", "drowned", 2, 3, 3, "leech_husk.png", ["RETRIBUTION"], "Retribution(2): Gain +1/+1.", {}, {}, {"kind": "buff_self", "atk": 1, "hp": 1, "thresh": 2}),
	"crypt_lurker": _u("crypt_lurker", "Crypt Lurker", "drowned", 3, 4, 3, "crypt_lurker.png", ["UNDYING", "SHROUD"], "Undying, Shroud."),
	"tide_gravekeeper": _u("tide_gravekeeper", "Tide-Risen Gravekeeper", "drowned", 4, 4, 6, "tide_gravekeeper.png", ["VANGUARD", "RETRIBUTION"], "Vanguard. Retribution(3): Summon 2/2 Skull.", {}, {}, {"kind": "summon", "count": 1, "token": "risen_skull_token", "atk": 1, "hp": 1, "thresh": 3}),
	"carrion_behemoth": _u("carrion_behemoth", "Carrion Behemoth", "drowned", 5, 7, 8, "carrion_behemoth.png", ["UNDYING", "LAST_ECHO"], "Undying. Last Echo: Friendly Drowned +2/+2.", {}, {"kind": "buff_all_allies", "atk": 2, "hp": 2, "tribe": "drowned"}),
	"drowned_patriarch": _u("drowned_patriarch", "The Drowned Patriarch", "drowned", 6, 8, 9, "drowned_patriarch.png", ["VANGUARD", "LAST_ECHO"], "Vanguard. Last Echo: Summon two 3/3 Skulls.", {}, {"kind": "summon", "count": 2, "token": "risen_skull_token", "atk": 2, "hp": 2}),
	# FORGE
	"cinder_sprite": _u("cinder_sprite", "Cinder Sprite", "forge", 1, 2, 2, "cinder_sprite.png", ["LAST_ECHO"], "Last Echo: Deal 2 dmg to random enemy.", {}, {"kind": "damage_random_enemy", "dmg": 2, "count": 1}),
	"slag_homunculus": _u("slag_homunculus", "Slagforged Homunculus", "forge", 1, 2, 3, "slag_homunculus.png", ["VANGUARD"], "Vanguard."),
	"clockwork_flayer": _u("clockwork_flayer", "Clockwork Flayer", "forge", 2, 3, 2, "clockwork_flayer.png", ["AEGIS"], "Aegis."),
	"ashen_overseer": _u("ashen_overseer", "Ashen Overseer", "forge", 3, 3, 5, "ashen_overseer.png", ["VOW"], "Vow: Give friendly Forge +2/+2 & Aegis.", {"kind": "buff_random_ally", "atk": 2, "hp": 2, "grant_kw": "AEGIS", "tribe": "forge"}),
	"inquisitor_automaton": _u("inquisitor_automaton", "Inquisitor Automaton", "forge", 4, 5, 4, "inquisitor_automaton.png", ["AEGIS", "FRENZY"], "Aegis, Frenzy."),
	"furnace_warden": _u("furnace_warden", "Furnace Warden", "forge", 5, 5, 9, "furnace_warden.png", ["VANGUARD", "AEGIS", "RETRIBUTION"], "Vanguard, Aegis. Retribution(2): Grant Aegis.", {}, {}, {"kind": "grant_kw_ally", "grant_kw": "AEGIS", "tribe": "forge", "thresh": 2}),
	"ironforge_tyrant": _u("ironforge_tyrant", "The Ironforge Tyrant", "forge", 6, 9, 9, "ironforge_tyrant.png", ["AEGIS", "SWEEP"], "Aegis, Sweep."),
	# CULT
	"cathedral_imp": _u("cathedral_imp", "Cathedral Imp", "cult", 1, 2, 1, "cathedral_imp.png", ["VOW"], "Vow: Deal 1 dmg to Commander, gain +2/+2.", {"kind": "self_pact", "atk": 2, "hp": 2, "dmg": 1}),
	"possessed_grimoire": _u("possessed_grimoire", "Possessed Grimoire", "cult", 1, 1, 3, "possessed_grimoire.png", ["VOW"], "Vow: Add a random Arcane Edict to hand.", {"kind": "add_edict", "count": 1}),
	"candelabra_fiend": _u("candelabra_fiend", "Candelabra Fiend", "cult", 2, 3, 4, "candelabra_fiend.png", ["VANGUARD"], "Vanguard. +1/+2 when you cast an Edict.", {}, {}, {}, {"on_edict": {"atk": 1, "hp": 2}}),
	"penitent_zealot": _u("penitent_zealot", "Penitent Zealot", "cult", 3, 4, 4, "penitent_zealot.png", ["RETRIBUTION"], "Retribution(2): Gain +2/+1.", {}, {}, {"kind": "buff_self", "atk": 2, "hp": 1, "thresh": 2}),
	"belltower_gargoyle": _u("belltower_gargoyle", "Belltower Gargoyle", "cult", 4, 4, 7, "belltower_gargoyle.png", ["VANGUARD", "AEGIS"], "Vanguard, Aegis."),
	"chorus_of_damned": _u("chorus_of_damned", "Chorus of the Damned", "cult", 5, 6, 6, "chorus_of_damned.png", ["LAST_ECHO"], "Last Echo: Deal 4 dmg to all enemies.", {}, {"kind": "damage_all_enemies", "dmg": 4}),
	"blind_archbishop": _u("blind_archbishop", "The Blind Archbishop", "cult", 6, 7, 9, "blind_archbishop.png", ["VOW"], "Vow: Give all friendly Cult +3/+3.", {"kind": "buff_all_allies", "atk": 3, "hp": 3, "tribe": "cult"}),
	# CRIMSON
	"sanguine_thrall": _u("sanguine_thrall", "Sanguine Thrall", "crimson", 1, 2, 2, "sanguine_thrall.png", ["VOW"], "Vow: Add 1 Blood Shard to hand.", {"kind": "add_shards", "count": 1}),
	"crimson_gargoyle": _u("crimson_gargoyle", "Crimson Gargoyle", "crimson", 1, 1, 4, "crimson_gargoyle.png", ["VANGUARD"], "Vanguard. +1 ATK extra from Blood Shards.", {}, {}, {}, {"on_shard": {"atk": 1, "hp": 0}}),
	"hemomancer_acolyte": _u("hemomancer_acolyte", "Hemomancer Acolyte", "crimson", 2, 3, 2, "hemomancer_acolyte.png", ["LAST_ECHO"], "Last Echo: Add 2 Blood Shards to hand.", {}, {"kind": "add_shards", "count": 2}),
	"flayed_duelist": _u("flayed_duelist", "Flayed Duelist", "crimson", 3, 4, 3, "flayed_duelist.png", ["FRENZY"], "Frenzy."),
	"baroness_vespera": _u("baroness_vespera", "Baroness Vespera", "crimson", 4, 5, 5, "baroness_vespera.png", ["FRENZY", "SHROUD"], "Frenzy, Shroud."),
	"amalgam_of_veins": _u("amalgam_of_veins", "Amalgam of Veins", "crimson", 5, 6, 9, "amalgam_of_veins.png", ["VANGUARD", "RETRIBUTION"], "Vanguard. Retribution(2): Crimson allies +1/+1.", {}, {}, {"kind": "buff_all_allies", "atk": 1, "hp": 1, "tribe": "crimson", "thresh": 2}),
	"blood_god_avatar": _u("blood_god_avatar", "The Blood-God Avatar", "crimson", 6, 9, 8, "blood_god_avatar.png", ["FRENZY", "VOW"], "Frenzy. Vow: +3 Shards and all allies +2/+2.", {"kind": "crimson_awakening", "atk": 2, "hp": 2, "count": 3}),
	# ASTRAL
	"stareater_wisp": _u("stareater_wisp", "Star-Eater Wisp", "astral", 1, 2, 2, "stareater_wisp.png", ["SHROUD"], "Shroud."),
	"void_mirror": _u("void_mirror", "Void Mirror", "astral", 1, 1, 4, "void_mirror.png", ["VANGUARD", "AEGIS"], "Vanguard, Aegis."),
	"crystal_viper": _u("crystal_viper", "Crystal Viper", "astral", 2, 3, 2, "crystal_viper.png", ["BLIGHT"], "Blight."),
	"comet_stalker": _u("comet_stalker", "Comet Stalker", "astral", 3, 4, 3, "comet_stalker.png", ["SWEEP"], "Sweep: Damages adjacent foes."),
	"celestial_hermit": _u("celestial_hermit", "Celestial Hermit", "astral", 4, 4, 6, "celestial_hermit.png", ["VOW"], "Vow: Buff Conclave units +2/+2 & 1 Free Refresh.", {"kind": "empower_conclave", "atk": 2, "hp": 2, "count": 1}),
	"rift_warden": _u("rift_warden", "Rift Warden", "astral", 5, 6, 5, "rift_warden.png", ["SWEEP", "SHROUD"], "Sweep, Shroud."),
	"devouring_constellation": _u("devouring_constellation", "The Devouring Constellation", "astral", 6, 8, 8, "devouring_constellation.png", ["SWEEP", "AEGIS"], "Sweep, Aegis."),
	# MERCENARIES
	"oakhaven_watchman": _u("oakhaven_watchman", "Oakhaven Watchman", "mercenary", 1, 2, 3, "oakhaven_watchman.png", ["VANGUARD"], "Vanguard."),
	"briarwood_herbalist": _u("briarwood_herbalist", "Briarwood Herbalist", "mercenary", 2, 2, 4, "briarwood_herbalist.png", ["VOW"], "Vow: Give a friendly unit +2/+2.", {"kind": "buff_random_ally", "atk": 2, "hp": 2}),
	"sunwarden_squire": _u("sunwarden_squire", "Sunwarden Squire", "mercenary", 3, 4, 4, "sunwarden_squire.png", ["AEGIS"], "Aegis."),
	"weave_chronicler": _u("weave_chronicler", "Weave Chronicler", "mercenary", 4, 4, 5, "weave_chronicler.png", ["VOW"], "Vow: Add a random Arcane Edict to hand.", {"kind": "add_edict", "count": 1}),
	"guild_quartermaster": _u("guild_quartermaster", "Guild Quartermaster", "mercenary", 5, 5, 6, "guild_quartermaster.png", ["VOW"], "Vow: Gain 2 Aether Crowns.", {"kind": "gain_crowns", "count": 2}),
	"elder_tomas": _u("elder_tomas", "Elder Tomas of Oakhaven", "mercenary", 6, 7, 7, "elder_tomas.png", ["VOW"], "Vow: Give one unit of each tribe +3/+3.", {"kind": "menagerie_buff", "atk": 3, "hp": 3}),
	# TOKENS
	"briar_spore_token": _u("briar_spore_token", "Briar Spore", "sylvan", 1, 1, 1, "spore_pod.png", [], "Summoned spore token.", {}, {}, {}, {"is_token": true}),
	"risen_skull_token": _u("risen_skull_token", "Risen Skull", "drowned", 1, 1, 1, "drowned_skulls.png", [], "Summoned skull token.", {}, {}, {}, {"is_token": true}),
}

var edicts: Dictionary = {
	"oakhaven_ration": {"id": "oakhaven_ration", "name": "Oakhaven Ration", "tier": 1, "cost": 1, "kind": "buff_random_ally", "atk": 2, "hp": 2, "desc": "Give random ally +2/+2."},
	"crimson_draught": {"id": "crimson_draught", "name": "Crimson Draught", "tier": 1, "cost": 1, "kind": "add_shards", "count": 2, "desc": "Add 2 Blood Shards to hand."},
	"crown_minting": {"id": "crown_minting", "name": "Crown Minting", "tier": 2, "cost": 2, "kind": "increase_max_crowns", "crowns": 1, "desc": "Gain +1 Max Crown permanently."},
	"stoneward_chant": {"id": "stoneward_chant", "name": "Stoneward Chant", "tier": 2, "cost": 2, "kind": "buff_vanguard", "atk": 1, "hp": 4, "desc": "Give ally +1/+4 and Vanguard."},
	"bastion_bounty": {"id": "bastion_bounty", "name": "Bastion Bounty", "tier": 3, "cost": 2, "kind": "recruit_random_tier", "desc": "Add random unit of your Tier."},
	"sunfire_tempering": {"id": "sunfire_tempering", "name": "Sunfire Tempering", "tier": 3, "cost": 3, "kind": "buff_all_allies", "atk": 2, "hp": 1, "desc": "Give all allies +2/+1."},
	"solaris_aegis": {"id": "solaris_aegis", "name": "Solaris Aegis", "tier": 4, "cost": 3, "kind": "grant_aegis", "atk": 2, "hp": 2, "desc": "Grant ally Aegis and +2/+2."},
	"echoes_of_ossuary": {"id": "echoes_of_ossuary", "name": "Echoes of the Ossuary", "tier": 4, "cost": 3, "kind": "grant_undying", "desc": "Grant a friendly unit Undying."},
	"astral_conjunction": {"id": "astral_conjunction", "name": "Astral Conjunction", "tier": 5, "cost": 3, "kind": "buff_shop", "atk": 3, "hp": 3, "desc": "Buff Conclave +3/+3 & 1 Free Refresh."},
	"blood_tithe_ritual": {"id": "blood_tithe_ritual", "name": "Blood Tithe Ritual", "tier": 5, "cost": 2, "kind": "crowns_and_shards", "crowns": 3, "count": 2, "desc": "Gain 3 Crowns & 2 Blood Shards."},
	"elder_coronation": {"id": "elder_coronation", "name": "Elder Coronation", "tier": 6, "cost": 4, "kind": "buff_all_allies", "atk": 4, "hp": 4, "desc": "Give all allies +4/+4."},
	"sovereign_ascension_rite": {"id": "sovereign_ascension_rite", "name": "Sovereign Ascension Rite", "tier": 6, "cost": 5, "kind": "add_oracle", "desc": "Add an Ascension Oracle to hand."},
}

var relics: Dictionary = {
	"briar_crown_band": {"id": "briar_crown_band", "name": "Briar Crown Band", "tier_kind": "LESSER", "desc": "Combat Start: All allies +2/+2."},
	"sunwarden_banner": {"id": "sunwarden_banner", "name": "Sunwarden Banner", "tier_kind": "LESSER", "desc": "Combat Start: Leftmost ally gains Aegis."},
	"oakhaven_purse": {"id": "oakhaven_purse", "name": "Oakhaven Merchant Purse", "tier_kind": "LESSER", "desc": "Round Start: Gain +2 bonus Crowns."},
	"crimson_chalice": {"id": "crimson_chalice", "name": "Crimson Chalice", "tier_kind": "LESSER", "desc": "Round Start: Add 2 Blood Shards."},
	"ossuary_lantern": {"id": "ossuary_lantern", "name": "Ossuary Lantern", "tier_kind": "LESSER", "desc": "Summoned combat units gain +2/+1."},
	"astral_astrolabe": {"id": "astral_astrolabe", "name": "Astral Astrolabe", "tier_kind": "LESSER", "desc": "Refreshed Conclave units gain +1/+1."},
	"solar_heartstone": {"id": "solar_heartstone", "name": "Solar Heartstone", "tier_kind": "GREATER", "desc": "Combat Start: Leftmost unit doubles ATK (+30 max) & +6 HP."},
	"aether_sovereign_seal": {"id": "aether_sovereign_seal", "name": "Aether Sovereign Seal", "tier_kind": "GREATER", "desc": "Max Crowns becomes 13 and +3 Crowns each round."},
	"elder_root_effigy": {"id": "elder_root_effigy", "name": "Elder Root Effigy", "tier_kind": "GREATER", "desc": "Combat Start: All allies +5/+6."},
	"sanctum_reliquary": {"id": "sanctum_reliquary", "name": "Sanctum Reliquary", "tier_kind": "GREATER", "desc": "End of Recruit: Allies permanently gain +2/+2."},
	"molten_anvil_core": {"id": "molten_anvil_core", "name": "Molten Anvil Core", "tier_kind": "GREATER", "desc": "Combat Start: Two leftmost allies gain Aegis & +3/+0."},
	"eternal_echo_bell": {"id": "eternal_echo_bell", "name": "Eternal Echo Bell", "tier_kind": "GREATER", "desc": "Combat Start: Last Echo & Undying allies +4/+4."},
}


static func _u(
	uid: String,
	uname: String,
	tribe: String,
	tier: int,
	atk: int,
	hp: int,
	sprite: String,
	kws: Array,
	desc: String,
	vow: Dictionary = {},
	last_echo: Dictionary = {},
	retribution: Dictionary = {},
	extra: Dictionary = {},
) -> Dictionary:
	return {
		"id": uid,
		"name": uname,
		"tribe": tribe,
		"tier": tier,
		"attack": atk,
		"health": hp,
		"sprite": sprite,
		"keywords": kws,
		"desc": desc,
		"vow": vow,
		"last_echo": last_echo,
		"retribution": retribution,
		"on_edict": extra.get("on_edict", {}),
		"on_shard": extra.get("on_shard", {}),
		"is_token": bool(extra.get("is_token", false)),
	}


func get_unit_sprite(filename: String) -> Texture2D:
	var key := "unit_" + filename
	if _texture_cache.has(key):
		return _texture_cache[key] as Texture2D
	var path := "res://assets/sprites/units/" + filename
	var tex: Texture2D = ResourceLoader.load(path) as Texture2D
	_texture_cache[key] = tex
	return tex


func get_portrait_texture(filename: String) -> Texture2D:
	var key := "port_" + filename
	if _texture_cache.has(key):
		return _texture_cache[key] as Texture2D
	var path := "res://assets/portraits/" + filename
	var tex: Texture2D = ResourceLoader.load(path) as Texture2D
	_texture_cache[key] = tex
	return tex
