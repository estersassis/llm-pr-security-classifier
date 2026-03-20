import google.generativeai as genai
from .base_handler import LLMHandler
from ..prompt import PromptRepository


class GeminiHandler(LLMHandler):
    def __init__(self, model_name, api_key):
        genai.configure(api_key=api_key)
        self.model_name = model_name
        self.prompt_repository = PromptRepository(model_name)
        
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=self.prompt_repository.get_system_prompt(),
            generation_config={
                "temperature": 0,
                "response_mime_type": "application/json"
            }
        )

    def generate(self, user_content: str) -> str:
        user_prompt = self.prompt_repository.get_user_prompt(user_content)
        response = self.model.generate_content(user_prompt)
        return response.text