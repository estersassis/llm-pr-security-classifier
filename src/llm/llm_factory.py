from .handler.gemini_handler import GeminiHandler
from .handler.ollama_handler import OllamaHandler
from .handler.base_handler import LLMHandler

class LLMFactory:
    @staticmethod
    def get_processor(model: str, api_key: str) -> LLMHandler:
        if "gemini" in model.lower():
            return GeminiHandler(model, api_key)
        return OllamaHandler(model)