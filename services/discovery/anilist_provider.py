import httpx
from typing import List, Optional, Any
from .base import DiscoveryProvider
from .models import CanonicalEntity, ProviderSource, Rating
import logging
import re

logger = logging.getLogger(__name__)

def strip_html(text: Optional[str]) -> Optional[str]:
    if not text: return text
    return re.sub('<[^<]+?>', '', text)

from ..resilience import resilient_call, CircuitBreaker

_anilist_cb = CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)

class AniListProvider(DiscoveryProvider):
    """Discovery provider using the AniList GraphQL API for anime content."""
    @property
    def name(self) -> str:
        return "anilist"

    @resilient_call(retry_on=(httpx.HTTPError, ValueError), circuit_breaker=_anilist_cb)
    async def _do_search(self, query: str, limit: int) -> List[CanonicalEntity]:
        query_graphql = '''
        query ($search: String, $page: Int, $perPage: Int) {
            Page (page: $page, perPage: $perPage) {
                media (search: $search, type: ANIME, sort: SEARCH_MATCH) {
                    id
                    title {
                        romaji
                        english
                        native
                    }
                    description
                    seasonYear
                    coverImage {
                        large
                    }
                    genres
                    averageScore
                    popularity
                }
            }
        }
        '''
        variables = {
            "search": query,
            "page": 1,
            "perPage": limit
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://graphql.anilist.co",
                json={"query": query_graphql, "variables": variables},
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()
            
            media_list = data.get("data", {}).get("Page", {}).get("media", [])
            entities = []
            for m in media_list:
                title = m.get("title", {}).get("english") or m.get("title", {}).get("romaji")
                
                ratings = {}
                if m.get("averageScore"):
                    # AniList is 0-100, convert to 0-10
                    ratings[self.name] = Rating(
                        value=m["averageScore"] / 10.0,
                        source="community",
                        vote_count=m.get("popularity")
                    )

                entity = CanonicalEntity(
                    title=title,
                    type="anime",
                    year=m.get("seasonYear"),
                    poster_url=m.get("coverImage", {}).get("large"),
                    overview=strip_html(m.get("description")),
                    genres=m.get("genres", []),
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

    async def search(self, query: str, limit: int = 5) -> List[CanonicalEntity]:
        """Search for anime on AniList."""
        try:
            return await self._do_search(query, limit) or []
        except Exception as e:
            logger.error(f"AniList search failed: {e}")
            return []

    async def get_details(self, provider_id: str) -> Optional[CanonicalEntity]:
        # Implementation for single item fetch
        return None
