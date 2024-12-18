from typing import List
from enum import Enum
from dataclasses import dataclass


class Protocol(Enum):
    TCP = "tcp"
    UDP = "udp"

    @staticmethod
    def all():
        return [p.value for p in Protocol]


@dataclass
class Slice:

    name: str
    rules: dict
    switches: List[str]
    active: bool = True
    # bandwidth: float,

    def __post_init__(self):
        # Validate rules
        if "allowed_protocols" not in self.rules:
            self.rules["allowed_protocols"] = None  # If none, no rule is enforced
        else:
            for idx, p in enumerate(self.rules["allowed_protocols"]):
                if p not in Protocol.all():
                    raise ValueError(f"Invalid protocol {p}")
                self.rules["allowed_protocols"][idx] = Protocol(p)
        if "allowed_ports" not in self.rules:
            self.rules["allowed_ports"] = None  # If none, no rule is enforced
        
        rules = ["allowed_protocols", "allowed_ports"]
        if not any([self.rules[r] for r in rules]):
            raise ValueError("No rules specified")
