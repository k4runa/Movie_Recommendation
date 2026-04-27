from pydantic import BaseModel, Field
from typing import Dict, List, Optional
import uuid

class Rating(BaseModel):
    value: float
    source: str
    vote_count: Optional[int] = None

class ProviderSource(BaseModel):
    id: str
    provider_name: str
    raw_data: Optional[Dict] = None

class CanonicalEntity(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    type: str # "movie", "tv", "anime"
    year: Optional[int] = None
    poster_url: Optional[str] = None
    overview: Optional[str] = None
    genres: List[str] = Field(default_factory=list)
    sources: Dict[str, ProviderSource] = Field(default_factory=dict)
    ratings: Dict[str, Rating] = Field(default_factory=dict)
    primary_rating: Optional[Rating] = None

    def merge_with(self, other: "CanonicalEntity") -> "CanonicalEntity":
        """Merge another entity into this one, intelligently picking the best metadata."""
        # 1. Merge sources & ratings
        self.sources.update({k: v for k, v in other.sources.items() if k not in self.sources})
        self.ratings.update({k: v for k, v in other.ratings.items() if k not in self.ratings})

        # 2. Prefer longer/better overview
        if other.overview:
            if not self.overview or len(other.overview) > len(self.overview):
                self.overview = other.overview

        # 3. Prefer TMDB poster if available (usually better resolution)
        if "tmdb" in other.sources and other.poster_url:
            self.poster_url = other.poster_url
        elif not self.poster_url and other.poster_url:
            self.poster_url = other.poster_url

        # 4. Fill missing metadata
        if not self.year and other.year:
            self.year = other.year
            
        # 5. Prioritize 'anime' type
        if self.type != 'anime' and other.type == 'anime':
            self.type = 'anime'
            
        # 6. Set primary rating if missing
        if not self.primary_rating:
            if "omdb" in self.ratings: self.primary_rating = self.ratings["omdb"]
            elif "tmdb" in self.ratings: self.primary_rating = self.ratings["tmdb"]
            elif "anilist" in self.ratings: self.primary_rating = self.ratings["anilist"]
            
        # 6. Combine unique genres
        self.genres = list(set(self.genres + other.genres))
        
        return self
