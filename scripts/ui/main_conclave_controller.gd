extends Node3D
## Main 3D War Table arena and 2D ornate Conclave HUD controller.

const WAR_TABLE_SCENE: PackedScene = preload("res://assets/models/conclave_war_table.glb")
const RELIC_PEDESTAL_SCENE: PackedScene = preload("res://assets/models/dawn_relic_pedestal.glb")
const AETHER_CROWN_SCENE: PackedScene = preload("res://assets/models/aether_crown.glb")

const PLAYER_ROW_Z: float = 1.05
const OPPONENT_ROW_Z: float = -1.05
const TABLE_TOP_Y: float = 0.94

var engine: ConclaveEngine = ConclaveEngine.new()
var selected_board_idx: int = -1
var _animating_combat: bool = false
var _skip_combat_anim: bool = false

var _arena_root: Node3D
var _board_pieces_root: Node3D
var _medallions_by_id: Dictionary = {}

# HUD references
var _hud_layer: CanvasLayer
var _status_label: Label
var _round_label: Label
var _tribes_label: Label
var _crowns_label: Label
var _tier_label: Label
var _elevate_btn: Button
var _refresh_btn: Button
var _freeze_btn: Button
var _combat_btn: Button
var _leaderboard_box: VBoxContainer
var _shop_box: HBoxContainer
var _edict_btn: Button
var _board_controls_box: HBoxContainer
var _swap_left_btn: Button
var _swap_right_btn: Button
var _dismiss_btn: Button
var _hand_box: HBoxContainer
var _commander_portrait: TextureRect
var _commander_stats_label: Label
var _mandate_btn: Button
var _relics_label: Label

# Modals
var _commander_modal: PanelContainer
var _commander_cards_box: HBoxContainer
var _modal_tribes_label: Label
var _choice_modal: PanelContainer
var _choice_title_label: Label
var _choice_cards_box: HBoxContainer
var _gameover_modal: PanelContainer
var _gameover_title: Label
var _gameover_rows: VBoxContainer

var _title_font: Font
var _body_font: Font


func _ready() -> void:
	_load_fonts()
	_build_3d_arena()
	_build_hud()
	GlobalSignalBus.state_updated.connect(_refresh_all_ui)
	GlobalSignalBus.status_message.connect(_on_status_message)
	GlobalSignalBus.combat_sequence_ready.connect(_on_combat_sequence_ready)
	engine.start_new_lobby()


func _load_fonts() -> void:
	if ResourceLoader.exists("res://assets/fonts/CinzelDecorative-Bold.ttf"):
		_title_font = ResourceLoader.load("res://assets/fonts/CinzelDecorative-Bold.ttf") as Font
	if ResourceLoader.exists("res://assets/fonts/alagard.ttf"):
		_body_font = ResourceLoader.load("res://assets/fonts/alagard.ttf") as Font


func _build_3d_arena() -> void:
	_arena_root = Node3D.new()
	_arena_root.name = "Arena3D"
	add_child(_arena_root)

	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color("#110E18")
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color("#342A48")
	env.ambient_light_energy = 0.75
	var world_env := WorldEnvironment.new()
	world_env.environment = env
	_arena_root.add_child(world_env)

	var dir_light := DirectionalLight3D.new()
	dir_light.rotation_degrees = Vector3(-52.0, 26.0, 0.0)
	dir_light.light_energy = 1.45
	dir_light.light_color = Color("#FFEBD2")
	dir_light.shadow_enabled = true
	_arena_root.add_child(dir_light)

	for lx in [-4.8, 4.8]:
		var torch := OmniLight3D.new()
		torch.position = Vector3(lx, 2.5, 0.2)
		torch.light_color = Color("#FF9D42")
		torch.light_energy = 2.4
		torch.omni_range = 9.0
		_arena_root.add_child(torch)

	var cam := Camera3D.new()
	cam.position = Vector3(0.0, 5.2, 5.1)
	cam.fov = 44.0
	_arena_root.add_child(cam)
	cam.look_at(Vector3(0.0, 0.78, 0.15), Vector3.UP)

	var table_inst := WAR_TABLE_SCENE.instantiate() as Node3D
	_arena_root.add_child(table_inst)

	for px in [-5.0, 5.0]:
		var ped := RELIC_PEDESTAL_SCENE.instantiate() as Node3D
		ped.position = Vector3(px, 0.0, 0.0)
		_arena_root.add_child(ped)

	for ci in range(3):
		var crown := AETHER_CROWN_SCENE.instantiate() as Node3D
		crown.position = Vector3(3.85 - ci * 0.12, TABLE_TOP_Y + ci * 0.06, 1.82)
		_arena_root.add_child(crown)

	_board_pieces_root = Node3D.new()
	_board_pieces_root.name = "BoardPieces"
	_arena_root.add_child(_board_pieces_root)


func _style_panel(panel: PanelContainer, bg: Color = Color(0.11, 0.09, 0.16, 0.92), border: Color = Color("#C99E44")) -> void:
	var sb := StyleBoxFlat.new()
	sb.bg_color = bg
	sb.border_color = border
	sb.set_border_width_all(2)
	sb.set_corner_radius_all(8)
	sb.set_content_margin_all(8)
	panel.add_theme_stylebox_override("panel", sb)


func _make_btn(text: String, min_w: int = 100, accent: Color = Color("#3A2E52")) -> Button:
	var btn := Button.new()
	btn.text = text
	btn.custom_minimum_size = Vector2(min_w, 34)
	var sb := StyleBoxFlat.new()
	sb.bg_color = accent
	sb.border_color = Color("#D4AC4B")
	sb.set_border_width_all(1)
	sb.set_corner_radius_all(6)
	sb.set_content_margin_all(6)
	btn.add_theme_stylebox_override("normal", sb)
	if _body_font != null:
		btn.add_theme_font_override("font", _body_font)
	return btn


func _build_hud() -> void:
	_hud_layer = CanvasLayer.new()
	add_child(_hud_layer)

	var root_margin := MarginContainer.new()
	root_margin.set_anchors_preset(Control.PRESET_FULL_RECT)
	root_margin.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root_margin.add_theme_constant_override("margin_left", 10)
	root_margin.add_theme_constant_override("margin_right", 10)
	root_margin.add_theme_constant_override("margin_top", 10)
	root_margin.add_theme_constant_override("margin_bottom", 10)
	_hud_layer.add_child(root_margin)

	var main_hbox := HBoxContainer.new()
	main_hbox.mouse_filter = Control.MOUSE_FILTER_IGNORE
	main_hbox.add_theme_constant_override("separation", 10)
	root_margin.add_child(main_hbox)

	# Left Sidebar: Leaderboard
	var side_panel := PanelContainer.new()
	side_panel.custom_minimum_size = Vector2(236, 0)
	_style_panel(side_panel)
	main_hbox.add_child(side_panel)

	var side_vbox := VBoxContainer.new()
	side_vbox.add_theme_constant_override("separation", 6)
	side_panel.add_child(side_vbox)

	var lb_title := Label.new()
	lb_title.text = "CONCLAVE LOBBY"
	lb_title.add_theme_color_override("font_color", Color("#E8BF5A"))
	if _title_font != null:
		lb_title.add_theme_font_override("font", _title_font)
	side_vbox.add_child(lb_title)

	_round_label = Label.new()
	_round_label.text = "Round 0"
	side_vbox.add_child(_round_label)

	_tribes_label = Label.new()
	_tribes_label.autowrap_mode = TextServer.AUTOWRAP_WORD
	_tribes_label.add_theme_font_size_override("font_size", 11)
	_tribes_label.add_theme_color_override("font_color", Color("#B7ADC9"))
	side_vbox.add_child(_tribes_label)

	_leaderboard_box = VBoxContainer.new()
	_leaderboard_box.add_theme_constant_override("separation", 4)
	side_vbox.add_child(_leaderboard_box)

	# Right Main Column
	var right_vbox := VBoxContainer.new()
	right_vbox.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	right_vbox.mouse_filter = Control.MOUSE_FILTER_IGNORE
	right_vbox.add_theme_constant_override("separation", 8)
	main_hbox.add_child(right_vbox)

	# Top Control & Shop Panel
	var top_panel := PanelContainer.new()
	_style_panel(top_panel)
	right_vbox.add_child(top_panel)

	var top_vbox := VBoxContainer.new()
	top_vbox.add_theme_constant_override("separation", 6)
	top_panel.add_child(top_vbox)

	var bar_row := HBoxContainer.new()
	bar_row.add_theme_constant_override("separation", 8)
	top_vbox.add_child(bar_row)

	_status_label = Label.new()
	_status_label.text = "Welcome to the War Conclave."
	_status_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	bar_row.add_child(_status_label)

	_crowns_label = Label.new()
	_crowns_label.add_theme_color_override("font_color", Color("#F2C94C"))
	bar_row.add_child(_crowns_label)

	_tier_label = Label.new()
	_tier_label.add_theme_color_override("font_color", Color("#72DDF7"))
	bar_row.add_child(_tier_label)

	_elevate_btn = _make_btn("Elevate", 112)
	_elevate_btn.pressed.connect(func() -> void: engine.elevate_bastion())
	bar_row.add_child(_elevate_btn)

	_refresh_btn = _make_btn("Refresh (1g)", 106)
	_refresh_btn.pressed.connect(func() -> void: engine.refresh_shop())
	bar_row.add_child(_refresh_btn)

	_freeze_btn = _make_btn("Seal (0g)", 84)
	_freeze_btn.pressed.connect(func() -> void: engine.toggle_freeze())
	bar_row.add_child(_freeze_btn)

	_combat_btn = _make_btn("COMBAT!", 112, Color("#8F2633"))
	_combat_btn.pressed.connect(_on_combat_pressed)
	bar_row.add_child(_combat_btn)

	# Shop Offer Row
	var shop_row := HBoxContainer.new()
	shop_row.add_theme_constant_override("separation", 8)
	top_vbox.add_child(shop_row)

	_shop_box = HBoxContainer.new()
	_shop_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_shop_box.add_theme_constant_override("separation", 6)
	shop_row.add_child(_shop_box)

	_edict_btn = _make_btn("Arcane Edict", 172, Color("#291E46"))
	_edict_btn.custom_minimum_size = Vector2(172, 76)
	_edict_btn.pressed.connect(func() -> void: engine.buy_shop_edict())
	shop_row.add_child(_edict_btn)

	# Transparent 3D Viewport Spacer
	var spacer := Control.new()
	spacer.size_flags_vertical = Control.SIZE_EXPAND_FILL
	spacer.mouse_filter = Control.MOUSE_FILTER_IGNORE
	right_vbox.add_child(spacer)

	# Warband Quick-Controls Bar above Hand
	var board_bar := PanelContainer.new()
	_style_panel(board_bar, Color(0.11, 0.09, 0.16, 0.85))
	right_vbox.add_child(board_bar)

	var board_bar_vbox := VBoxContainer.new()
	board_bar_vbox.add_theme_constant_override("separation", 4)
	board_bar.add_child(board_bar_vbox)

	var board_hdr := HBoxContainer.new()
	board_hdr.add_theme_constant_override("separation", 6)
	board_bar_vbox.add_child(board_hdr)

	var bh_lbl := Label.new()
	bh_lbl.text = "WARBAND FORMATION (3D War Table) — Click slot to Select / Target:"
	bh_lbl.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	bh_lbl.add_theme_font_size_override("font_size", 12)
	bh_lbl.add_theme_color_override("font_color", Color("#E8BF5A"))
	board_hdr.add_child(bh_lbl)

	_swap_left_btn = _make_btn("<- Left", 80)
	_swap_left_btn.pressed.connect(_on_swap_left)
	board_hdr.add_child(_swap_left_btn)

	_swap_right_btn = _make_btn("Right ->", 80)
	_swap_right_btn.pressed.connect(_on_swap_right)
	board_hdr.add_child(_swap_right_btn)

	_dismiss_btn = _make_btn("Dismiss (+1g)", 110, Color("#6C242B"))
	_dismiss_btn.pressed.connect(_on_dismiss_selected)
	board_hdr.add_child(_dismiss_btn)

	_board_controls_box = HBoxContainer.new()
	_board_controls_box.add_theme_constant_override("separation", 6)
	board_bar_vbox.add_child(_board_controls_box)

	# Bottom Commander & Hand Bar
	var bot_panel := PanelContainer.new()
	_style_panel(bot_panel)
	right_vbox.add_child(bot_panel)

	var bot_hbox := HBoxContainer.new()
	bot_hbox.add_theme_constant_override("separation", 10)
	bot_panel.add_child(bot_hbox)

	_commander_portrait = TextureRect.new()
	_commander_portrait.custom_minimum_size = Vector2(72, 72)
	_commander_portrait.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_commander_portrait.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	bot_hbox.add_child(_commander_portrait)

	var comm_vbox := VBoxContainer.new()
	comm_vbox.custom_minimum_size = Vector2(215, 0)
	bot_hbox.add_child(comm_vbox)

	_commander_stats_label = Label.new()
	_commander_stats_label.add_theme_color_override("font_color", Color("#E8BF5A"))
	comm_vbox.add_child(_commander_stats_label)

	_mandate_btn = _make_btn("Mandate", 210, Color("#2E244E"))
	_mandate_btn.pressed.connect(_on_mandate_pressed)
	comm_vbox.add_child(_mandate_btn)

	_relics_label = Label.new()
	_relics_label.add_theme_font_size_override("font_size", 11)
	_relics_label.add_theme_color_override("font_color", Color("#72DDF7"))
	comm_vbox.add_child(_relics_label)

	var hand_scroll := ScrollContainer.new()
	hand_scroll.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	hand_scroll.custom_minimum_size = Vector2(0, 86)
	bot_hbox.add_child(hand_scroll)

	_hand_box = HBoxContainer.new()
	_hand_box.add_theme_constant_override("separation", 6)
	hand_scroll.add_child(_hand_box)

	_build_modals()


func _build_modals() -> void:
	# 1. Commander Selection Modal
	_commander_modal = PanelContainer.new()
	_commander_modal.set_anchors_preset(Control.PRESET_CENTER)
	_commander_modal.custom_minimum_size = Vector2(920, 480)
	_commander_modal.offset_left = -460
	_commander_modal.offset_right = 460
	_commander_modal.offset_top = -240
	_commander_modal.offset_bottom = 240
	_style_panel(_commander_modal, Color(0.08, 0.06, 0.13, 0.97))
	_hud_layer.add_child(_commander_modal)

	var cm_v := VBoxContainer.new()
	cm_v.add_theme_constant_override("separation", 12)
	_commander_modal.add_child(cm_v)

	var cm_title := Label.new()
	cm_title.text = "AETHELGARD: CONCLAVE OF WAR — CHOOSE YOUR COMMANDER"
	cm_title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	cm_title.add_theme_color_override("font_color", Color("#E8BF5A"))
	if _title_font != null:
		cm_title.add_theme_font_override("font", _title_font)
	cm_v.add_child(cm_title)

	_modal_tribes_label = Label.new()
	_modal_tribes_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	cm_v.add_child(_modal_tribes_label)

	_commander_cards_box = HBoxContainer.new()
	_commander_cards_box.alignment = BoxContainer.ALIGNMENT_CENTER
	_commander_cards_box.add_theme_constant_override("separation", 16)
	_commander_cards_box.size_flags_vertical = Control.SIZE_EXPAND_FILL
	cm_v.add_child(_commander_cards_box)

	# 2. Dawn Relic / Ascension Oracle Modal
	_choice_modal = PanelContainer.new()
	_choice_modal.set_anchors_preset(Control.PRESET_CENTER)
	_choice_modal.custom_minimum_size = Vector2(820, 340)
	_choice_modal.offset_left = -410
	_choice_modal.offset_right = 410
	_choice_modal.offset_top = -170
	_choice_modal.offset_bottom = 170
	_style_panel(_choice_modal, Color(0.08, 0.06, 0.13, 0.97))
	_choice_modal.visible = false
	_hud_layer.add_child(_choice_modal)

	var ch_v := VBoxContainer.new()
	ch_v.add_theme_constant_override("separation", 12)
	_choice_modal.add_child(ch_v)

	_choice_title_label = Label.new()
	_choice_title_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_choice_title_label.add_theme_color_override("font_color", Color("#E8BF5A"))
	ch_v.add_child(_choice_title_label)

	_choice_cards_box = HBoxContainer.new()
	_choice_cards_box.alignment = BoxContainer.ALIGNMENT_CENTER
	_choice_cards_box.add_theme_constant_override("separation", 14)
	_choice_cards_box.size_flags_vertical = Control.SIZE_EXPAND_FILL
	ch_v.add_child(_choice_cards_box)

	# 3. Game Over Modal
	_gameover_modal = PanelContainer.new()
	_gameover_modal.set_anchors_preset(Control.PRESET_CENTER)
	_gameover_modal.custom_minimum_size = Vector2(540, 420)
	_gameover_modal.offset_left = -270
	_gameover_modal.offset_right = 270
	_gameover_modal.offset_top = -210
	_gameover_modal.offset_bottom = 210
	_style_panel(_gameover_modal, Color(0.08, 0.06, 0.13, 0.97))
	_gameover_modal.visible = false
	_hud_layer.add_child(_gameover_modal)

	var go_v := VBoxContainer.new()
	go_v.add_theme_constant_override("separation", 10)
	_gameover_modal.add_child(go_v)

	_gameover_title = Label.new()
	_gameover_title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_gameover_title.add_theme_color_override("font_color", Color("#E8BF5A"))
	go_v.add_child(_gameover_title)

	_gameover_rows = VBoxContainer.new()
	_gameover_rows.size_flags_vertical = Control.SIZE_EXPAND_FILL
	go_v.add_child(_gameover_rows)

	var new_btn := _make_btn("NEW CONCLAVE", 180, Color("#5A4216"))
	new_btn.pressed.connect(func() -> void: engine.start_new_lobby())
	go_v.add_child(new_btn)


func _clear_children(node: Node) -> void:
	for c in node.get_children():
		c.queue_free()


func _on_status_message(text: String) -> void:
	if _status_label != null:
		_status_label.text = text


func _refresh_all_ui() -> void:
	_commander_modal.visible = engine.phase == ConclaveEngine.Phase.COMMANDER_SELECT
	_gameover_modal.visible = engine.phase == ConclaveEngine.Phase.GAME_OVER

	if engine.phase == ConclaveEngine.Phase.COMMANDER_SELECT:
		_render_commander_modal()
		_clear_3d_board()
		return

	var human: Dictionary = engine.get_human()
	if human.is_empty():
		return

	_round_label.text = "Round %d" % engine.round_number
	var exiled_name: String = String(GameDatabase.tribes[engine.exiled_tribe]["name"])
	_tribes_label.text = "Exiled Tribe: %s\n(5 Active + Mercenaries)" % exiled_name
	_crowns_label.text = "Crowns: %d/%d" % [int(human["crowns"]), int(human["max_crowns"])]
	_tier_label.text = "Bastion Tier %d" % int(human["bastion_tier"])
	_elevate_btn.text = "Tier MAX" if int(human["bastion_tier"]) >= 6 else "Elevate (%dg)" % int(human["upgrade_cost"])
	_refresh_btn.text = "Refresh (Free)" if int(human["free_refreshes"]) > 0 else "Refresh (1g)"
	_freeze_btn.text = "Unseal" if bool(human["shop_frozen"]) else "Seal (0g)"

	_render_leaderboard()
	_render_shop(human)
	_render_board_controls(human)
	_render_commander_bar(human)
	_render_hand(human)

	if not _animating_combat:
		_sync_3d_board(human["board"], _get_opponent_preview_board())

	if engine.phase == ConclaveEngine.Phase.RELIC_SELECT and not (human["pending_relics"] as Array).is_empty():
		_render_relic_modal(human["pending_relics"])
	elif not (human["pending_oracle"] as Array).is_empty():
		_render_oracle_modal(human["pending_oracle"])
	else:
		_choice_modal.visible = false

	if engine.phase == ConclaveEngine.Phase.GAME_OVER:
		_render_gameover_modal()


func _get_opponent_preview_board() -> Array:
	var pair: Dictionary = engine.get_human_opponent()
	if pair.is_empty():
		return []
	var opp: Dictionary = pair["commander"]
	return opp["board"]


func _render_commander_modal() -> void:
	var act_names: Array[String] = []
	for t in engine.active_tribes:
		if t != GameDatabase.NEUTRAL_TRIBE:
			act_names.append(String(GameDatabase.tribes[t]["name"]))
	_modal_tribes_label.text = "Active Tribes: %s  |  Exiled: %s" % [", ".join(act_names), String(GameDatabase.tribes[engine.exiled_tribe]["name"])]

	_clear_children(_commander_cards_box)
	for cid in engine.commander_choices:
		var defn: Dictionary = GameDatabase.commanders[cid]
		var p := PanelContainer.new()
		p.custom_minimum_size = Vector2(270, 340)
		_style_panel(p, Color(0.14, 0.11, 0.22, 0.96))
		var v := VBoxContainer.new()
		v.add_theme_constant_override("separation", 6)
		p.add_child(v)

		var tex_rect := TextureRect.new()
		tex_rect.texture = GameDatabase.get_portrait_texture(String(defn["portrait"]))
		tex_rect.custom_minimum_size = Vector2(110, 110)
		tex_rect.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		tex_rect.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		v.add_child(tex_rect)

		var nm := Label.new()
		nm.text = "%s\n(%s)" % [String(defn["name"]), String(defn["title"])]
		nm.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		nm.add_theme_color_override("font_color", Color("#E8BF5A"))
		v.add_child(nm)

		var vit := Label.new()
		vit.text = "HP: %d  |  Armor: %d" % [int(defn["health"]), int(defn["armor"])]
		vit.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		v.add_child(vit)

		var md := Label.new()
		md.text = "%s: %s" % [String(defn["mandate_name"]), String(defn["mandate_desc"])]
		md.autowrap_mode = TextServer.AUTOWRAP_WORD
		md.size_flags_vertical = Control.SIZE_EXPAND_FILL
		v.add_child(md)

		var btn := _make_btn("Choose Commander", 200, Color("#5A4216"))
		btn.pressed.connect(engine.select_human_commander.bind(cid))
		v.add_child(btn)
		_commander_cards_box.add_child(p)


func _render_leaderboard() -> void:
	_clear_children(_leaderboard_box)
	var pair: Dictionary = engine.get_human_opponent()
	var opp_slot: int = int(pair["commander"]["slot_index"]) if not pair.is_empty() else -1

	for comm in engine.leaderboard():
		var slot: int = int(comm["slot_index"])
		var is_hum: bool = bool(comm["is_human"])
		var is_opp: bool = slot == opp_slot
		var dead: bool = bool(comm["eliminated"])

		var row := PanelContainer.new()
		var bg := Color(0.18, 0.14, 0.28, 0.95) if is_hum else (Color(0.28, 0.12, 0.16, 0.95) if is_opp else Color(0.12, 0.10, 0.18, 0.85))
		if dead:
			bg = Color(0.08, 0.08, 0.10, 0.65)
		var border := Color("#E8BF5A") if is_hum else (Color("#D64550") if is_opp else Color("#4F4566"))
		_style_panel(row, bg, border)

		var lbl := Label.new()
		var tag := " (YOU)" if is_hum else (" (VS)" if is_opp else (" [OUT]" if dead else ""))
		lbl.text = "%s%s\nHP %d+%d | Tier %d" % [String(comm["name"]), tag, int(comm["health"]), int(comm["armor"]), int(comm["bastion_tier"])]
		lbl.add_theme_font_size_override("font_size", 11)
		row.add_child(lbl)
		_leaderboard_box.add_child(row)


func _render_shop(human: Dictionary) -> void:
	_clear_children(_shop_box)
	var shop_u: Array = human["shop_units"]
	for i in range(shop_u.size()):
		var u: Dictionary = shop_u[i]
		var btn := _make_btn("", 130, Color("#241F36"))
		btn.custom_minimum_size = Vector2(130, 76)
		btn.text = "%s\nT%d %s | %d/%d\nRecruit (3g)" % [
			String(u["name"]).substr(0, 15),
			int(u["tier"]),
			String(u["tribe"]).substr(0, 3).to_upper(),
			int(u["attack"]),
			int(u["health"]),
		]
		btn.tooltip_text = String(GameDatabase.units[String(u["unit_id"])]["desc"])
		btn.pressed.connect(engine.recruit_unit.bind(i))
		_shop_box.add_child(btn)

	var eid: String = String(human["shop_edict_id"])
	if eid == "":
		_edict_btn.visible = false
	else:
		_edict_btn.visible = true
		var ed: Dictionary = GameDatabase.edicts[eid]
		var cost: int = maxi(0, int(ed["cost"]) - (1 if String(human["commander_id"]) == "rachel" else 0))
		_edict_btn.text = "EDICT: %s\nCost: %dg" % [String(ed["name"]).substr(0, 14), cost]
		_edict_btn.tooltip_text = String(ed["desc"])


func _render_board_controls(human: Dictionary) -> void:
	_clear_children(_board_controls_box)
	var board: Array = human["board"]
	if selected_board_idx >= board.size():
		selected_board_idx = -1
	for i in range(board.size()):
		var u: Dictionary = board[i]
		var is_sel: bool = (i == selected_board_idx)
		var btn := _make_btn(
			"%s\n%d/%d%s" % [String(u["name"]).substr(0, 12), int(u["attack"]), int(u["health"]), " *" if bool(u["is_ascended"]) else ""],
			112,
			Color("#3D305E") if is_sel else Color("#201B2E"),
		)
		btn.custom_minimum_size = Vector2(112, 46)
		btn.pressed.connect(_on_board_slot_clicked.bind(i))
		_board_controls_box.add_child(btn)

	var has_sel := selected_board_idx >= 0 and selected_board_idx < board.size()
	_swap_left_btn.disabled = not has_sel or selected_board_idx == 0
	_swap_right_btn.disabled = not has_sel or selected_board_idx >= board.size() - 1
	_dismiss_btn.disabled = not has_sel


func _render_commander_bar(human: Dictionary) -> void:
	_commander_portrait.texture = GameDatabase.get_portrait_texture(String(human["portrait"]))
	_commander_stats_label.text = "%s\nHP: %d  |  Armor: %d" % [String(human["name"]), int(human["health"]), int(human["armor"])]
	var defn: Dictionary = GameDatabase.commanders[String(human["commander_id"])]
	_mandate_btn.text = "%s (%s)" % [String(defn["mandate_name"]), "Passive" if bool(defn["is_passive"]) else "%dg" % int(defn["mandate_cost"])]
	_mandate_btn.tooltip_text = String(defn["mandate_desc"])
	_mandate_btn.disabled = bool(defn["is_passive"]) or bool(human["mandate_used"])

	var rel_names: Array[String] = []
	for rid in human["relics"]:
		rel_names.append(String(GameDatabase.relics[rid]["name"]))
	_relics_label.text = "Relics: %s" % (", ".join(rel_names) if not rel_names.is_empty() else "None yet (Round 6 & 9)")


func _render_hand(human: Dictionary) -> void:
	_clear_children(_hand_box)
	var hand: Array = human["hand"]
	for i in range(hand.size()):
		var card: Dictionary = hand[i]
		var kind: String = String(card["kind"])
		var btn := _make_btn("", 118, Color("#40311B") if kind == "ASCENSION_ORACLE" else Color("#241F36"))
		btn.custom_minimum_size = Vector2(118, 76)
		if kind == "UNIT":
			var u: Dictionary = card["unit"]
			btn.text = "%s\n%d/%d\n[Deploy]" % [String(u["name"]).substr(0, 13), int(u["attack"]), int(u["health"])]
			btn.tooltip_text = String(GameDatabase.units[String(u["unit_id"])]["desc"])
		else:
			btn.text = "%s\n[Play]" % String(card["title"]).substr(0, 14)
		btn.pressed.connect(_on_hand_card_pressed.bind(i))
		_hand_box.add_child(btn)


func _render_relic_modal(relic_ids: Array) -> void:
	_choice_title_label.text = "CHOOSE A DAWN RELIC"
	_clear_children(_choice_cards_box)
	for i in range(relic_ids.size()):
		var rid: String = String(relic_ids[i])
		var relic: Dictionary = GameDatabase.relics[rid]
		var btn := _make_btn("%s\n[%s]\n\n%s" % [String(relic["name"]), String(relic["tier_kind"]), String(relic["desc"])], 240, Color("#241C38"))
		btn.custom_minimum_size = Vector2(240, 200)
		btn.pressed.connect(engine.pick_human_relic.bind(i))
		_choice_cards_box.add_child(btn)
	_choice_modal.visible = true


func _render_oracle_modal(options: Array) -> void:
	_choice_title_label.text = "ASCENSION ORACLE — DISCOVER A UNIT"
	_clear_children(_choice_cards_box)
	for i in range(options.size()):
		var u: Dictionary = options[i]
		var btn := _make_btn("%s\nTier %d %s\n%d / %d\n\n%s" % [
			String(u["name"]),
			int(u["tier"]),
			String(u["tribe"]).capitalize(),
			int(u["attack"]),
			int(u["health"]),
			String(GameDatabase.units[String(u["unit_id"])]["desc"]),
		], 240, Color("#241C38"))
		btn.custom_minimum_size = Vector2(240, 200)
		btn.pressed.connect(func() -> void: engine.pick_oracle_choice(i))
		_choice_cards_box.add_child(btn)
	_choice_modal.visible = true


func _render_gameover_modal() -> void:
	var h: Dictionary = engine.get_human()
	var place: int = int(h["placement"])
	_gameover_title.text = "VICTORY! CONCLAVE CHAMPION (#1)" if place == 1 else "ELIMINATED — PLACE #%d" % place
	_clear_children(_gameover_rows)
	for idx in range(engine.leaderboard().size()):
		var c: Dictionary = engine.leaderboard()[idx]
		var lbl := Label.new()
		lbl.text = "#%d  %-22s  Tier %d  HP %d+%d" % [idx + 1, String(c["name"]), int(c["bastion_tier"]), int(c["health"]), int(c["armor"])]
		if bool(c["is_human"]):
			lbl.add_theme_color_override("font_color", Color("#E8BF5A"))
		_gameover_rows.add_child(lbl)


func _clear_3d_board() -> void:
	_medallions_by_id.clear()
	if _board_pieces_root != null:
		for c in _board_pieces_root.get_children():
			c.queue_free()


func _sync_3d_board(player_units: Array, opponent_units: Array) -> void:
	_clear_3d_board()
	_spawn_3d_row(player_units, PLAYER_ROW_Z, false)
	_spawn_3d_row(opponent_units, OPPONENT_ROW_Z, true)


func _spawn_3d_row(units_arr: Array, z_pos: float, is_opponent: bool) -> void:
	var n: int = units_arr.size()
	for i in range(n):
		var u: Dictionary = units_arr[i]
		var x_pos: float = (float(i) - float(n - 1) * 0.5) * 1.12
		var piece := UnitMedallion3D.new()
		_board_pieces_root.add_child(piece)
		piece.setup(u, (not is_opponent and i == selected_board_idx), is_opponent)
		piece.set_slot_position(Vector3(x_pos, TABLE_TOP_Y, z_pos))
		_medallions_by_id[String(u["instance_id"])] = piece


func _on_board_slot_clicked(idx: int) -> void:
	if selected_board_idx == idx:
		selected_board_idx = -1
	else:
		selected_board_idx = idx
	_refresh_all_ui()


func _on_swap_left() -> void:
	if selected_board_idx > 0:
		engine.swap_board_units(selected_board_idx, selected_board_idx - 1)
		selected_board_idx -= 1


func _on_swap_right() -> void:
	if selected_board_idx >= 0 and selected_board_idx < (engine.get_human()["board"] as Array).size() - 1:
		engine.swap_board_units(selected_board_idx, selected_board_idx + 1)
		selected_board_idx += 1


func _on_dismiss_selected() -> void:
	if selected_board_idx >= 0:
		engine.dismiss_unit(selected_board_idx)
		selected_board_idx = -1


func _on_hand_card_pressed(hand_idx: int) -> void:
	var target_idx: int = maxi(0, selected_board_idx)
	engine.play_hand_card(hand_idx, target_idx)


func _on_mandate_pressed() -> void:
	var target_idx: int = maxi(0, selected_board_idx)
	engine.use_commander_mandate(target_idx)


func _on_combat_pressed() -> void:
	if _animating_combat:
		_skip_combat_anim = true
		return
	selected_board_idx = -1
	engine.start_combat_phase()


func _on_combat_sequence_ready(events: Array, outcome: Dictionary) -> void:
	_animating_combat = true
	_skip_combat_anim = false
	_combat_btn.text = "Skip Anim"
	_sync_3d_board(outcome["start_player"], outcome["start_opponent"])

	for ev in events:
		if _skip_combat_anim or not is_inside_tree():
			break
		var kind: String = String(ev["kind"])
		var src_id: String = String(ev["source_id"])
		var tgt_id: String = String(ev["target_id"])
		_status_label.text = String(ev["desc"])

		if kind == "ATTACK":
			var src_piece: UnitMedallion3D = _medallions_by_id.get(src_id) as UnitMedallion3D
			var tgt_piece: UnitMedallion3D = _medallions_by_id.get(tgt_id) as UnitMedallion3D
			if src_piece != null and tgt_piece != null:
				src_piece.play_attack_lunge(tgt_piece.global_position)
				tgt_piece.play_hit_flash()
			await get_tree().create_timer(0.28).timeout
		elif kind == "DEATH":
			var dead_piece: UnitMedallion3D = _medallions_by_id.get(src_id) as UnitMedallion3D
			if dead_piece != null:
				dead_piece.visible = false
			await get_tree().create_timer(0.14).timeout
		else:
			await get_tree().create_timer(0.12).timeout

	_animating_combat = false
	_combat_btn.text = "COMBAT!"

	var winner: String = String(outcome["winner"])
	var dmg: int = int(outcome["damage"])
	if winner == "player":
		_status_label.text = "Victory! Dealt %d damage." % dmg
	elif winner == "opponent":
		_status_label.text = "Defeat! Took %d damage." % dmg
	else:
		_status_label.text = "Stalemate! 0 damage taken."

	if engine.phase != ConclaveEngine.Phase.GAME_OVER:
		engine.advance_to_next_round()
	else:
		_refresh_all_ui()
