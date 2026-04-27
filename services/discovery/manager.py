import asyncio
from typing import List, Dict
from .base import DiscoveryProvider
from .tmdb_provider import TMDBProvider
from .anilist_provider import AniListProvider
from .omdb_provider import OMDBProvider
from .router import DiscoveryRouter, RouteStrategy
from .merger import DiscoveryMerger
from .models import CanonicalEntity
from ..cache import cache_service
import hashlib
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class DiscoveryManager:
    def __init__(self):
        self.providers: Dict[str, DiscoveryProvider] = {
            "tmdb": TMDBProvider(),
            "anilist": AniListProvider(),
            "omdb": OMDBProvider()
        }
        self.router = DiscoveryRouter()
        self.merger = DiscoveryMerger()

    def _cache_key(self, query: str) -> str:
        return f"discovery_search_v2_{hashlib.md5(query.lower().encode()).hexdigest()}"

    async def _execute_parallel_search(self, query: str, active_providers: List[DiscoveryProvider], limit: int) -> List[List[CanonicalEntity]]:
        tasks = [provider.search(query, limit) for provider in active_providers]
        return await asyncio.gather(*tasks, return_exceptions=True) #type: ignore

    async def search_all(self, query: str, limit: int = 10) -> List[dict]:
        """
        Orchestrates intent-based search across multiple providers, merges results,
        and returns them as serializable dicts.
        """
        cache_key = self._cache_key(query)
        
        # Check cache
        cached = await cache_service.get(cache_key)
        if cached:
            try:
                return json.loads(cached)
            except (json.JSONDecodeError, TypeError):
                pass
        
        strategy = self.router.detect_intent(query)
        logger.info(f"Discovery search: query='{query}', strategy={strategy.value}")
        
        active_providers = []
        if strategy == RouteStrategy.ANIME_FIRST:
            active_providers = [self.providers["anilist"], self.providers["tmdb"]]
        elif strategy == RouteStrategy.MOVIE_ONLY:
            active_providers = [self.providers["tmdb"]]
        else: # AGGRESSIVE_PARALLEL
            active_providers = list(self.providers.values())

        # Execute searches
        raw_results = await self._execute_parallel_search(query, active_providers, limit)
        
        # Filter out exceptions
        valid_results = []
        for _, res in enumerate(raw_results):
            if isinstance(res, Exception):
                logger.error(f"Provider search failed: {res}")
            else:
                valid_results.append(res)
        
        # Merge & deduplicate
        merged_entities = self.merger.merge_results(valid_results)
        
        # Serialize
        result_dicts = [entity.model_dump() for entity in merged_entities]
        
        # Cache for 1 hour
        try:
            # Cache whole result set
            await cache_service.set(cache_key, json.dumps(result_dicts), ttl=3600)
            
            # Also cache individual entities by ID for detail view speed
            for entity in merged_entities:
                await cache_service.set(f"entity_{entity.id}", entity.model_dump_json(), ttl=3600)
        except Exception:
            pass  # Cache failures shouldn't break search
        
        return result_dicts

    async def get_entity_by_id(self, entity_id: str) -> Optional[CanonicalEntity]:
        """Fetch a single entity from cache by its canonical ID."""
        try:
            cached = await cache_service.get(f"entity_{entity_id}")
            if cached:
                return CanonicalEntity.model_validate_json(cached)
        except Exception:
            pass
        return None

