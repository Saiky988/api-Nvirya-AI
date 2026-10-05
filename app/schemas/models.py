from typing import Optional
from pydantic import BaseModel

class ModelCard(BaseModel):
    id: str
    object: str = "model"
    created: int = 1700000000
    owned_by: str = "nvirya"

class ModelListResponse(BaseModel):
    object: str = "list"
    data: list[ModelCard]
