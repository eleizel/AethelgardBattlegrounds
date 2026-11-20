class_name UnitMedallion3D
extends Node3D
## 3D tactical medallion piece displaying unit sprite, stats, Aegis bubble, and combat tweens.

const MEDALLION_STD_SCENE: PackedScene = preload("res://assets/models/unit_medallion.glb")
const MEDALLION_ASC_SCENE: PackedScene = preload("res://assets/models/unit_medallion_ascended.glb")

var instance_id: String = ""
var _base_pos: Vector3 = Vector3.ZERO
var _mesh_root: Node3D
var _sprite_3d: Sprite3D
var _atk_label: Label3D
var _hp_label: Label3D
var _kw_label: Label3D
var _aegis_dome: MeshInstance3D
var _select_ring: MeshInstance3D
var _active_tween: Tween


func _init() -> void:
	pass


func _exit_tree() -> void:
	if _active_tween != null and _active_tween.is_valid():
		_active_tween.kill()


func setup(unit_data: Dictionary, is_selected: bool = false, is_opponent: bool = false) -> void:
	instance_id = String(unit_data.get("instance_id", ""))
	var is_asc: bool = bool(unit_data.get("is_ascended", false))

	for c in get_children():
		c.queue_free()

	var scene_res: PackedScene = MEDALLION_ASC_SCENE if is_asc else MEDALLION_STD_SCENE
	_mesh_root = scene_res.instantiate() as Node3D
	add_child(_mesh_root)
	if is_opponent:
		_mesh_root.rotation_degrees.y = 180.0

	_sprite_3d = Sprite3D.new()
	_sprite_3d.texture = GameDatabase.get_unit_sprite(String(unit_data.get("sprite", "")))
	_sprite_3d.pixel_size = 0.0115
	_sprite_3d.texture_filter = BaseMaterial3D.TEXTURE_FILTER_NEAREST
	_sprite_3d.position = Vector3(0.0, 0.56, -0.04 if not is_opponent else 0.04)
	_sprite_3d.rotation_degrees.x = -24.0
	_sprite_3d.shaded = false
	add_child(_sprite_3d)

	_atk_label = Label3D.new()
	_atk_label.font_size = 44
	_atk_label.outline_size = 10
	_atk_label.modulate = Color("#FFB84D")
	_atk_label.position = Vector3(-0.34, 0.28, 0.36)
	_atk_label.rotation_degrees.x = -38.0
	add_child(_atk_label)

	_hp_label = Label3D.new()
	_hp_label.font_size = 44
	_hp_label.outline_size = 10
	_hp_label.modulate = Color("#FF6472")
	_hp_label.position = Vector3(0.34, 0.28, 0.36)
	_hp_label.rotation_degrees.x = -38.0
	add_child(_hp_label)

	_kw_label = Label3D.new()
	_kw_label.font_size = 24
	_kw_label.outline_size = 6
	_kw_label.modulate = Color("#6CE6FF")
	_kw_label.position = Vector3(0.0, 1.05, 0.0)
	_kw_label.rotation_degrees.x = -24.0
	add_child(_kw_label)

	var dome_mesh := SphereMesh.new()
	dome_mesh.radius = 0.52
	dome_mesh.height = 0.90
	var dome_mat := StandardMaterial3D.new()
	dome_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	dome_mat.albedo_color = Color(0.35, 0.85, 1.0, 0.24)
	dome_mat.emission_enabled = true
	dome_mat.emission = Color(0.28, 0.80, 1.0, 1.0)
	dome_mat.emission_energy_multiplier = 0.8
	dome_mesh.material = dome_mat
	_aegis_dome = MeshInstance3D.new()
	_aegis_dome.mesh = dome_mesh
	_aegis_dome.position = Vector3(0.0, 0.45, 0.0)
	add_child(_aegis_dome)

	var ring_mesh := TorusMesh.new()
	ring_mesh.inner_radius = 0.46
	ring_mesh.outer_radius = 0.52
	var ring_mat := StandardMaterial3D.new()
	ring_mat.albedo_color = Color("#4FE3FF")
	ring_mat.emission_enabled = true
	ring_mat.emission = Color("#4FE3FF")
	ring_mat.emission_energy_multiplier = 1.4
	ring_mesh.material = ring_mat
	_select_ring = MeshInstance3D.new()
	_select_ring.mesh = ring_mesh
	_select_ring.position = Vector3(0.0, 0.04, 0.0)
	_select_ring.visible = is_selected
	add_child(_select_ring)

	refresh_visuals(unit_data, is_selected)


func refresh_visuals(unit_data: Dictionary, is_selected: bool = false) -> void:
	if _atk_label == null:
		return
	_atk_label.text = str(int(unit_data.get("attack", 0)))
	_hp_label.text = str(int(unit_data.get("health", 0)))

	var kws: Array = unit_data.get("keywords", [])
	var tags: Array[String] = []
	for k in kws:
		var ks: String = String(k)
		if ks == "VANGUARD":
			tags.append("VAN")
		elif ks == "AEGIS":
			tags.append("AEG")
		elif ks == "BLIGHT":
			tags.append("BLI")
		elif ks == "FRENZY":
			tags.append("FRZ")
		elif ks == "UNDYING":
			tags.append("UND")
		elif ks == "SWEEP":
			tags.append("SWP")
		elif ks == "SHROUD":
			tags.append("SHR")
	_kw_label.text = " ".join(tags)
	_aegis_dome.visible = kws.has("AEGIS")
	_select_ring.visible = is_selected
	if _sprite_3d != null:
		_sprite_3d.modulate = Color(1.0, 1.0, 1.0, 0.55) if (kws.has("SHROUD") and not bool(unit_data.get("shroud_broken", false))) else Color.WHITE


func set_slot_position(pos: Vector3) -> void:
	_base_pos = pos
	position = pos


func play_attack_lunge(target_pos: Vector3) -> void:
	if not is_inside_tree():
		return
	if _active_tween != null and _active_tween.is_valid():
		_active_tween.kill()
	var mid_pos := _base_pos.lerp(target_pos, 0.72) + Vector3(0.0, 0.25, 0.0)
	_active_tween = create_tween()
	_active_tween.tween_property(self, "position", mid_pos, 0.14).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	_active_tween.tween_property(self, "position", _base_pos, 0.16).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)


func play_hit_flash() -> void:
	if not is_inside_tree() or _sprite_3d == null:
		return
	var tw := create_tween()
	tw.tween_property(_sprite_3d, "modulate", Color(1.6, 0.35, 0.35, 1.0), 0.08)
	tw.tween_property(_sprite_3d, "modulate", Color.WHITE, 0.14)
