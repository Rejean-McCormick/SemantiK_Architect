# app/core/domain/semantic_models.py
from typing import List, Union
from pydantic import BaseModel, Field

class UniversalNode(BaseModel):
    """
    The GF-Native Frame (Prototype Path).
    
    Unlike Ninai's strict validation, this model maps 1:1 to Grammatical Framework 
    structures without enforcing a whitelist of allowed functions.
    
    It enables the 'Architect' to prototype new functions (e.g. mkIsAProperty) 
    and pass them directly to the PGF power.
    """
    function: str = Field(..., description="The name of the GF function (e.g. mkFact)")
    args: List[Union[str, int, float, 'UniversalNode']] = Field(
        default_factory=list,
        description="Arguments can be primitives (Strings) or nested Function Calls."
    )

# Enable recursion (Node -> Args -> Node)
UniversalNode.model_rebuild()