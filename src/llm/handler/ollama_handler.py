from .base_handler import LLMHandler
from ..prompt import PromptRepository
import requests


class OllamaHandler(LLMHandler):
    def __init__(self, model_name):
        self.model_name = model_name
        self.prompt_repository = PromptRepository(model_name)
        self.url = "http://localhost:11434/api/generate"

    def generate(self, user_content: str) -> str:
        payload = {
            "model": self.model_name,
            "system": self.prompt_repository.get_system_prompt(),
            "prompt": self.prompt_repository.get_user_prompt(user_content),
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.0}
        }

        response = requests.post(self.url, json=payload, timeout=180)
        response.raise_for_status()
        return response.json().get('response', '')