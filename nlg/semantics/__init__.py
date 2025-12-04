from semantics.types import BioFrame, Event, BioFrame as BioFrame, Event as Event
from typing import Protocol

class Frame(Protocol):
    frame_type: str
__all__ = ["Frame", "BioFrame", "EventFrame"]
