import google.generativeai as genai
from .base_handler import LLMHandler


class GeminiHandler(LLMHandler):
    def __init__(self, model_name, api_key, system_prompts):
        genai.configure(api_key=api_key)
        self.model_name = model_name
        self.system_prompts = system_prompts

    def generate(self, user_prompt: str, is_batch: bool) -> str:
        system_content = self.system_prompts['batch'] if is_batch else self.system_prompts['unit']
        
        # Inicializa o modelo com a instrução de sistema fixa
        model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=system_content,
            generation_config={
                "temperature": 0,
                "response_mime_type": "application/json"
            }
        )
        
        # Chamada síncrona
        response = model.generate_content(user_prompt)
        return response.text