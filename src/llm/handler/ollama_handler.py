from .base_handler import LLMHandler
import requests


class OllamaHandler(LLMHandler):
    def __init__(self, model_name, system_prompts):
        self.model_name = model_name
        self.system_prompts = system_prompts
        self.url = "http://localhost:11434/api/generate"

    def generate(self, user_prompt: str, is_batch: bool) -> str:
        system_content = self.system_prompts['batch'] if is_batch else self.system_prompts['unit']
        
        payload = {
            "model": self.model_name,
            "system": system_content,
            "prompt": user_prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.0}
        }

        response = requests.post(self.url, json=payload, timeout=180)
        response.raise_for_status()
        return response.json().get('response', '')