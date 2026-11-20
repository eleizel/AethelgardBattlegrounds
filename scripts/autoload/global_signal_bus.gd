extends Node
## Global lifecycle event bus (< 15 core signals).

signal state_updated()
signal status_message(text: String)
signal combat_sequence_ready(events: Array, outcome: Dictionary)
signal ascension_triggered(unit_name: String)
signal match_finished(placement: int)
