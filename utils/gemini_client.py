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

    MODEL_FALLBACK_CHAIN = [
        "gemini-3-pro-preview",
        "gemini-2.5-pro", 
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-2.0-flash",
        "gemini-1.5-flash"
    ]

    def generate_content(self, model: str, contents: str, config: Optional[object] = None) -> Optional[object]:
        """
        Generate content using the client with automatic fallback
        If 'model' fails, it tries the rest of the chain.
        """
        if not self.client:
            print("❌ Error: Gemini Client not initialized (check API key)")
            return None
            
        # Determine starting point in chain
        start_index = 0
        if model in self.MODEL_FALLBACK_CHAIN:
            start_index = self.MODEL_FALLBACK_CHAIN.index(model)
        
        # Create effective chain: requested model -> rest of chain
        # If requested model is NOT in chain, try it first, then default to chain
        if model not in self.MODEL_FALLBACK_CHAIN:
            chain_to_try = [model] + self.MODEL_FALLBACK_CHAIN
        else:
            chain_to_try = self.MODEL_FALLBACK_CHAIN[start_index:]
            
        for attempt_model in chain_to_try:
            try:
                # print(f"   🤖 Trying model: {attempt_model}...")
                response = self.client.models.generate_content(
                    model=attempt_model,
                    contents=contents,
                    config=config
                )
                return response
            except Exception as e:
                error_str = str(e)
                # Check for critical errors that warrant fallback
                if "429" in error_str or "404" in error_str or "RESOURCE_EXHAUSTED" in error_str or "NOT_FOUND" in error_str:
                    print(f"   ⚠️  Model {attempt_model} failed ({'Quota' if '429' in error_str else 'Not Found'}). Falling back...")
                    continue
                else:
                    # Reraise other errors (e.g., input validation)
                    print(f"Gemini API Error with model {attempt_model}: {e}")
                    # If it's a structural error (like bad config), fallback might not help, but we try once more with a simpler model if possible?
                    # For now, continue to fallback is safer for robustness.
                    continue
        
        print("❌ All models in fallback chain exhausted.")
        return None
