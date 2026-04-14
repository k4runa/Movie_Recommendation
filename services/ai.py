"""
services/ai.py — Google GenAI Integration Service

Provides advanced movie taste analysis and personalized recommendation
explanations using the modern Google GenAI SDK.

Required Environment Variables:
    GEMINI_API_KEY: Your Google AI Studio API key.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Try to import the new SDK
try:
    from google import genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

load_dotenv()

logger = logging.getLogger(__name__)

# Fetch API key
api_key = os.getenv("GEMINI_API_KEY")

class AIService:
    """
    Handles communication with Google Gemini to provide intelligent
    movie-related insights using the modern GenAI Client.
    """

    def __init__(self, model_name: str = "gemini-2.0-flash"):
        self.model_name = model_name
        self.active = HAS_GENAI and bool(api_key)
        self.client = None
        
        if self.active:
            try:
                # The Client manages authentication and provides access to all models
                self.client = genai.Client(api_key=api_key)
            except Exception as e:
                logger.error(f"Failed to initialize GenAI Client: {e}")
                self.active = False
        elif not HAS_GENAI:
            logger.info("google-genai package not installed. Gemini features disabled.")
        else:
            logger.warning("GEMINI_API_KEY not found in environment. AI features will be disabled.")

    async def analyze_user_taste(self, watched_movies: List[Dict[str, Any]]) -> Optional[str]:
        """
        Generates a professional summary of the user's movie preferences
        based on their watch history using asynchronous content generation.
        """
        if not self.active or not watched_movies or not self.client:
            return None

        movie_entries = [f"- {m.get('title')}: {m.get('overview', 'No overview available.')}" for m in watched_movies]
        context = "\n".join(movie_entries)
        
        prompt = f"""
        I am a movie recommendation engine. I want you to analyze a user's taste based on their watch history below.
        
        WATCH HISTORY:
        {context}
        
        TASK:
        Write a professional, catchy, and insightful one-paragraph summary (under 60 words) describing the user's 
        cinematic personality. Identify specific patterns, themes, or moods they seem to enjoy. 
        Refer to them as "You".
        """

        try:
            # Using the asynchronous 'aio' module of the new SDK
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"GenAI SDK Error (analyze_user_taste): {e}")
            return "Unable to analyze taste profile at this time."

    async def explain_recommendations(
        self, watched_titles: List[str], recommendations: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        Generates a brief "Reason why" for each recommended movie.
        """
        if not self.active or not watched_titles or not recommendations or not self.client:
            return {}

        rec_titles = [r.get("title") for r in recommendations]
        
        prompt = f"""
        User's Watch History: {', '.join(watched_titles)}
        
        Recommendations for the user: {', '.join(rec_titles)}
        
        TASK:
        For each recommended movie, provide a ONE-SENTENCE "hook" explaining why the user might like it, 
        referencing their watch history where possible. 
        Keep it brief, persuasive, and professional.
        
        Format the output precisely as:
        Title: Reason
        Title: Reason
        """

        try:
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            
            explanations = {}
            for line in response.text.strip().split("\n"):
                if ":" in line:
                    parts = line.split(":", 1)
                    title, reason = parts[0], parts[1]
                    explanations[title.strip()] = reason.strip()
            return explanations
        except Exception as e:
            logger.error(f"GenAI SDK Error (explain_recommendations): {e}")
            return {}

# Singleton instance
ai_service = AIService()
