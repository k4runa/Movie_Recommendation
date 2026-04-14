"""
services/ai.py — Gemini AI Integration Service

Provides advanced movie taste analysis and personalized recommendation
explanations using Google's Gemini Generative AI models.

Required Environment Variables:
    GEMINI_API_KEY: Your Google AI Studio API key.
"""

import os
import logging
import google.generativeai as genai
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Configure the Gemini SDK
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
else:
    logger.warning("GEMINI_API_KEY not found in environment. AI features will be disabled.")


class AIService:
    """
    Handles communication with Google Gemini to provide intelligent
    movie-related insights.
    """

    def __init__(self, model_name: str = "gemini-1.5-flash"):
        self.model_name = model_name
        self.active = bool(api_key)

    def _get_model(self):
        return genai.GenerativeModel(self.model_name)

    async def analyze_user_taste(self, watched_movies: List[Dict[str, Any]]) -> Optional[str]:
        """
        Generates a professional summary of the user's movie preferences
        based on their watch history.
        """
        if not self.active or not watched_movies:
            return None

        # Prepare the context
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
            model = self._get_model()
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini API Error (analyze_user_taste): {e}")
            return "Unable to analyze taste profile at this time."

    async def explain_recommendations(
        self, watched_titles: List[str], recommendations: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        Generates a brief "Reason why" for each recommended movie based
        on the user's history.
        """
        if not self.active or not watched_titles or not recommendations:
            return {}

        rec_titles = [r.get("title") for r in recommendations]
        
        prompt = f"""
        User's Watch History: {', '.join(watched_titles)}
        
        Recommendations for the user: {', '.join(rec_titles)}
        
        TASK:
        For each recommended movie, provide a ONE-SENTENCE "hook" explaining why the user might like it, 
        referencing their watch history where possible. 
        Keep it brief, persuasive, and professional.
        
        Format the output as:
        Title: Reason
        Title: Reason
        """

        try:
            model = self._get_model()
            response = model.generate_content(prompt)
            
            # Parse the response into a dict
            explanations = {}
            for line in response.text.strip().split("\n"):
                if ":" in line:
                    title, reason = line.split(":", 1)
                    explanations[title.strip()] = reason.strip()
            return explanations
        except Exception as e:
            logger.error(f"Gemini API Error (explain_recommendations): {e}")
            return {}

# Singleton instance
ai_service = AIService()
