import os
import google.generativeai as genai
from typing import Optional

class GeminiAdapter:
    """
    Driven Adapter for Google Gemini LLM.
    Supports 'Bring Your Own Key' (BYOK) architecture.
    """
    def __init__(self, user_api_key: Optional[str] = None):
        # 1. Priority: User provided key (from Request Header)
        if user_api_key:
            self.api_key = user_api_key
            self.source = "User-Provided"
        # 2. Fallback: Server env var (Optional - you might disable this to save costs)
        else:
            self.api_key = os.getenv("GOOGLE_API_KEY")
            self.source = "Server-Default"

        if not self.api_key:
            raise ValueError("No LLM API Key provided. Please enter your Gemini Key in Settings.")

        # Configure the global instance for this session/request
        # Note: genai.configure is global, so this isn't thread-safe in high concurrency 
        # without looking at context vars, but acceptable for v1.0.
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel("gemini-pro")

    def generate_text(self, prompt: str) -> str:
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            # Catch "Quota Exceeded" specifically to tell user it's THEIR key
            if "429" in str(e):
                raise ConnectionError(f"Your Gemini API Key quota is exceeded ({self.source}).")
            raise e