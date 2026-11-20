class_name ConclaveEngine
extends RefCounted
## Complete War Conclave autobattler state machine, shop/ascension rules, AI, and combat engine.

enum Phase {
	COMMANDER_SELECT,
	RECRUIT,
	RELIC_SELECT,
	COMBAT,
	GAME_OVER,
}

const MAX_WARBAND: int = 7
const MAX_HAND: int = 10

var rng: RandomNumberGenerator = RandomNumberGenerator.new()
var phase: Phase = Phase.COMMANDER_SELECT
var round_number: int = 0
var active_tribes: Array[String] = []
var exiled_tribe: String = ""
var commander_choices: Array[String] = []
var commanders: Array[Dictionary] = []
var pool_counts: Dictionary = {}
var current_pairings: Array[Dictionary] = []
var last_human_outcome: Dictionary = {}
var last_human_opponent_slot: int = -1
var _seq: int = 0
var _elimination_cursor: int = 8


func _next_id(prefix: String) -> String:
	_seq += 1
	return "%s_%d" % [prefix, _seq]


func start_new_lobby(seed_val: int = -1) -> void:
	if seed_val >= 0:
		rng.seed = seed_val
	else:
		rng.randomize()

	phase = Phase.COMMANDER_SELECT
	round_number = 0
	_seq = 0
	_elimination_cursor = 8
	commanders.clear()
	current_pairings.clear()
	last_human_outcome.clear()
	last_human_opponent_slot = -1

	var biomes: Array[String] = GameDatabase.BIOME_TRIBES.duplicate()
	var exile_idx: int = rng.randi_range(0, biomes.size() - 1)
	exiled_tribe = biomes[exile_idx]
	active_tribes.clear()
	for t in biomes:
		if t != exiled_tribe:
			active_tribes.append(t)
	active_tribes.append(GameDatabase.NEUTRAL_TRIBE)

	pool_counts.clear()
	for uid in GameDatabase.units.keys():
		var defn: Dictionary = GameDatabase.units[uid]
		if not bool(defn["is_token"]) and active_tribes.has(String(defn["tribe"])):
			var tier: int = int(defn["tier"])
			pool_counts[uid] = int(GameDatabase.TIER_POOL_COPIES[tier])

	var cids: Array = GameDatabase.commanders.keys()
	_shuffle_array(cids)
	commander_choices.clear()
	for i in range(mini(3, cids.size())):
		commander_choices.append(String(cids[i]))

	GlobalSignalBus.state_updated.emit()


func _shuffle_array(arr: Array) -> void:
	for i in range(arr.size() - 1, 0, -1):
		var j: int = rng.randi_range(0, i)
		var tmp: Variant = arr[i]
		arr[i] = arr[j]
		arr[j] = tmp


func _make_commander_state(slot_idx: int, cid: String, is_human_flag: bool) -> Dictionary:
	var defn: Dictionary = GameDatabase.commanders[cid]
	return {
		"slot_index": slot_idx,
		"commander_id": cid,
		"name": String(defn["name"]),
		"title": String(defn["title"]),
		"portrait": String(defn["portrait"]),
		"health": int(defn["health"]),
		"armor": int(defn["armor"]),
		"max_health": int(defn["health"]),
		"is_human": is_human_flag,
		"bastion_tier": 1,
		"upgrade_cost": 5,
		"crowns": 3,
		"max_crowns": 3,
		"bonus_max_crowns": 0,
		"crowns_cap": 10,
		"board": [],
		"hand": [],
		"shop_units": [],
		"shop_edict_id": "",
		"shop_frozen": false,
		"free_refreshes": 0,
		"mandate_used": false,
		"relics": [],
		"pending_oracle": [],
		"pending_relics": [],
		"eliminated": false,
		"placement": 0,
		"win_streak": 0,
		"wins": 0,
		"losses": 0,
	}


func _make_unit(uid: String, is_ascended: bool = false, custom_id: String = "") -> Dictionary:
	var defn: Dictionary = GameDatabase.units[uid]
	var mult: int = 2 if is_ascended else 1
	var atk: int = int(defn["attack"]) * mult
	var hp: int = int(defn["health"]) * mult
	var kws: Array[String] = []
	for k in defn["keywords"]:
		kws.append(String(k))
	return {
		"instance_id": custom_id if custom_id != "" else _next_id("u"),
		"unit_id": uid,
		"name": ("Ascended " + String(defn["name"])) if is_ascended else String(defn["name"]),
		"tribe": String(defn["tribe"]),
		"tier": int(defn["tier"]),
		"attack": atk,
		"health": hp,
		"max_health": hp,
		"keywords": kws,
		"is_ascended": is_ascended,
		"is_token": bool(defn["is_token"]),
		"sprite": String(defn["sprite"]),
		"blight_used": false,
		"undying_used": false,
		"shroud_broken": false,
		"retribution_counter": 0,
	}


func _clone_unit_for_combat(u: Dictionary, suffix: String) -> Dictionary:
	var copy: Dictionary = u.duplicate(true)
	copy["instance_id"] = String(u["instance_id"]) + suffix
	copy["health"] = int(u["max_health"])
	copy["blight_used"] = false
	copy["undying_used"] = false
	copy["shroud_broken"] = false
	copy["retribution_counter"] = 0
	return copy


func _apply_buff(u: Dictionary, atk_d: int, hp_d: int) -> void:
	u["attack"] = maxi(0, int(u["attack"]) + atk_d)
	u["health"] = maxi(1, int(u["health"]) + hp_d)
	u["max_health"] = maxi(1, int(u["max_health"]) + hp_d)


func _has_kw(u: Dictionary, kw: String) -> bool:
	if kw == "SHROUD" and bool(u.get("shroud_broken", false)):
		return false
	return (u["keywords"] as Array).has(kw)


func _add_kw(u: Dictionary, kw: String) -> void:
	var kws: Array = u["keywords"]
	if not kws.has(kw):
		kws.append(kw)
	if kw == "SHROUD":
		u["shroud_broken"] = false


func get_human() -> Dictionary:
	if commanders.is_empty():
		return {}
	return commanders[0]


func select_human_commander(cid: String) -> void:
	if phase != Phase.COMMANDER_SELECT or not GameDatabase.commanders.has(cid):
		return
	var others: Array[String] = []
	for k in GameDatabase.commanders.keys():
		if String(k) != cid:
			others.append(String(k))
	_shuffle_array(others)

	commanders.clear()
	commanders.append(_make_commander_state(0, cid, true))
	for i in range(7):
		commanders.append(_make_commander_state(i + 1, others[i], false))

	advance_to_next_round()


func _pool_draw(max_tier: int, count: int, exact_tier: int = -1) -> Array[String]:
	var drawn: Array[String] = []
	for _step in range(count):
		var candidates: Array[String] = []
		for uid in pool_counts.keys():
			var rem: int = int(pool_counts[uid])
			if rem <= 0:
				continue
			var t: int = int(GameDatabase.units[uid]["tier"])
			if (exact_tier > 0 and t == exact_tier) or (exact_tier <= 0 and t <= max_tier):
				for _c in range(rem):
					candidates.append(String(uid))
		if candidates.is_empty():
			break
		var picked: String = candidates[rng.randi_range(0, candidates.size() - 1)]
		pool_counts[picked] = int(pool_counts[picked]) - 1
		drawn.append(picked)
	return drawn


func _pool_draw_distinct(exact_tier: int, count: int = 3) -> Array[String]:
	var avail: Array[String] = []
	for uid in pool_counts.keys():
		if int(pool_counts[uid]) > 0 and int(GameDatabase.units[uid]["tier"]) == exact_tier:
			avail.append(String(uid))
	if avail.size() < count:
		avail.clear()
		for uid in pool_counts.keys():
			if int(pool_counts[uid]) > 0 and int(GameDatabase.units[uid]["tier"]) <= exact_tier:
				avail.append(String(uid))
	if avail.is_empty():
		return []
	_shuffle_array(avail)
	var out: Array[String] = []
	for i in range(mini(count, avail.size())):
		var uid: String = avail[i]
		pool_counts[uid] = maxi(0, int(pool_counts[uid]) - 1)
		out.append(uid)
	return out


func _pool_return(uid: String, copies: int = 1) -> void:
	if not pool_counts.has(uid):
		return
	var tier: int = int(GameDatabase.units[uid]["tier"])
	var cap: int = int(GameDatabase.TIER_POOL_COPIES[tier])
	pool_counts[uid] = mini(cap, int(pool_counts[uid]) + copies)


func _random_edict_id(max_tier: int) -> String:
	var eligible: Array[String] = []
	for eid in GameDatabase.edicts.keys():
		if int(GameDatabase.edicts[eid]["tier"]) <= max_tier:
			eligible.append(String(eid))
	if eligible.is_empty():
		for eid in GameDatabase.edicts.keys():
			eligible.append(String(eid))
	return eligible[rng.randi_range(0, eligible.size() - 1)]


func _populate_shop(comm: Dictionary, preserve_frozen: bool = false) -> void:
	var shop_units: Array = comm["shop_units"]
	if preserve_frozen and bool(comm["shop_frozen"]) and not shop_units.is_empty():
		comm["shop_frozen"] = false
		if String(comm["shop_edict_id"]) == "":
			comm["shop_edict_id"] = _random_edict_id(int(comm["bastion_tier"]))
		return

	for old_u in shop_units:
		_pool_return(String(old_u["unit_id"]), 1)
	shop_units.clear()
	comm["shop_frozen"] = false

	var tier: int = int(comm["bastion_tier"])
	var slots: int = int(GameDatabase.CONCLAVE_SHOP_SLOTS[tier])
	var drawn: Array[String] = _pool_draw(tier, slots)
	var has_astrolabe: bool = (comm["relics"] as Array).has("astral_astrolabe")
	for uid in drawn:
		var u: Dictionary = _make_unit(uid)
		if has_astrolabe:
			_apply_buff(u, 1, 1)
		shop_units.append(u)

	comm["shop_edict_id"] = _random_edict_id(tier)


func _add_hand_card(comm: Dictionary, kind: String, title: String, unit_data: Dictionary = {}, edict_id: String = "", discover_tier: int = 1) -> bool:
	var hand: Array = comm["hand"]
	if hand.size() >= MAX_HAND:
		return false
	hand.append({
		"card_id": _next_id("card"),
		"kind": kind,
		"title": title,
		"unit": unit_data,
		"edict_id": edict_id,
		"discover_tier": discover_tier,
	})
	return true


func _count_non_ascended(comm: Dictionary, uid: String) -> int:
	var total: int = 0
	for u in comm["board"]:
		if String(u["unit_id"]) == uid and not bool(u["is_ascended"]):
			total += 1
	for c in comm["hand"]:
		if String(c["kind"]) == "UNIT":
			var cu: Dictionary = c["unit"]
			if not cu.is_empty() and String(cu["unit_id"]) == uid and not bool(cu["is_ascended"]):
				total += 1
	return total


func _check_and_fuse_ascension(comm: Dictionary, uid: String) -> Dictionary:
	var board: Array = comm["board"]
	var hand: Array = comm["hand"]
	var b_idx: Array[int] = []
	var h_idx: Array[int] = []

	for i in range(board.size()):
		if String(board[i]["unit_id"]) == uid and not bool(board[i]["is_ascended"]):
			b_idx.append(i)
	for i in range(hand.size()):
		if String(hand[i]["kind"]) == "UNIT":
			var cu: Dictionary = hand[i]["unit"]
			if not cu.is_empty() and String(cu["unit_id"]) == uid and not bool(cu["is_ascended"]):
				h_idx.append(i)

	if b_idx.size() + h_idx.size() < 3:
		return {}

	var defn: Dictionary = GameDatabase.units[uid]
	var base_atk: int = int(defn["attack"])
	var base_hp: int = int(defn["health"])
	var chosen: Array[Dictionary] = []
	var rem_b: Array[int] = []
	var rem_h: Array[int] = []

	for i in b_idx:
		if chosen.size() < 3:
			chosen.append(board[i])
			rem_b.append(i)
	for i in h_idx:
		if chosen.size() < 3:
			chosen.append(hand[i]["unit"])
			rem_h.append(i)

	var bonus_atk: int = 0
	var bonus_hp: int = 0
	var merged_kws: Array[String] = []
	for u in chosen:
		bonus_atk += maxi(0, int(u["attack"]) - base_atk)
		bonus_hp += maxi(0, int(u["max_health"]) - base_hp)
		for kw in u["keywords"]:
			if not merged_kws.has(String(kw)):
				merged_kws.append(String(kw))

	rem_b.sort()
	rem_b.reverse()
	for i in rem_b:
		board.remove_at(i)
	rem_h.sort()
	rem_h.reverse()
	for i in rem_h:
		hand.remove_at(i)

	var asc: Dictionary = _make_unit(uid, true, _next_id("asc"))
	asc["attack"] = int(asc["attack"]) + bonus_atk
	asc["health"] = int(asc["health"]) + bonus_hp
	asc["max_health"] = int(asc["max_health"]) + bonus_hp
	for kw in merged_kws:
		_add_kw(asc, kw)

	if hand.size() < MAX_HAND:
		_add_hand_card(comm, "UNIT", String(asc["name"]), asc)
	elif board.size() < MAX_WARBAND:
		board.append(asc)

	var oracle_tier: int = mini(6, int(comm["bastion_tier"]) + 1)
	_add_hand_card(comm, "ASCENSION_ORACLE", "Ascension Oracle (Tier %d)" % oracle_tier, {}, "", oracle_tier)
	if bool(comm["is_human"]):
		GlobalSignalBus.ascension_triggered.emit(String(asc["name"]))
	return asc


func refresh_shop(comm: Dictionary = {}) -> bool:
	var c: Dictionary = get_human() if comm.is_empty() else comm
	if int(c["free_refreshes"]) > 0:
		c["free_refreshes"] = int(c["free_refreshes"]) - 1
	elif int(c["crowns"]) >= 1:
		c["crowns"] = int(c["crowns"]) - 1
	else:
		if bool(c["is_human"]):
			GlobalSignalBus.status_message.emit("Not enough Aether Crowns to refresh.")
		return false
	_populate_shop(c, false)
	if bool(c["is_human"]):
		GlobalSignalBus.status_message.emit("Conclave refreshed.")
		GlobalSignalBus.state_updated.emit()
	return true


func toggle_freeze() -> void:
	var c: Dictionary = get_human()
	c["shop_frozen"] = not bool(c["shop_frozen"])
	GlobalSignalBus.status_message.emit("Conclave sealed." if bool(c["shop_frozen"]) else "Conclave unsealed.")
	GlobalSignalBus.state_updated.emit()


func elevate_bastion(comm: Dictionary = {}) -> bool:
	var c: Dictionary = get_human() if comm.is_empty() else comm
	var tier: int = int(c["bastion_tier"])
	var cost: int = int(c["upgrade_cost"])
	if tier >= 6 or int(c["crowns"]) < cost:
		if bool(c["is_human"]):
			GlobalSignalBus.status_message.emit("Cannot elevate Bastion Tier.")
		return false
	c["crowns"] = int(c["crowns"]) - cost
	tier += 1
	c["bastion_tier"] = tier
	c["upgrade_cost"] = int(GameDatabase.BASTION_UPGRADE_COSTS.get(tier, 0))
	if bool(c["is_human"]):
		GlobalSignalBus.status_message.emit("Bastion elevated to Tier %d!" % tier)
		GlobalSignalBus.state_updated.emit()
	return true


func recruit_unit(shop_idx: int, comm: Dictionary = {}) -> bool:
	var c: Dictionary = get_human() if comm.is_empty() else comm
	var shop_units: Array = c["shop_units"]
	if shop_idx < 0 or shop_idx >= shop_units.size():
		return false
	if int(c["crowns"]) < 3:
		if bool(c["is_human"]):
			GlobalSignalBus.status_message.emit("Recruiting costs 3 Aether Crowns.")
		return false

	var candidate: Dictionary = shop_units[shop_idx]
	var uid: String = String(candidate["unit_id"])
	var will_triple: bool = _count_non_ascended(c, uid) >= 2
	if (c["hand"] as Array).size() >= MAX_HAND and not will_triple:
		if bool(c["is_human"]):
			GlobalSignalBus.status_message.emit("Hand is full (max 10 cards).")
		return false

	c["crowns"] = int(c["crowns"]) - 3
	var unit: Dictionary = shop_units[shop_idx]
	shop_units.remove_at(shop_idx)
	(c["hand"] as Array).append({
		"card_id": _next_id("card"),
		"kind": "UNIT",
		"title": String(unit["name"]),
		"unit": unit,
		"edict_id": "",
		"discover_tier": 1,
	})
	var asc: Dictionary = _check_and_fuse_ascension(c, uid)
	if bool(c["is_human"]):
		if not asc.is_empty():
			GlobalSignalBus.status_message.emit("Ascension! 3x forged into %s!" % String(asc["name"]))
		else:
			GlobalSignalBus.status_message.emit("Recruited %s." % String(unit["name"]))
		GlobalSignalBus.state_updated.emit()
	return true


func dismiss_unit(board_idx: int, comm: Dictionary = {}) -> bool:
	var c: Dictionary = get_human() if comm.is_empty() else comm
	var board: Array = c["board"]
	if board_idx < 0 or board_idx >= board.size():
		return false
	var unit: Dictionary = board[board_idx]
	board.remove_at(board_idx)
	if not bool(unit["is_token"]):
		_pool_return(String(unit["unit_id"]), 3 if bool(unit["is_ascended"]) else 1)
	c["crowns"] = int(c["crowns"]) + 1
	if bool(c["is_human"]):
		GlobalSignalBus.status_message.emit("Dismissed %s (+1 Crown)." % String(unit["name"]))
		GlobalSignalBus.state_updated.emit()
	return true


func swap_board_units(idx_a: int, idx_b: int) -> bool:
	var board: Array = get_human()["board"]
	if idx_a < 0 or idx_b < 0 or idx_a >= board.size() or idx_b >= board.size() or idx_a == idx_b:
		return false
	var tmp: Variant = board[idx_a]
	board[idx_a] = board[idx_b]
	board[idx_b] = tmp
	GlobalSignalBus.status_message.emit("Warband formation updated.")
	GlobalSignalBus.state_updated.emit()
	return true


func _apply_vow(comm: Dictionary, source: Dictionary, target_idx: int) -> void:
	var defn: Dictionary = GameDatabase.units[String(source["unit_id"])]
	var vow: Dictionary = defn["vow"]
	if vow.is_empty():
		return
	var mult: int = 2 if bool(source["is_ascended"]) else 1
	var kind: String = String(vow.get("kind", ""))
	var board: Array = comm["board"]
	var t_tribe: String = String(vow.get("tribe", ""))

	if kind == "buff_random_ally":
		var allies: Array[Dictionary] = []
		for u in board:
			if String(u["instance_id"]) != String(source["instance_id"]):
				if t_tribe == "" or String(u["tribe"]) == t_tribe:
					allies.append(u)
		var target: Dictionary = {}
		if target_idx >= 0 and target_idx < board.size():
			var cand: Dictionary = board[target_idx]
			if String(cand["instance_id"]) != String(source["instance_id"]) and (t_tribe == "" or String(cand["tribe"]) == t_tribe):
				target = cand
		if target.is_empty() and not allies.is_empty():
			target = allies[rng.randi_range(0, allies.size() - 1)]
		if not target.is_empty():
			_apply_buff(target, int(vow.get("atk", 0)) * mult, int(vow.get("hp", 0)) * mult)
			if vow.has("grant_kw"):
				_add_kw(target, String(vow["grant_kw"]))
	elif kind == "buff_all_allies":
		for u in board:
			if t_tribe == "" or String(u["tribe"]) == t_tribe:
				_apply_buff(u, int(vow.get("atk", 0)) * mult, int(vow.get("hp", 0)) * mult)
	elif kind == "self_pact":
		_damage_commander(comm, int(vow.get("dmg", 1)))
		_apply_buff(source, int(vow.get("atk", 0)) * mult, int(vow.get("hp", 0)) * mult)
	elif kind == "add_edict":
		for _i in range(int(vow.get("count", 1)) * mult):
			var eid: String = _random_edict_id(int(comm["bastion_tier"]))
			_add_hand_card(comm, "ARCANE_EDICT", String(GameDatabase.edicts[eid]["name"]), {}, eid)
	elif kind == "add_shards":
		for _i in range(int(vow.get("count", 1)) * mult):
			_add_hand_card(comm, "BLOOD_SHARD", "Blood Shard (+1/+1)")
	elif kind == "gain_crowns":
		comm["crowns"] = int(comm["crowns"]) + int(vow.get("count", 2)) * mult
	elif kind == "crimson_awakening":
		for _i in range(int(vow.get("count", 3)) * mult):
			_add_hand_card(comm, "BLOOD_SHARD", "Blood Shard (+1/+1)")
		for u in board:
			if String(u["instance_id"]) != String(source["instance_id"]):
				_apply_buff(u, int(vow.get("atk", 2)) * mult, int(vow.get("hp", 2)) * mult)
	elif kind == "empower_conclave":
		comm["free_refreshes"] = int(comm["free_refreshes"]) + int(vow.get("count", 1)) * mult
		for u in comm["shop_units"]:
			_apply_buff(u, int(vow.get("atk", 2)) * mult, int(vow.get("hp", 2)) * mult)
	elif kind == "menagerie_buff":
		var seen_tribes: Dictionary = {}
		for u in board:
			if String(u["instance_id"]) != String(source["instance_id"]):
				var ut: String = String(u["tribe"])
				if not seen_tribes.has(ut):
					seen_tribes[ut] = []
				(seen_tribes[ut] as Array).append(u)
		for group_key in seen_tribes.keys():
			var grp: Array = seen_tribes[group_key]
			var chosen: Dictionary = grp[rng.randi_range(0, grp.size() - 1)]
			_apply_buff(chosen, int(vow.get("atk", 3)) * mult, int(vow.get("hp", 3)) * mult)


func _resolve_edict(comm: Dictionary, eid: String) -> void:
	var edict: Dictionary = GameDatabase.edicts[eid]
	var kind: String = String(edict["kind"])
	var board: Array = comm["board"]

	if kind == "buff_random_ally" and not board.is_empty():
		var t: Dictionary = board[rng.randi_range(0, board.size() - 1)]
		_apply_buff(t, int(edict["atk"]), int(edict["hp"]))
	elif kind == "add_shards":
		for _i in range(int(edict["count"])):
			_add_hand_card(comm, "BLOOD_SHARD", "Blood Shard (+1/+1)")
	elif kind == "increase_max_crowns":
		comm["bonus_max_crowns"] = int(comm["bonus_max_crowns"]) + int(edict["crowns"])
		comm["max_crowns"] = mini(13, int(comm["max_crowns"]) + int(edict["crowns"]))
		comm["crowns"] = int(comm["crowns"]) + int(edict["crowns"])
	elif kind == "buff_vanguard" and not board.is_empty():
		var t: Dictionary = board[rng.randi_range(0, board.size() - 1)]
		_apply_buff(t, int(edict["atk"]), int(edict["hp"]))
		_add_kw(t, "VANGUARD")
	elif kind == "recruit_random_tier":
		var drawn: Array[String] = _pool_draw(int(comm["bastion_tier"]), 1, int(comm["bastion_tier"]))
		if drawn.is_empty():
			drawn = _pool_draw(int(comm["bastion_tier"]), 1)
		if not drawn.is_empty():
			var u: Dictionary = _make_unit(drawn[0])
			_add_hand_card(comm, "UNIT", String(u["name"]), u)
	elif kind == "buff_all_allies":
		for u in board:
			_apply_buff(u, int(edict["atk"]), int(edict["hp"]))
	elif kind == "grant_aegis" and not board.is_empty():
		var no_aeg: Array[Dictionary] = []
		for u in board:
			if not _has_kw(u, "AEGIS"):
				no_aeg.append(u)
		var pool: Array = no_aeg if not no_aeg.is_empty() else board
		var t: Dictionary = pool[rng.randi_range(0, pool.size() - 1)]
		_add_kw(t, "AEGIS")
		_apply_buff(t, int(edict["atk"]), int(edict["hp"]))
	elif kind == "grant_undying" and not board.is_empty():
		var no_und: Array[Dictionary] = []
		for u in board:
			if not _has_kw(u, "UNDYING"):
				no_und.append(u)
		var pool: Array = no_und if not no_und.is_empty() else board
		_add_kw(pool[rng.randi_range(0, pool.size() - 1)], "UNDYING")
	elif kind == "buff_shop":
		comm["free_refreshes"] = int(comm["free_refreshes"]) + 1
		for u in comm["shop_units"]:
			_apply_buff(u, int(edict["atk"]), int(edict["hp"]))
	elif kind == "crowns_and_shards":
		comm["crowns"] = int(comm["crowns"]) + int(edict["crowns"])
		for _i in range(int(edict["count"])):
			_add_hand_card(comm, "BLOOD_SHARD", "Blood Shard (+1/+1)")
	elif kind == "add_oracle":
		var t_next: int = mini(6, int(comm["bastion_tier"]) + 1)
		_add_hand_card(comm, "ASCENSION_ORACLE", "Ascension Oracle (Tier %d)" % t_next, {}, "", t_next)

	for u in board:
		var on_ed: Dictionary = GameDatabase.units[String(u["unit_id"])]["on_edict"]
		if not on_ed.is_empty():
			var mult: int = 2 if bool(u["is_ascended"]) else 1
			_apply_buff(u, int(on_ed["atk"]) * mult, int(on_ed["hp"]) * mult)
	if String(comm["commander_id"]) == "rachel" and not board.is_empty():
		_apply_buff(board[rng.randi_range(0, board.size() - 1)], 1, 1)


func buy_shop_edict(comm: Dictionary = {}) -> bool:
	var c: Dictionary = get_human() if comm.is_empty() else comm
	var eid: String = String(c["shop_edict_id"])
	if eid == "":
		return false
	var edict: Dictionary = GameDatabase.edicts[eid]
	var discount: int = 1 if String(c["commander_id"]) == "rachel" else 0
	var cost: int = maxi(0, int(edict["cost"]) - discount)
	if int(c["crowns"]) < cost:
		if bool(c["is_human"]):
			GlobalSignalBus.status_message.emit("%s costs %d Crowns." % [String(edict["name"]), cost])
		return false
	c["crowns"] = int(c["crowns"]) - cost
	c["shop_edict_id"] = ""
	_resolve_edict(c, eid)
	if bool(c["is_human"]):
		GlobalSignalBus.status_message.emit("Cast Arcane Edict: %s." % String(edict["name"]))
		GlobalSignalBus.state_updated.emit()
	return true


func play_hand_card(hand_idx: int, target_idx: int = 0, comm: Dictionary = {}) -> bool:
	var c: Dictionary = get_human() if comm.is_empty() else comm
	var hand: Array = c["hand"]
	if hand_idx < 0 or hand_idx >= hand.size():
		return false
	var card: Dictionary = hand[hand_idx]
	var kind: String = String(card["kind"])
	var board: Array = c["board"]

	if kind == "UNIT":
		if board.size() >= MAX_WARBAND:
			if bool(c["is_human"]):
				GlobalSignalBus.status_message.emit("Warband full (max 7 units).")
			return false
		hand.remove_at(hand_idx)
		var u: Dictionary = card["unit"]
		board.append(u)
		_apply_vow(c, u, target_idx)
		if bool(c["is_human"]):
			GlobalSignalBus.status_message.emit("Deployed %s." % String(u["name"]))
			GlobalSignalBus.state_updated.emit()
		return true

	if kind == "BLOOD_SHARD":
		if board.is_empty():
			return false
		var t_i: int = clampi(target_idx, 0, board.size() - 1)
		hand.remove_at(hand_idx)
		var target: Dictionary = board[t_i]
		_apply_buff(target, 1, 1)
		var on_sh: Dictionary = GameDatabase.units[String(target["unit_id"])]["on_shard"]
		if not on_sh.is_empty():
			var mult: int = 2 if bool(target["is_ascended"]) else 1
			_apply_buff(target, int(on_sh["atk"]) * mult, int(on_sh["hp"]) * mult)
		if bool(c["is_human"]):
			GlobalSignalBus.status_message.emit("Blood Shard (+1/+1) applied to %s." % String(target["name"]))
			GlobalSignalBus.state_updated.emit()
		return true

	if kind == "FORGE_PLATING":
		if board.is_empty():
			return false
		var t_i: int = clampi(target_idx, 0, board.size() - 1)
		hand.remove_at(hand_idx)
		var target: Dictionary = board[t_i]
		_apply_buff(target, 2, 2)
		_add_kw(target, "AEGIS")
		if bool(c["is_human"]):
			GlobalSignalBus.status_message.emit("Forge Plating (+2/+2 & Aegis) applied to %s." % String(target["name"]))
			GlobalSignalBus.state_updated.emit()
		return true

	if kind == "ARCANE_EDICT":
		hand.remove_at(hand_idx)
		_resolve_edict(c, String(card["edict_id"]))
		if bool(c["is_human"]):
			GlobalSignalBus.status_message.emit("Cast %s." % String(card["title"]))
			GlobalSignalBus.state_updated.emit()
		return true

	if kind == "ASCENSION_ORACLE":
		if not (c["pending_oracle"] as Array).is_empty():
			return false
		hand.remove_at(hand_idx)
		var ids: Array[String] = _pool_draw_distinct(int(card["discover_tier"]), 3)
		for uid in ids:
			(c["pending_oracle"] as Array).append(_make_unit(uid))
		if bool(c["is_human"]):
			GlobalSignalBus.status_message.emit("Ascension Oracle opened!")
			GlobalSignalBus.state_updated.emit()
		return true

	return false


func pick_oracle_choice(choice_idx: int, comm: Dictionary = {}) -> bool:
	var c: Dictionary = get_human() if comm.is_empty() else comm
	var opts: Array = c["pending_oracle"]
	if choice_idx < 0 or choice_idx >= opts.size():
		return false
	var chosen: Dictionary = opts[choice_idx]
	opts.remove_at(choice_idx)
	for rem in opts:
		_pool_return(String(rem["unit_id"]), 1)
	opts.clear()

	_add_hand_card(c, "UNIT", String(chosen["name"]), chosen)
	_check_and_fuse_ascension(c, String(chosen["unit_id"]))
	if bool(c["is_human"]):
		GlobalSignalBus.status_message.emit("Oracle discovered %s." % String(chosen["name"]))
		GlobalSignalBus.state_updated.emit()
	return true


func use_commander_mandate(target_idx: int = 0, comm: Dictionary = {}) -> bool:
	var c: Dictionary = get_human() if comm.is_empty() else comm
	var cid: String = String(c["commander_id"])
	var defn: Dictionary = GameDatabase.commanders[cid]
	if bool(defn["is_passive"]) or bool(c["mandate_used"]):
		return false
	var cost: int = int(defn["mandate_cost"])
	if int(c["crowns"]) < cost:
		if bool(c["is_human"]):
			GlobalSignalBus.status_message.emit("%s costs %d Crowns." % [String(defn["mandate_name"]), cost])
		return false

	var board: Array = c["board"]
	if cid in ["rowan", "lyra", "caelen", "valora"] and board.is_empty():
		if bool(c["is_human"]):
			GlobalSignalBus.status_message.emit("Deploy a unit first to target your Mandate.")
		return false

	if cid == "carmilla":
		if int(c["health"]) <= 1:
			return false
		c["health"] = int(c["health"]) - 1
		c["crowns"] = int(c["crowns"]) + 1
		_add_hand_card(c, "BLOOD_SHARD", "Blood Shard (+1/+1)")
		_add_hand_card(c, "BLOOD_SHARD", "Blood Shard (+1/+1)")
		c["mandate_used"] = true
		if bool(c["is_human"]):
			GlobalSignalBus.status_message.emit("Sanguine Tithe: +1 Crown & 2 Blood Shards.")
			GlobalSignalBus.state_updated.emit()
		return true

	c["crowns"] = int(c["crowns"]) - cost
	c["mandate_used"] = true
	var t_i: int = clampi(target_idx, 0, maxi(0, board.size() - 1))

	if cid == "rowan" and not board.is_empty():
		_apply_buff(board[t_i], 1, 2)
		_add_kw(board[t_i], "VANGUARD")
	elif cid == "rachel":
		var eid: String = _random_edict_id(int(c["bastion_tier"]))
		_add_hand_card(c, "ARCANE_EDICT", String(GameDatabase.edicts[eid]["name"]), {}, eid)
		if not board.is_empty():
			_apply_buff(board[t_i], 1, 1)
	elif cid == "lyra" and not board.is_empty():
		var bonus: int = 3 if String(board[t_i]["tribe"]) == "sylvan" else 2
		_apply_buff(board[t_i], bonus, bonus)
	elif cid == "caelen" and not board.is_empty():
		_apply_buff(board[t_i], 3, 0)
		_add_kw(board[t_i], "SHROUD")
	elif cid == "valora" and not board.is_empty():
		_apply_buff(board[t_i], 2, 0)
		_add_kw(board[t_i], "AEGIS")

	if bool(c["is_human"]):
		GlobalSignalBus.status_message.emit("Activated Mandate: %s." % String(defn["mandate_name"]))
		GlobalSignalBus.state_updated.emit()
	return true


func pick_human_relic(choice_idx: int) -> bool:
	var h: Dictionary = get_human()
	var choices: Array = h["pending_relics"]
	if choice_idx < 0 or choice_idx >= choices.size():
		return false
	var rid: String = String(choices[choice_idx])
	_grant_relic(h, rid)
	choices.clear()
	phase = Phase.RECRUIT
	GlobalSignalBus.status_message.emit("Claimed Dawn Relic: %s!" % String(GameDatabase.relics[rid]["name"]))
	GlobalSignalBus.state_updated.emit()
	return true


func _grant_relic(comm: Dictionary, rid: String) -> void:
	var relics: Array = comm["relics"]
	if not relics.has(rid):
		relics.append(rid)
	if rid == "aether_sovereign_seal":
		comm["crowns_cap"] = 13
		comm["crowns"] = int(comm["crowns"]) + 3


func _damage_commander(comm: Dictionary, dmg: int) -> void:
	if dmg <= 0 or bool(comm["eliminated"]):
		return
	var rem: int = dmg
	var armor: int = int(comm["armor"])
	if armor > 0:
		var abs_amt: int = mini(armor, rem)
		comm["armor"] = armor - abs_amt
		rem -= abs_amt
	if rem > 0:
		comm["health"] = maxi(0, int(comm["health"]) - rem)
	if int(comm["health"]) <= 0:
		comm["eliminated"] = true


func _run_ai_turn(ai: Dictionary) -> void:
	if bool(ai["eliminated"]):
		return
	var pref: Array = GameDatabase.commanders[String(ai["commander_id"])]["preferred"]

	# Play hand cards
	var guard: int = 0
	while not (ai["hand"] as Array).is_empty() and guard < 15:
		guard += 1
		var progressed: bool = false
		var hand: Array = ai["hand"]
		for i in range(hand.size()):
			var card: Dictionary = hand[i]
			var k: String = String(card["kind"])
			if k == "ASCENSION_ORACLE":
				if play_hand_card(i, 0, ai) and not (ai["pending_oracle"] as Array).is_empty():
					pick_oracle_choice(0, ai)
				progressed = true
				break
			elif k in ["BLOOD_SHARD", "FORGE_PLATING", "ARCANE_EDICT"]:
				if not (ai["board"] as Array).is_empty() or k == "ARCANE_EDICT":
					play_hand_card(i, 0, ai)
					progressed = true
					break
			elif k == "UNIT" and (ai["board"] as Array).size() < MAX_WARBAND:
				play_hand_card(i, 0, ai)
				progressed = true
				break
		if not progressed:
			break

	# Elevate tier on curve
	if int(ai["bastion_tier"]) < 6 and int(ai["crowns"]) >= int(ai["upgrade_cost"]):
		if round_number in [2, 4, 6, 8, 10] or int(ai["upgrade_cost"]) <= 3:
			elevate_bastion(ai)

	# Recruit units
	var ops: int = 0
	while int(ai["crowns"]) >= 3 and ops < 7:
		ops += 1
		var shop_u: Array = ai["shop_units"]
		if shop_u.is_empty():
			if int(ai["crowns"]) >= 4 or int(ai["free_refreshes"]) > 0:
				refresh_shop(ai)
			else:
				break
		if shop_u.is_empty():
			break

		var best_i: int = 0
		var best_score: float = -999.0
		for idx in range(shop_u.size()):
			var u: Dictionary = shop_u[idx]
			var sc: float = float(u["tier"]) * 3.0 + float(u["attack"]) + float(u["health"])
			if pref.has(String(u["tribe"])):
				sc += 3.5
			if _count_non_ascended(ai, String(u["unit_id"])) == 2:
				sc += 18.0
			if sc > best_score:
				best_score = sc
				best_i = idx

		var board: Array = ai["board"]
		var chosen_u: Dictionary = shop_u[best_i]
		if board.size() >= MAX_WARBAND and _count_non_ascended(ai, String(chosen_u["unit_id"])) < 2:
			var weak_i: int = 0
			var weak_sc: float = 99999.0
			for idx in range(board.size()):
				var bu: Dictionary = board[idx]
				var wsc: float = float(bu["tier"]) * 2.0 + float(bu["attack"]) + float(bu["health"]) + (12.0 if bool(bu["is_ascended"]) else 0.0)
				if wsc < weak_sc:
					weak_sc = wsc
					weak_i = idx
			if best_score > weak_sc + 2.0:
				dismiss_unit(weak_i, ai)
			else:
				break

		if not recruit_unit(best_i, ai):
			break

		var inner: int = 0
		while not (ai["hand"] as Array).is_empty() and inner < 8:
			inner += 1
			var p: bool = false
			for h_i in range((ai["hand"] as Array).size()):
				var hc: Dictionary = ai["hand"][h_i]
				if String(hc["kind"]) == "ASCENSION_ORACLE":
					play_hand_card(h_i, 0, ai)
					if not (ai["pending_oracle"] as Array).is_empty():
						pick_oracle_choice(0, ai)
					p = true
					break
				elif String(hc["kind"]) == "UNIT" and (ai["board"] as Array).size() < MAX_WARBAND:
					play_hand_card(h_i, 0, ai)
					p = true
					break
			if not p:
				break

	if String(ai["shop_edict_id"]) != "":
		buy_shop_edict(ai)
	if not bool(ai["mandate_used"]):
		use_commander_mandate(0, ai)


func _pair_commanders() -> void:
	var alive: Array[Dictionary] = []
	for c in commanders:
		if not bool(c["eliminated"]):
			alive.append(c)
	current_pairings.clear()
	if alive.size() <= 1:
		return

	var slots: Array[int] = []
	for c in alive:
		slots.append(int(c["slot_index"]))
	_shuffle_array(slots)

	if slots.size() % 2 == 1:
		var solo_slot: int = slots.pop_back()
		var ghost_slot: int = solo_slot
		for c in commanders:
			if bool(c["eliminated"]):
				ghost_slot = int(c["slot_index"])
				break
		if ghost_slot == solo_slot:
			ghost_slot = slots[0]
		current_pairings.append({"a": solo_slot, "b": ghost_slot, "ghost": true})

	for i in range(0, slots.size(), 2):
		current_pairings.append({"a": slots[i], "b": slots[i + 1], "ghost": false})


func get_human_opponent() -> Dictionary:
	for p in current_pairings:
		if int(p["a"]) == 0:
			return {"commander": commanders[int(p["b"])], "ghost": bool(p["ghost"])}
		if int(p["b"]) == 0:
			return {"commander": commanders[int(p["a"])], "ghost": bool(p["ghost"])}
	return {}


func advance_to_next_round() -> void:
	if phase == Phase.GAME_OVER:
		return
	round_number += 1

	for comm in commanders:
		if bool(comm["eliminated"]):
			continue
		var has_seal: bool = (comm["relics"] as Array).has("aether_sovereign_seal")
		var cap: int = 13 if has_seal else int(comm["crowns_cap"])
		var max_c: int = mini(cap, mini(10, 2 + round_number) + int(comm["bonus_max_crowns"]))
		comm["max_crowns"] = max_c
		var bonus: int = (2 if (comm["relics"] as Array).has("oakhaven_purse") else 0) + (3 if has_seal else 0)
		comm["crowns"] = max_c + bonus
		if int(comm["bastion_tier"]) < 6 and int(comm["upgrade_cost"]) > 0:
			comm["upgrade_cost"] = maxi(0, int(comm["upgrade_cost"]) - 1)
		comm["mandate_used"] = false
		comm["free_refreshes"] = 1 if String(comm["commander_id"]) == "melissa" else 0

		if String(comm["commander_id"]) == "ironforge" and round_number % 2 == 0:
			_add_hand_card(comm, "FORGE_PLATING", "Forge Plating (+2/+2 & Aegis)")
		if (comm["relics"] as Array).has("crimson_chalice"):
			_add_hand_card(comm, "BLOOD_SHARD", "Blood Shard (+1/+1)")
			_add_hand_card(comm, "BLOOD_SHARD", "Blood Shard (+1/+1)")

		_populate_shop(comm, true)

		var r_kind: String = "LESSER" if round_number == 6 else ("GREATER" if round_number == 9 else "")
		if r_kind != "":
			var r_cands: Array[String] = []
			for rid in GameDatabase.relics.keys():
				if String(GameDatabase.relics[rid]["tier_kind"]) == r_kind and not (comm["relics"] as Array).has(String(rid)):
					r_cands.append(String(rid))
			_shuffle_array(r_cands)
			var offered: Array[String] = r_cands.slice(0, mini(3, r_cands.size()))
			if bool(comm["is_human"]):
				comm["pending_relics"] = offered
			elif not offered.is_empty():
				_grant_relic(comm, offered[0])

		if not bool(comm["is_human"]):
			_run_ai_turn(comm)

	_pair_commanders()
	var h: Dictionary = get_human()
	if not (h["pending_relics"] as Array).is_empty():
		phase = Phase.RELIC_SELECT
	else:
		phase = Phase.RECRUIT
	GlobalSignalBus.state_updated.emit()


func start_combat_phase() -> Dictionary:
	if phase == Phase.RELIC_SELECT and not (get_human()["pending_relics"] as Array).is_empty():
		pick_human_relic(0)
	phase = Phase.COMBAT

	for comm in commanders:
		if not bool(comm["eliminated"]) and (comm["relics"] as Array).has("sanctum_reliquary"):
			for u in comm["board"]:
				_apply_buff(u, 2, 2)

	var newly_dead: Array[Dictionary] = []
	var human_res: Dictionary = {}

	for p in current_pairings:
		var sa: int = int(p["a"])
		var sb: int = int(p["b"])
		var ghost: bool = bool(p["ghost"])
		var ca: Dictionary = commanders[sa]
		var cb: Dictionary = commanders[sb]

		var outcome: Dictionary = _resolve_combat(ca, cb)
		var winner: String = String(outcome["winner"])
		var dmg: int = int(outcome["damage"])

		if winner == "player":
			ca["wins"] = int(ca["wins"]) + 1
			ca["win_streak"] = int(ca["win_streak"]) + 1
			if not ghost:
				cb["losses"] = int(cb["losses"]) + 1
				cb["win_streak"] = 0
				_damage_commander(cb, dmg)
				if bool(cb["eliminated"]):
					newly_dead.append(cb)
		elif winner == "opponent":
			ca["losses"] = int(ca["losses"]) + 1
			ca["win_streak"] = 0
			_damage_commander(ca, dmg)
			if bool(ca["eliminated"]):
				newly_dead.append(ca)
			if not ghost:
				cb["wins"] = int(cb["wins"]) + 1
				cb["win_streak"] = int(cb["win_streak"]) + 1

		if sa == 0:
			human_res = outcome
			last_human_opponent_slot = sb
		elif sb == 0:
			var flipped: Dictionary = outcome.duplicate(true)
			flipped["winner"] = "opponent" if winner == "player" else ("player" if winner == "opponent" else "tie")
			human_res = flipped
			last_human_opponent_slot = sa

	newly_dead.sort_custom(func(a: Dictionary, b: Dictionary) -> bool:
		return (int(a["health"]) + int(a["armor"])) < (int(b["health"]) + int(b["armor"]))
	)
	for dead in newly_dead:
		if int(dead["placement"]) == 0:
			dead["placement"] = _elimination_cursor
			_elimination_cursor -= 1

	var alive: Array[Dictionary] = []
	for c in commanders:
		if not bool(c["eliminated"]):
			alive.append(c)

	if alive.size() <= 1 or bool(get_human()["eliminated"]):
		alive.sort_custom(func(a: Dictionary, b: Dictionary) -> bool:
			return (int(a["health"]) + int(a["armor"])) < (int(b["health"]) + int(b["armor"]))
		)
		for rem in alive:
			if int(rem["placement"]) == 0:
				rem["placement"] = _elimination_cursor
				_elimination_cursor -= 1
		if int(get_human()["placement"]) == 0:
			get_human()["placement"] = 1
		phase = Phase.GAME_OVER
		GlobalSignalBus.match_finished.emit(int(get_human()["placement"]))

	last_human_outcome = human_res
	if not human_res.is_empty():
		GlobalSignalBus.combat_sequence_ready.emit(human_res["events"], human_res)
	GlobalSignalBus.state_updated.emit()
	return human_res


func _resolve_combat(ca: Dictionary, cb: Dictionary) -> Dictionary:
	var boards: Dictionary = {"player": [], "opponent": []}
	for u in ca["board"]:
		(boards["player"] as Array).append(_clone_unit_for_combat(u, "_p"))
	for u in cb["board"]:
		(boards["opponent"] as Array).append(_clone_unit_for_combat(u, "_o"))

	var relics_map: Dictionary = {
		"player": ca["relics"],
		"opponent": cb["relics"],
	}
	_apply_combat_start_relics(boards["player"], relics_map["player"])
	_apply_combat_start_relics(boards["opponent"], relics_map["opponent"])

	var start_p: Array = []
	var start_o: Array = []
	for u in boards["player"]:
		start_p.append(u.duplicate(true))
	for u in boards["opponent"]:
		start_o.append(u.duplicate(true))

	var events: Array[Dictionary] = []
	var cursor: Dictionary = {"player": 0, "opponent": 0}
	var turn_side: String = "player" if (boards["player"] as Array).size() > (boards["opponent"] as Array).size() else (
		"opponent" if (boards["opponent"] as Array).size() > (boards["player"] as Array).size() else (
			"player" if rng.randi_range(0, 1) == 0 else "opponent"
		)
	)

	var steps: int = 0
	while not (boards["player"] as Array).is_empty() and not (boards["opponent"] as Array).is_empty() and steps < 250:
		steps += 1
		var opp_side: String = "opponent" if turn_side == "player" else "player"
		var atk_board: Array = boards[turn_side]
		var idx: int = int(cursor[turn_side]) % atk_board.size()
		var attacker: Dictionary = atk_board[idx]
		cursor[turn_side] = (idx + 1) % maxi(1, atk_board.size())

		if int(attacker["attack"]) > 0:
			var strikes: int = 2 if _has_kw(attacker, "FRENZY") else 1
			for _s in range(strikes):
				if not atk_board.has(attacker) or int(attacker["health"]) <= 0 or (boards[opp_side] as Array).is_empty():
					break
				var def_board: Array = boards[opp_side]
				var t_idx: int = _pick_target_idx(def_board)
				if t_idx < 0:
					break
				attacker["shroud_broken"] = true
				var primary: Dictionary = def_board[t_idx]
				var targets: Array[Dictionary] = [primary]
				if _has_kw(attacker, "SWEEP"):
					if t_idx - 1 >= 0:
						targets.append(def_board[t_idx - 1])
					if t_idx + 1 < def_board.size():
						targets.append(def_board[t_idx + 1])

				events.append({
					"kind": "ATTACK",
					"side": turn_side,
					"source_id": String(attacker["instance_id"]),
					"target_id": String(primary["instance_id"]),
					"value": int(attacker["attack"]),
					"desc": "%s (%d/%d) strikes %s (%d/%d)." % [String(attacker["name"]), int(attacker["attack"]), int(attacker["health"]), String(primary["name"]), int(primary["attack"]), int(primary["health"])],
				})

				for t in targets:
					_deal_strike_damage(attacker, t, turn_side, opp_side, events)
				_deal_strike_damage(primary, attacker, opp_side, turn_side, events)
				_cleanup_combat_deaths(boards, relics_map, cursor, events)

		turn_side = opp_side

	var p_alive: Array = boards["player"]
	var o_alive: Array = boards["opponent"]
	var winner: String = "tie"
	var dmg: int = 0
	if not p_alive.is_empty() and o_alive.is_empty():
		winner = "player"
		dmg = int(ca["bastion_tier"])
		for u in p_alive:
			dmg += int(u["tier"])
	elif not o_alive.is_empty() and p_alive.is_empty():
		winner = "opponent"
		dmg = int(cb["bastion_tier"])
		for u in o_alive:
			dmg += int(u["tier"])

	return {
		"winner": winner,
		"damage": dmg,
		"events": events,
		"start_player": start_p,
		"start_opponent": start_o,
		"end_player": p_alive,
		"end_opponent": o_alive,
	}


func _apply_combat_start_relics(board: Array, relic_list: Array) -> void:
	if board.is_empty():
		return
	if relic_list.has("briar_crown_band"):
		for u in board:
			_apply_buff(u, 2, 2)
	if relic_list.has("elder_root_effigy"):
		for u in board:
			_apply_buff(u, 5, 6)
	if relic_list.has("sunwarden_banner"):
		_add_kw(board[0], "AEGIS")
	if relic_list.has("molten_anvil_core"):
		for i in range(mini(2, board.size())):
			_apply_buff(board[i], 3, 0)
			_add_kw(board[i], "AEGIS")
	if relic_list.has("solar_heartstone"):
		var first: Dictionary = board[0]
		_apply_buff(first, mini(30, int(first["attack"])), 6)
	if relic_list.has("eternal_echo_bell"):
		for u in board:
			if _has_kw(u, "LAST_ECHO") or _has_kw(u, "UNDYING"):
				_apply_buff(u, 4, 4)


func _pick_target_idx(def_board: Array) -> int:
	if def_board.is_empty():
		return -1
	var non_shroud: Array[int] = []
	for i in range(def_board.size()):
		if not _has_kw(def_board[i], "SHROUD"):
			non_shroud.append(i)
	var eligible: Array[int] = non_shroud
	if eligible.is_empty():
		for i in range(def_board.size()):
			eligible.append(i)
	var vanguards: Array[int] = []
	for i in eligible:
		if _has_kw(def_board[i], "VANGUARD"):
			vanguards.append(i)
	var pool: Array[int] = vanguards if not vanguards.is_empty() else eligible
	return pool[rng.randi_range(0, pool.size() - 1)]


func _deal_strike_damage(attacker: Dictionary, defender: Dictionary, side: String, opp_side: String, events: Array[Dictionary]) -> void:
	var atk: int = int(attacker["attack"])
	if atk <= 0:
		return
	if _has_kw(defender, "AEGIS"):
		(defender["keywords"] as Array).erase("AEGIS")
		events.append({
			"kind": "AEGIS_POP",
			"side": opp_side,
			"source_id": String(attacker["instance_id"]),
			"target_id": String(defender["instance_id"]),
			"value": 0,
			"desc": "%s's Aegis absorbed the strike!" % String(defender["name"]),
		})
		return
	defender["health"] = int(defender["health"]) - atk
	if _has_kw(attacker, "BLIGHT") and not bool(attacker["blight_used"]):
		attacker["blight_used"] = true
		defender["health"] = 0
		events.append({
			"kind": "BLIGHT_KILL",
			"side": side,
			"source_id": String(attacker["instance_id"]),
			"target_id": String(defender["instance_id"]),
			"value": atk,
			"desc": "%s's Blight destroyed %s!" % [String(attacker["name"]), String(defender["name"])],
		})


func _cleanup_combat_deaths(boards: Dictionary, relics_map: Dictionary, cursor: Dictionary, events: Array[Dictionary]) -> void:
	for _pass in range(10):
		var any_died: bool = false
		for side in ["player", "opponent"]:
			var board: Array = boards[side]
			var dead_entries: Array[Dictionary] = []
			for i in range(board.size()):
				if int(board[i]["health"]) <= 0:
					dead_entries.append({"idx": i, "unit": board[i]})
			if dead_entries.is_empty():
				continue
			any_died = true
			for k in range(dead_entries.size() - 1, -1, -1):
				var idx: int = int(dead_entries[k]["idx"])
				var u: Dictionary = dead_entries[k]["unit"]
				board.remove_at(idx)
				events.append({"kind": "DEATH", "side": side, "source_id": String(u["instance_id"]), "target_id": "", "value": 0, "desc": "%s fell." % String(u["name"])})
				if idx < int(cursor[side]):
					cursor[side] = maxi(0, int(cursor[side]) - 1)

			for ally in board:
				var ret: Dictionary = GameDatabase.units[String(ally["unit_id"])]["retribution"]
				if not ret.is_empty():
					var thresh: int = int(ret["thresh"])
					ally["retribution_counter"] = int(ally["retribution_counter"]) + dead_entries.size()
					while int(ally["retribution_counter"]) >= thresh:
						ally["retribution_counter"] = int(ally["retribution_counter"]) - thresh
						_trigger_retribution_combat(side, ally, ret, boards, relics_map)

			var shift: int = 0
			for entry in dead_entries:
				var dead_u: Dictionary = entry["unit"]
				var insert_at: int = mini(board.size(), int(entry["idx"]) + shift)
				var before_len: int = board.size()
				_trigger_last_echo_combat(side, dead_u, insert_at, boards, relics_map, events)
				shift += board.size() - before_len

				if _has_kw(dead_u, "UNDYING") and not bool(dead_u["undying_used"]) and board.size() < MAX_WARBAND:
					var rev: Dictionary = _make_unit(String(dead_u["unit_id"]), bool(dead_u["is_ascended"]), _next_id("und_" + side))
					rev["health"] = 1
					rev["max_health"] = 1
					rev["undying_used"] = true
					if (relics_map[side] as Array).has("ossuary_lantern"):
						_apply_buff(rev, 2, 1)
					board.insert(mini(board.size(), int(entry["idx"]) + shift), rev)
					shift += 1
					events.append({"kind": "UNDYING", "side": side, "source_id": String(rev["instance_id"]), "target_id": "", "value": 1, "desc": "%s revived via Undying!" % String(rev["name"])})
		if not any_died:
			break


func _spawn_combat_token(side: String, token_id: String, pos: int, atk_b: int, hp_b: int, is_asc: bool, boards: Dictionary, relics_map: Dictionary) -> Dictionary:
	var board: Array = boards[side]
	if board.size() >= MAX_WARBAND:
		return {}
	var tok: Dictionary = _make_unit(token_id, is_asc, _next_id("tok_" + side))
	if atk_b != 0 or hp_b != 0:
		_apply_buff(tok, atk_b, hp_b)
	if (relics_map[side] as Array).has("ossuary_lantern"):
		_apply_buff(tok, 2, 1)
	board.insert(clampi(pos, 0, board.size()), tok)
	return tok


func _trigger_retribution_combat(side: String, unit: Dictionary, spec: Dictionary, boards: Dictionary, relics_map: Dictionary) -> void:
	var mult: int = 2 if bool(unit["is_ascended"]) else 1
	var kind: String = String(spec["kind"])
	var board: Array = boards[side]
	if kind == "buff_self":
		_apply_buff(unit, int(spec["atk"]) * mult, int(spec["hp"]) * mult)
	elif kind == "summon":
		var idx: int = board.find(unit) + 1
		_spawn_combat_token(side, String(spec["token"]), idx, int(spec.get("atk", 0)) * mult, int(spec.get("hp", 0)) * mult, bool(unit["is_ascended"]), boards, relics_map)
	elif kind == "grant_kw_ally":
		var kw: String = String(spec["grant_kw"])
		var t_tribe: String = String(spec.get("tribe", ""))
		for u in board:
			if (t_tribe == "" or String(u["tribe"]) == t_tribe) and not _has_kw(u, kw):
				_add_kw(u, kw)
				break
	elif kind == "buff_all_allies":
		var t_tribe: String = String(spec.get("tribe", ""))
		for u in board:
			if t_tribe == "" or String(u["tribe"]) == t_tribe:
				_apply_buff(u, int(spec["atk"]) * mult, int(spec["hp"]) * mult)


func _trigger_last_echo_combat(side: String, unit: Dictionary, death_slot: int, boards: Dictionary, relics_map: Dictionary, events: Array[Dictionary]) -> void:
	var spec: Dictionary = GameDatabase.units[String(unit["unit_id"])]["last_echo"]
	if spec.is_empty():
		return
	var mult: int = 2 if bool(unit["is_ascended"]) else 1
	var opp_side: String = "opponent" if side == "player" else "player"
	var kind: String = String(spec["kind"])

	if kind == "summon":
		for off in range(int(spec.get("count", 1))):
			var tok: Dictionary = _spawn_combat_token(side, String(spec["token"]), death_slot + off, int(spec.get("atk", 0)), int(spec.get("hp", 0)), bool(unit["is_ascended"]), boards, relics_map)
			if not tok.is_empty():
				events.append({"kind": "LAST_ECHO", "side": side, "source_id": String(unit["instance_id"]), "target_id": String(tok["instance_id"]), "value": 0, "desc": "%s summoned %s." % [String(unit["name"]), String(tok["name"])]})
	elif kind == "buff_all_allies":
		var t_tribe: String = String(spec.get("tribe", ""))
		for u in boards[side]:
			if t_tribe == "" or String(u["tribe"]) == t_tribe:
				_apply_buff(u, int(spec["atk"]) * mult, int(spec["hp"]) * mult)
	elif kind == "damage_random_enemy":
		var opp_b: Array = boards[opp_side]
		for _i in range(int(spec.get("count", 1)) * mult):
			var living: Array[Dictionary] = []
			for e in opp_b:
				if int(e["health"]) > 0:
					living.append(e)
			if living.is_empty():
				break
			var t: Dictionary = living[rng.randi_range(0, living.size() - 1)]
			if _has_kw(t, "AEGIS"):
				(t["keywords"] as Array).erase("AEGIS")
			else:
				t["health"] = int(t["health"]) - int(spec["dmg"])
	elif kind == "damage_all_enemies":
		var dmg: int = int(spec["dmg"]) * mult
		for t in boards[opp_side]:
			if int(t["health"]) <= 0:
				continue
			if _has_kw(t, "AEGIS"):
				(t["keywords"] as Array).erase("AEGIS")
			else:
				t["health"] = int(t["health"]) - dmg
	elif kind == "add_shards":
		for c in commanders:
			if (side == "player" and int(c["slot_index"]) == 0) or (side == "opponent" and int(c["slot_index"]) == last_human_opponent_slot):
				for _i in range(int(spec.get("count", 2)) * mult):
					_add_hand_card(c, "BLOOD_SHARD", "Blood Shard (+1/+1)")


func leaderboard() -> Array[Dictionary]:
	var alive: Array[Dictionary] = []
	var dead: Array[Dictionary] = []
	for c in commanders:
		if bool(c["eliminated"]):
			dead.append(c)
		else:
			alive.append(c)
	alive.sort_custom(func(a: Dictionary, b: Dictionary) -> bool:
		return (int(a["health"]) + int(a["armor"])) > (int(b["health"]) + int(b["armor"]))
	)
	dead.sort_custom(func(a: Dictionary, b: Dictionary) -> bool:
		return int(a["placement"]) < int(b["placement"])
	)
	var out: Array[Dictionary] = []
	out.append_array(alive)
	out.append_array(dead)
	return out
