import httpx
from typing import List, Optional
from .base import DiscoveryProvider
from .models import CanonicalEntity, ProviderSource, Rating
import logging
import os

logger = logging.getLogger(__name__)

class TMDBProvider(DiscoveryProvider):
    """Discovery provider using The Movie Database (TMDB) API."""
    @property
    def name(self) -> str:
        return "tmdb"

    def _headers(self) -> dict:
        token = os.getenv("API_READ_ACCESS_TOKEN", "")
        return {"Authorization": f"Bearer {token}", "accept": "application/json"}

    async def search(self, query: str, limit: int = 5) -> List[CanonicalEntity]:
        """Search for movies and TV shows on TMDB."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("https://api.themoviedb.org/3/search/multi",params={"query": query,"language": "en-US","include_adult": "true"},headers=self._headers(),timeout=10.0)
                response.raise_for_status()
                data        = response.json()
                results     = data.get("results", [])
                entities    = []
                for m in results[:limit]:
                    media_type = m.get("media_type")
                    
                    if media_type not in ["movie", "tv"]:
                        continue
                    
                    title           = m.get("title") or m.get("name") or "Unknown"
                    release_date    = m.get("release_date") or m.get("first_air_date") or ""
                    year            = int(release_date.split("-")[0]) if release_date else None
                    ratings         = {}
                    
                    if m.get("vote_average"):
                        ratings[self.name] = Rating(value=m["vote_average"],source="general",vote_count=m.get("vote_count"))
                    entity = CanonicalEntity(
                        title=title,
                        type="movie" if media_type == "movie" else "tv",
                        year=year,
                        poster_url=f"https://image.tmdb.org/t/p/w500{m['poster_path']}" if m.get("poster_path") else None,
                        overview=m.get("overview"),
                        genres=[str(gid) for gid in m.get("genre_ids", [])],
                        sources={
                            self.name: ProviderSource(
                                id=str(m["id"]),
                                provider_name=self.name,
                                raw_data=m
                            )
                        },
                        ratings=ratings,
                        primary_rating=ratings.get(self.name)
                    )
                    entities.append(entity)
                return entities
        except Exception as e:
            logger.error(f"TMDB search failed: {e}")
            return []

    async def get_details(self, provider_id: str) -> Optional[CanonicalEntity]:
        # Implementation for single item fetch
        return None
