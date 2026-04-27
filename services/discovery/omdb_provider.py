import httpx
import os
import logging
from typing import List, Optional
from .base import DiscoveryProvider
from .models import CanonicalEntity, Rating, ProviderSource

from ..resilience import resilient_call, CircuitBreaker

logger = logging.getLogger(__name__)

_omdb_cb = CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)

class OMDBProvider(DiscoveryProvider):
    """Discovery provider using the OMDb API for general movie metadata."""
    def __init__(self):
        self.api_key = os.getenv("OMDB_API_KEY")
        self.base_url = "https://www.omdbapi.com/"

    @property
    def name(self) -> str:
        return "omdb"

    @resilient_call(retry_on=(httpx.HTTPError, ValueError), circuit_breaker=_omdb_cb)
    async def _do_search(self, query: str, limit: int) -> List[CanonicalEntity]:
        async with httpx.AsyncClient() as client:
            params = {
                "apikey": self.api_key,
                "s": query,
                "r": "json"
            }
            response = await client.get(self.base_url, params=params, timeout=5.0)
            response.raise_for_status()
            data = response.json()

            if data.get("Response") == "False":
                return []

            results = []
            for item in data.get("Search", [])[:limit]:
                entity = CanonicalEntity(
                    id=f"omdb-{item['imdbID']}",
                    title=item["Title"],
                    year=int(item["Year"][:4]) if item["Year"][:4].isdigit() else None,
                    type="movie" if item["Type"] == "movie" else "tv",
                    poster_url=item["Poster"] if item["Poster"] != "N/A" else None,
                    sources={
                        "omdb": ProviderSource(
                            id=item["imdbID"],
                            provider_name="omdb"
                        )
                    }
                )
                results.append(entity)
            return results

    async def search(self, query: str, limit: int = 5) -> List[CanonicalEntity]:
        """Search for movies on OMDb."""
        if not self.api_key:
            logger.warning("OMDb API key not found. Skipping OMDb search.")
            return []
        try:
            return await self._do_search(query, limit) or []
        except Exception as e:
            logger.error(f"OMDb search failed: {e}")
            return []

    @resilient_call(retry_on=(httpx.HTTPError, ValueError), circuit_breaker=_omdb_cb)
    async def _do_get_details(self, provider_id: str) -> Optional[CanonicalEntity]:
        async with httpx.AsyncClient() as client:
            params = {
                "apikey": self.api_key,
                "i": provider_id,
                "plot": "full"
            }
            response = await client.get(self.base_url, params=params, timeout=5.0)
            response.raise_for_status()
            item = response.json()

            if item.get("Response") == "False":
                return None

            ratings = {}
            imdb_rating = item.get("imdbRating")
            if imdb_rating and imdb_rating != "N/A":
                ratings["imdb"] = Rating(
                    value=float(imdb_rating),
                    source="omdb",
                    vote_count=int(item.get("imdbVotes", "0").replace(",", "")) if item.get("imdbVotes") != "N/A" else None
                )

            return CanonicalEntity(
                id=f"omdb-{item['imdbID']}",
                title=item["Title"],
                year=int(item["Year"][:4]) if item["Year"][:4].isdigit() else None,
                type="movie" if item["Type"] == "movie" else "tv",
                poster_url=item["Poster"] if item["Poster"] != "N/A" else None,
                overview=item.get("Plot") if item.get("Plot") != "N/A" else None,
                genres=[g.strip() for g in item.get("Genre", "").split(",")] if item.get("Genre") != "N/A" else [],
                ratings=ratings,
                primary_rating=ratings.get("imdb"),
                sources={
                    "omdb": ProviderSource(
                        id=item["imdbID"],
                        provider_name="omdb"
                    )
                }
            )

    async def get_details(self, provider_id: str) -> Optional[CanonicalEntity]:
        """Fetch detailed movie metadata from OMDb by IMDb ID."""
        if not self.api_key:
            return None
        try:
            return await self._do_get_details(provider_id)
        except Exception as e:
            logger.error(f"OMDb detail fetch failed: {e}")
            return None
