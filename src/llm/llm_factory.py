from .handler.gemini_handler import GeminiHandler
from .handler.ollama_handler import OllamaHandler
from .handler.base_handler import LLMHandler

class LLMFactory:
    @staticmethod
    def get_processor(model: str, api_key: str, system_prompts: dict) -> LLMHandler:
        if "gemini" in model.lower():
            return GeminiHandler(model, api_key, system_prompts)
        return OllamaHandler(model, system_prompts)