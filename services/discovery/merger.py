from typing import List
import difflib
from .models import CanonicalEntity

class DiscoveryMerger:
    def __init__(self, similarity_threshold: float = 0.85):
        self.threshold = similarity_threshold

    def _similar(self, a: str, b: str) -> float:
        if not a or not b:
            return 0.0
        return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()

    def merge_results(self, all_results: List[List[CanonicalEntity]]) -> List[CanonicalEntity]:
        """
        Merge results from multiple providers into a unified list of canonical entities.
        Deduplication is performed based on exact ID matches and fuzzy title/year comparisons.
        """
        flattened: List[CanonicalEntity] = []
        for provider_results in all_results:
            flattened.extend(provider_results)

        merged_entities: List[CanonicalEntity] = []

        for entity in flattened:
            matched = False
            for existing in merged_entities:
                # 1. Check for shared external IDs (e.g. IMDb ID)
                shared_omdb = (
                    "omdb" in entity.sources and "omdb" in existing.sources and 
                    entity.sources["omdb"].id == existing.sources["omdb"].id
                )
                
                # 2. Fuzzy Match Logic
                similarity = self._similar(entity.title, existing.title)
                same_year = (entity.year == existing.year) if entity.year and existing.year else True
                same_type = (entity.type == existing.type)
                
                fuzzy_match = (similarity >= self.threshold) and same_year and same_type

                if shared_omdb or fuzzy_match:
                    existing.merge_with(entity)
                    matched = True
                    break

            if not matched:
                merged_entities.append(entity)

        return merged_entities
