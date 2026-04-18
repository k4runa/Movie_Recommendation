"""
services/ai.py — Multi-Provider AI Service (Gemini with Groq Fallback)

Provides movie taste analysis and personalized recommendation explanations.
Features an automatic fallback mechanism: if Gemini (Primary) fails due to 
quota (429) or other errors, the service automatically retries using 
Groq (Secondary).

Required Environment Variables:
    GEMINI_API_KEY: Primary provider key.
    GROQ_API_KEY: Secondary (fallback) provider key.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# SDK Imports
try:
    from google import genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

try:
    from groq import AsyncGroq
    HAS_GROQ = True
except ImportError:
    HAS_GROQ = False

load_dotenv()
logger = logging.getLogger(__name__)

# Fetch API keys
gemini_key = os.getenv("GEMINI_API_KEY")
groq_key = os.getenv("GROQ_API_KEY")

class AIService:
    """
    Handles AI insights with a resilient fallback architecture.
    Primary: Google Gemini
    Secondary: Groq (Llama-3)
    """

    def __init__(
        self, 
        gemini_model: str = "gemini-2.0-flash",
        groq_model: str = "llama-3.3-70b-versatile"
    ):
        self.gemini_model = gemini_model
        self.groq_model = groq_model
        
        # Initialize Gemini
        self.gemini_active = HAS_GENAI and bool(gemini_key)
        self.gemini_client = None
        if self.gemini_active:
            try:
                self.gemini_client = genai.Client(api_key=gemini_key)
            except Exception as e:
                logger.error(f"Failed to initialize Gemini Client: {e}")
                self.gemini_active = False

        # Initialize Groq
        self.groq_active = HAS_GROQ and bool(groq_key)
        self.groq_client = None
        if self.groq_active:
            try:
                self.groq_client = AsyncGroq(api_key=groq_key)
            except Exception as e:
                logger.error(f"Failed to initialize Groq Client: {e}")
                self.groq_active = False
        
        self.active = self.gemini_active or self.groq_active
        
        if not self.active:
            logger.warning("No AI providers (Gemini/Groq) are correctly configured. AI features disabled.")

    async def analyze_user_taste(self, watched_movies: List[Dict[str, Any]]) -> Optional[str]:
        """
        Generates a summary of the user's movie taste. 
        Tries Gemini first, falls back to Groq on failure.
        """
        if not self.active or not watched_movies:
            return None

        movie_entries = [f"- {m.get('title')}: {m.get('overview', 'No overview available.')}" for m in watched_movies]
        context = "\n".join(movie_entries)
        
        prompt = f"""
        Analyze the user's movie taste based on their watch history:
        {context}
        
        TASK:
        Write a professional, catchy, and insightful one-paragraph summary (under 60 words) 
        describing their cinematic personality. Refer to them as "You".
        """

        # 1. Try Primary (Gemini)
        if self.gemini_active and self.gemini_client:
            try:
                response = await self.gemini_client.aio.models.generate_content(
                    model=self.gemini_model,
                    contents=prompt
                )
                return response.text.strip()
            except Exception as e:
                logger.warning(f"Gemini failed (analyze_user_taste), trying Groq... Error: {e}")

        # 2. Fallback (Groq)
        if self.groq_active and self.groq_client:
            try:
                response = await self.groq_client.chat.completions.create(
                    model=self.groq_model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=150
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                logger.error(f"Groq fallback failed as well: {e}")

        return "Unable to analyze taste profile at this time (All providers exhausted)."

    async def explain_recommendations(
        self, watched_titles: List[str], recommendations: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        Generates a "Reason why" hook for each recommendation with fallback.
        """
        if not self.active or not watched_titles or not recommendations:
            return {}

        rec_titles = [r.get("title", "") for r in recommendations]
        prompt = f"""
        Watch History: {', '.join(watched_titles)}
        Recommendations: {', '.join(rec_titles)}
        
        TASK:
        For each recommended movie, provide a ONE-SENTENCE explanation why they might like it.
        Format precisely:
        Title: Reason
        Title: Reason
        """

        # 1. Try Primary (Gemini)
        if self.gemini_active and self.gemini_client:
            try:
                response = await self.gemini_client.aio.models.generate_content(
                    model=self.gemini_model,
                    contents=prompt
                )
                return self._parse_explanations(response.text)
            except Exception as e:
                logger.warning(f"Gemini failed (explain_recs), trying Groq... Error: {e}")

        # 2. Fallback (Groq)
        if self.groq_active and self.groq_client:
            try:
                response = await self.groq_client.chat.completions.create(
                    model=self.groq_model,
                    messages=[{"role": "user", "content": prompt}]
                )
                return self._parse_explanations(response.choices[0].message.content)
            except Exception as e:
                logger.error(f"Groq fallback failed (explain_recs): {e}")

        return {}

    def _parse_explanations(self, text: str) -> Dict[str, str]:
        """Helper to parse 'Title: Reason' format."""
        explanations = {}
        if not text:
            return explanations
            
        for line in text.strip().split("\n"):
            if ":" in line:
                parts = line.split(":", 1)
                explanations[parts[0].strip()] = parts[1].strip()
        return explanations

# Singleton instance
ai_service = AIService()
