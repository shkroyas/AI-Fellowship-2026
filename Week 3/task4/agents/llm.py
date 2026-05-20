import time
import google.generativeai as genai
from config import Config

class GeminiKeyRotator:
    """Manages active key cycling over your configured list of Gemini keys to prevent RPM rate limit blocks."""
    
    def __init__(self):
        # Retrieve parsed keys list from config
        self.keys = Config.get_gemini_api_keys()
        self.current_index = 0
        
    def get_keys_count(self) -> int:
        return len(self.keys)
        
    def get_current_key(self) -> str:
        if not self.keys:
            raise ValueError(
                "No Gemini API Keys found! Please set API_KEY list inside your .env file."
            )
        return self.keys[self.current_index]
        
    def rotate(self) -> str:
        """Cycles to the next API key in the list."""
        if not self.keys:
            raise ValueError("No Gemini API Keys found to rotate!")
        self.current_index = (self.current_index + 1) % len(self.keys)
        current_key = self.keys[self.current_index]
        print(f"  [Key Rotator]: Cycling to API Key at index {self.current_index}...")
        return current_key
        
    def configure_current(self):
        """Sets the active key in the generativeai SDK library."""
        key = self.get_current_key()
        genai.configure(api_key=key)

# Central instance of Key Rotator
rotator = GeminiKeyRotator()

def call_llm_with_rotation(prompt: str, temperature: float = 0.1, response_schema=None) -> str:
    """
    Centralized model executor that runs a prompt using Gemini 2.5 Flash.
    If a 429 quota exception is caught, it dynamically rotates to the next API key.
    """
    model_name = "gemini-2.5-flash"
    max_attempts = max(rotator.get_keys_count() * 2, 5)
    base_delay = 5
    
    for attempt in range(max_attempts):
        try:
            # Register active key
            rotator.configure_current()
            
            # Setup generative model
            model = genai.GenerativeModel(model_name)
            
            # Formulate generation config
            config_args = {"temperature": temperature}
            if response_schema:
                config_args["response_mime_type"] = "application/json"
                config_args["response_schema"] = response_schema
                
            config = genai.GenerationConfig(**config_args)
            
            response = model.generate_content(
                prompt,
                generation_config=config
            )
            return response.text.strip()
            
        except Exception as e:
            error_str = str(e)
            # Match standard 429 rate limit or quota patterns
            if "429" in error_str or "quota" in error_str.lower() or "exhausted" in error_str.lower():
                if rotator.get_keys_count() > 1:
                    rotator.rotate()
                else:
                    delay = base_delay * (attempt + 1)
                    print(f"  [Rate Limit]: Single key setup. Sleeping for {delay}s...")
                    time.sleep(delay)
            else:
                # Raise other exceptions up the execution graph
                raise e
                
    raise RuntimeError("LLM call failed. All rotated API keys have exhausted their rate limits.")
