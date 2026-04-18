import os
import logging
from typing import Dict, Any, AsyncGenerator
from dotenv import load_dotenv
import asyncio
import random

# SDK Imports
try:
    from google import genai
    HAS_GENAI       =   True
except ImportError:
    HAS_GENAI       =   False
try:
    from groq import AsyncGroq
    HAS_GROQ        =   True
except ImportError:
    HAS_GROQ        =   False

load_dotenv()
logger              =   logging.getLogger(__name__)


def parse_keys(env_var: str) -> list[str]:
    """Helper to parse comma-separated API keys from environment."""
    raw             =   os.getenv(env_var, "")
    return [k.strip() for k in raw.split(",") if k.strip()]


class AIService:
    """
    Handles AI insights with a resilient fallback and rotation architecture.
    Supports multiple API keys for both Gemini and Groq.
    """

    def __init__(
        self,
        gemini_model:           str     =   "gemini-2.5-flash",
        gemini_fallback_model:  str     =   "gemini-1.5-flash",
        groq_model:             str     =   "llama-3.3-70b-versatile",
    ):
        self.gemini_model               =   gemini_model
        self.gemini_fallback_model      =   gemini_fallback_model
        self.groq_model                 =   groq_model

        # Parse multiple keys
        self.gemini_keys                =   parse_keys("GEMINI_API_KEY")
        self.groq_keys                  =   parse_keys("GROQ_API_KEY")

        # Track current key indices for rotation
        self.current_gemini_idx         =   0
        self.current_groq_idx           =   0

        self.gemini_active              =   HAS_GENAI and len(self.gemini_keys) > 0
        self.groq_active                =   HAS_GROQ and len(self.groq_keys) > 0
        self.active                     =   self.gemini_active or self.groq_active

        if not self.active:
            logger.warning("No AI providers (Gemini/Groq) are correctly configured. AI features disabled.")

    async def _call_gemini(self, prompt: str) -> str:
        """Helper to call Gemini with key rotation on quota limits."""
        if not self.gemini_active:
            raise Exception("Gemini not active")

        # Try all available keys starting from the current one
        num_keys                        =   len(self.gemini_keys)
        for _ in range(num_keys):
            key                         =   self.gemini_keys[self.current_gemini_idx]
            delay                       =   1.0
            for attempt in range(3):
                try:
                    client              =   genai.Client(api_key=key)
                    response            =   await client.aio.models.generate_content(model=self.gemini_model, contents=prompt)
                    
                    if response and response.text:
                        return response.text.strip()
                
                except Exception as e:
                    err_str             =   str(e).upper() 
                    if "429" in err_str or "RATE_LIMIT" in err_str or "TOO_MANY_REQUESTS" in err_str:
                        if attempt < 2:
                            sleep_time  =   min(delay * (2 ** attempt) + random.uniform(0, 0.5), 10.0)
                            logger.warning(f"Gemini Key {self.current_gemini_idx} rate limited. Retrying in {sleep_time:.2f}s...")
                            await asyncio.sleep(sleep_time)
                            continue
                        else:
                            break # rotate key after retries exhausted
                    elif "QUOTA" in err_str or "EXHAUSTED" in err_str:
                        # Hard quota limit, rotate immediately
                        break
                    
                    # If it's a model not found or invalid model error, try fallback
                    if "MODEL" in err_str or "NOT_FOUND" in err_str or "INVALID" in err_str:
                        logger.warning(f"Model {self.gemini_model} failed. Trying fallback {self.gemini_fallback_model}...")
                        try:
                            response    =   await client.aio.models.generate_content(model=self.gemini_fallback_model, contents=prompt)
                            if response and response.text:
                                return response.text.strip()
                        except Exception as fallback_e:
                            raise fallback_e
                    raise e  # Real error, don't rotate

            logger.warning(f"Gemini Key {self.current_gemini_idx} exhausted or failed. Rotating to next key...")
            self.current_gemini_idx     =   (self.current_gemini_idx + 1) % num_keys

        raise Exception("All Gemini API keys exhausted.")

    async def _call_groq(self, prompt: str, max_tokens: int = 250) -> str:
        """Helper to call Groq with key rotation on quota limits."""
        if not self.groq_active:
            raise Exception("Groq not active")
        num_keys                        =   len(self.groq_keys)
        for _ in range(num_keys):
            key                         =   self.groq_keys[self.current_groq_idx]
            delay                       =   1.0
            for attempt in range(3):
                try:
                    client              =   AsyncGroq(api_key=key)
                    response            =   await client.chat.completions.create(model=self.groq_model,messages=[{"role": "user", "content": prompt}],max_tokens=max_tokens,)
                    if response and response.choices[0].message.content:
                        return response.choices[0].message.content.strip()
                except Exception as e:
                    err_str             =   str(e).upper()
                    if "429" in err_str or "RATE_LIMIT" in err_str or "TOO_MANY_REQUESTS" in err_str:
                        if attempt < 2:
                            sleep_time  =   min(delay * (2 ** attempt) + random.uniform(0, 0.5), 10.0)
                            logger.warning(f"Groq Key {self.current_groq_idx} rate limited. Retrying in {sleep_time:.2f}s...")
                            await asyncio.sleep(sleep_time)
                            continue
                        else:
                            break
                    elif "QUOTA" in err_str or "EXHAUSTED" in err_str:
                        break
                    raise e
            
            logger.warning(f"Groq Key {self.current_groq_idx} exhausted. Rotating to next key...")
            self.current_groq_idx       =   (self.current_groq_idx + 1) % num_keys

        raise Exception("All Groq API keys exhausted.")

    async def analyze_user_taste(self, watched_movies: list[dict[str, Any]]) -> str | None:
        """Generates a summary of the user's movie taste in English."""
        if not self.active or not watched_movies:
            return None

        movie_entries           =   [f"- {m.get('title')}: {m.get('overview', 'No overview available.')}"for m in watched_movies]
        context                 =   "\n".join(movie_entries)

        prompt                  = f"""
                    Analyze the user's movie taste based on their watch history:
                    {context}
        
                    TASK:
                    You are Eco, a professional and insightful cinematic AI assistant for CineWave.
                    Write a professional, catchy, and insightful one-paragraph summary (under 60 words) 
                    describing their cinematic personality. Refer to them as "You".
                    Everything must be in English.
                """
        # 1. Try Gemini (with rotation)
        if self.gemini_active:
            try:
                return await self._call_gemini(prompt)
            except Exception as e:
                logger.warning(f"All Gemini keys failed or error occurred: {e}. Trying Groq fallback...")

        # 2. Fallback to Groq (with rotation)
        if self.groq_active:
            try:
                return await self._call_groq(prompt, max_tokens=150)
            except Exception as e:
                logger.error(f"All AI providers (Gemini & Groq) exhausted: {e}")

        return "Unable to analyze taste profile at this time (Service limit reached)."

    async def explain_recommendations(self, watched_titles: list[str], recommendations: list[Dict[str, Any]]) -> dict[str, str]:
        """Generates a 'Reason why' hook for each recommendation in English."""
        if not self.active or not watched_titles or not recommendations:
            return {}

        rec_titles              =   [r.get("title", "") for r in recommendations]
        prompt                  =   f"""
                Watch History: {', '.join(watched_titles)}
                Recommendations: {', '.join(rec_titles)}
                
                TASK:
                You are Eco, the CineWave AI assistant.
                For each recommended movie, provide a ONE-SENTENCE explanation why the user might like it based on their history.
                Everything must be in English.
                Format precisely:
                Title: Reason
                Title: Reason
            """
        # 1. Try Gemini
        if self.gemini_active:
            try:
                raw_text        =   await self._call_gemini(prompt)
                return self._parse_explanations(raw_text)
            except Exception as e:
                logger.warning(f"Gemini cluster failed: {e}. Trying Groq fallback...")

        # 2. Fallback to Groq
        if self.groq_active:
            try:
                raw_text        =   await self._call_groq(prompt)
                return self._parse_explanations(raw_text)
            except Exception as e:
                logger.error(f"Groq cluster failed as well: {e}")

        return {}

    async def chat(self, message: str, context: str | None = None) -> str:
        """Wrapper for non-streaming calls."""
        full_response           =   ""
        async for chunk in self.stream_chat(message, context):
            full_response       = full_response + chunk
        return full_response

    async def stream_chat(self, message: str, context: str | None = None) -> AsyncGenerator[str, None]:
        """General stream chat method with full fallback support."""
        if not self.active:
            yield "AI Service not active"
            return

        prompt                  =   message
        if context:
            prompt              =   f"Context: {context}\n\nUser Message: {message}"

        # 1. Try Gemini
        if self.gemini_active:
            try:
                async for chunk in self._stream_gemini(prompt):
                    yield chunk
                return
            except Exception as e:
                logger.warning(f"Gemini stream failed: {e}. Trying Groq...")
        # 2. Try Groq
        if self.groq_active:
            try:
                async for chunk in self._stream_groq(prompt):
                    yield chunk
                return
            except Exception as e:
                logger.error(f"Groq stream failed: {e}")

        yield "I'm currently experiencing high demand and cannot process your request right now. Please try again in a few moments."

    async def _stream_gemini(self, prompt: str) -> AsyncGenerator[str, None]:
        """Helper to stream Gemini with key rotation (simplified)."""
        key                     =   self.gemini_keys[self.current_gemini_idx]
        try:
            client              =   genai.Client(api_key=key)
            # Use generate_content_stream for streaming
            async for response in await client.aio.models.generate_content_stream(model=self.gemini_model, contents=prompt):
                if response.text:
                    yield response.text
        except Exception as e:
            # If rate limited or quota, we might want to rotate, 
            # but for streaming it's harder to restart. 
            # For now, let it fail to the fallback.
            raise e

    async def _stream_groq(self, prompt: str) -> AsyncGenerator[str, None]:
        """Helper to stream Groq with key rotation (simplified)."""
        key                     =   self.groq_keys[self.current_groq_idx]
        try:
            client              =   AsyncGroq(api_key=key)
            stream              =   await client.chat.completions.create(model=self.groq_model,messages=[{"role": "user", "content": prompt}],stream=True,)
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            raise e

    def _parse_explanations(self, text: str) -> dict[str, str]:
        """Helper to parse 'Title: Reason' format."""
        explanations            =   {}
        if not text:
            return explanations

        for line in text.strip().split("\n"):
            if ":" in line:
                parts           =   line.split(":", 1)
                explanations[parts[0].strip()]  =   parts[1].strip()
        return explanations


# Singleton instance
ai_service = AIService()
