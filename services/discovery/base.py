from abc import ABC, abstractmethod
from typing import List, Optional
from .models import CanonicalEntity

class DiscoveryProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def search(self, query: str, limit: int = 5) -> List[CanonicalEntity]:
        """Search the provider and return normalized entities."""
        pass

    @abstractmethod
    async def get_details(self, provider_id: str) -> Optional[CanonicalEntity]:
        """Fetch detailed info for a specific item from this provider."""
        pass
