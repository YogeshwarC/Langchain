import os
from google import genai
from typing import Optional

class GeminiClient:
    """
    Wrapper for Google GenAI Client
    Handles initialization and basic generation calls
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            print("WARNING: No GEMINI_API_KEY provided")
            self.client = None
        else:
            self.client = genai.Client(api_key=self.api_key)

    def generate_content(self, model: str, contents: str) -> Optional[object]:
        """Generate content using the client"""
        if not self.client:
            return None
            
        try:
            response = self.client.models.generate_content(
                model=model,
                contents=contents
            )
            return response
        except Exception as e:
            print(f"Gemini API Error: {e}")
            return None
