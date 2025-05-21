# gui/elevator_state.py
from typing import Dict, List
from request import Direction, RequestType, UserIntent, Request

NUM_ELEVATORS = 5
NUM_FLOORS = 20

class ElevatorStateManager:
    def __init__(self):
        self.states = {
            eid: {
                "floor": 1,
                "direction": Direction.NONE,
                "door_open": False,
                "internal_buttons": set()
            } for eid in range(1, NUM_ELEVATORS + 1)
        }
        self.external_buttons: Dict[int, Dict[str, bool]] = {
            floor: {"UP": False, "DOWN": False} for floor in range(1, NUM_FLOORS + 1)
        }

    def update_elevator(self, eid: int, floor: int, direction: Direction, door_open: bool):
        self.states[eid]["floor"] = floor
        self.states[eid]["direction"] = direction
        self.states[eid]["door_open"] = door_open

    def set_internal_button(self, eid: int, floor: int, active: bool):
        if active:
            self.states[eid]["internal_buttons"].add(floor)
        else:
            self.states[eid]["internal_buttons"].discard(floor)

    def set_external_button(self, floor: int, intent: UserIntent, active: bool):
        self.external_buttons[floor][intent.value] = active

    def get_snapshot(self):
        return {
            "elevators": self.states,
            "external_buttons": self.external_buttons
        }

state_manager = ElevatorStateManager()