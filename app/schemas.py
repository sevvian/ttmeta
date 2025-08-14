from typing import List, Optional, Union

from pydantic import BaseModel, Field


class ParseRequest(BaseModel):
    title: str

class ParseBatchRequest(BaseModel):
    titles: List[str]

class ParsedResult(BaseModel):
    title: Optional[str] = None
    year: Optional[int] = None
    season: Optional[int] = None
    episodes: List[int] = Field(default_factory=list)
    episode_range: Optional[str] = None
    quality: Optional[str] = None
    resolution: Optional[str] = None
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None
    audio_languages: List[str] = Field(default_factory=list)
    file_size: Optional[str] = None
    source: Optional[str] = None
    group: Optional[str] = None
    raw: str
    confidence: float = 0.0
    notes: Optional[str] = None
