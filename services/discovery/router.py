import re
from enum import Enum
from typing import List

class RouteStrategy(Enum):
    ANIME_FIRST = "anime_first"
    MOVIE_ONLY = "movie_only"
    AGGRESSIVE_PARALLEL = "aggressive_parallel"

class DiscoveryRouter:
    """Analyzes search query to determine the best routing strategy for providers."""
    
    ANIME_KEYWORDS = {
        "anime", "ova", "manga", "season", "shippuden", "no", "to", "wa", "ga", "ni", "de", "kara", "made",
        "titan", "kaisen", "ghoul", "note", "clover", "ball", "naruto", "boruto", "piece", "beast", "online",
        "art", "slayer", "academia", "hunter", "fullmetal", "alchemist", "bleach", "geass", "clannad", "stein",
        "monogatari", "haikyuu", "kuroko", "evangelion", "bebop", "champloo", "gundam", "fate", "stay", "night"
    }
    
    def detect_intent(self, query: str) -> RouteStrategy:
        """Determine the most effective provider routing strategy based on search keywords."""
        query_lower = query.lower()
        # Clean query for better matching
        clean_query = re.sub(r'[^\w\s]', '', query_lower)
        words = set(clean_query.split())
        
        # Heuristic 1: Anime Keywords
        if self.ANIME_KEYWORDS.intersection(words):
            return RouteStrategy.ANIME_FIRST
            
        # Heuristic 2: Japanese Romaji patterns and common endings
        if re.search(r'(kun|chan|san|sama|senpai|sensei|maru|suke|taru|mono|den|maru)\b', query_lower):
            return RouteStrategy.ANIME_FIRST
            
        # Heuristic 3: Anime-specific year patterns like "2024 anime" or "Spring 2024"
        if re.search(r'\b(spring|summer|fall|winter)\s+\d{4}\b', query_lower):
            return RouteStrategy.ANIME_FIRST

        # Default strategy
        return RouteStrategy.AGGRESSIVE_PARALLEL
