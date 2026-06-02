from dataclasses import dataclass


@dataclass
class Edge:
    u: str
    v: str
    distance: float
    is_active: bool = True

    def to_dict(self):
        return {"u": self.u, "v": self.v, "distance": self.distance, "is_active": self.is_active}
