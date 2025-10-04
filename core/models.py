from pydantic import BaseModel, model_validator, field_validator
from typing import Dict, List, Optional, Tuple


class SectionRequest(BaseModel):
    topicTitle: Optional[str] = None
    center: Optional[Tuple[float, float]] = None
    
    width: float = 1280
    height: float = 720

    @model_validator(mode='after')
    def check_at_least_one(self) -> 'SectionRequest':
        if self.topicTitle is None and self.center is None:
            raise ValueError('At least one of topicTitle or center must be provided')
        elif self.topicTitle is not None and self.center is not None:
            raise ValueError('Only one of topicTitle or center can be provided, not both')
        return self
    
    type: str = 'addSection'

class TitleRequest(BaseModel):
    topicTitle: str
    location: Tuple[float, float]
    size: int
    font: str
    color: Tuple[int, int, int]

    type: str = 'addTitle'

class StickerRequest(BaseModel):
    topicTitle: str
    content: str

    type: str = "addSticker"


class ColumnOfStickersRequest(BaseModel):
    topicTitle: str
    content: List[str]
    spacing: Optional[int] = 200

    type: str = "addStickerColumn"


class ImagesRequest(BaseModel):
    topicTitle: str
    content: List[str] # list of b64 ims. but raw bytes will more efficient
    spacing: Optional[int] = 220

    type: str = "addImages"


class TableRequest(BaseModel):
    topicTitle: str
    content: List[Dict[str, str]]

    type: str = "addTable"

    @field_validator("content")
    def validate_data(cls, content):
        if not content:
            raise ValueError("Content cannot be empty")

        # Ensure all dictionaries have the same keys
        keys = set(content[0].keys())
        for row in content[1:]:
            if set(row.keys()) != keys:
                raise ValueError("All data rows must have the same keys")

        return content


    def sort(self, key_value_pair_to_sort: dict):
        if not key_value_pair_to_sort:
            return self

        key, val = next(iter(key_value_pair_to_sort.items()))
        self.content = sorted(self.content, key=lambda d: val not in d[key])
        return self
    