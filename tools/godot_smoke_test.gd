extends SceneTree
## Headless GDScript verification running ConclaveEngine through an entire match.

func _initialize() -> void:
	var db_script: GDScript = load("res://scripts/autoload/game_database.gd")
	var bus_script: GDScript = load("res://scripts/autoload/global_signal_bus.gd")
	var bus: Node = bus_script.new()
	bus.name = "GlobalSignalBus"
	root.add_child(bus)
	var db: Node = db_script.new()
	db.name = "GameDatabase"
	root.add_child(db)

	var eng_script: GDScript = load("res://scripts/core/conclave_engine.gd")
	var eng: Variant = eng_script.new()
	eng.start_new_lobby(42)
	assert(eng.active_tribes.size() == 6, "Expected 5 active biome tribes + mercenary")
	assert(eng.commander_choices.size() == 3, "Expected 3 commander choices")
	eng.select_human_commander(eng.commander_choices[0])
	assert(eng.commanders.size() == 8, "Expected 8 commanders in lobby")

	var rounds: int = 0
	while eng.phase != eng.Phase.GAME_OVER and rounds < 35:
		rounds += 1
		if eng.phase == eng.Phase.RELIC_SELECT:
			eng.pick_human_relic(0)
		var h: Dictionary = eng.get_human()
		if int(h["bastion_tier"]) < 6 and int(h["crowns"]) >= int(h["upgrade_cost"]) and eng.round_number in [2, 4, 6]:
			eng.elevate_bastion()
		while int(h["crowns"]) >= 3 and not (h["shop_units"] as Array).is_empty():
			if not eng.recruit_unit(0):
				break
		for hi in range((h["hand"] as Array).size() - 1, -1, -1):
			eng.play_hand_card(hi, 0)
			if not (h["pending_oracle"] as Array).is_empty():
				eng.pick_oracle_choice(0)
		eng.start_combat_phase()
		if eng.phase != eng.Phase.GAME_OVER:
			eng.advance_to_next_round()

	assert(eng.phase == eng.Phase.GAME_OVER, "Match should reach GAME_OVER")
	print("GODOT_SMOKE_OK rounds=%d placement=%d" % [eng.round_number, int(eng.get_human()["placement"])])
	quit(0)
