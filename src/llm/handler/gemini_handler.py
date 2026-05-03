import time

import google.generativeai as genai

from ..rich_api_log import llm_api_request_spinner, log_llm_api_failure, log_llm_api_success
from ..prompt import PromptRepository
from .base_handler import LLMHandler


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
                "response_mime_type": "application/json",
            },
        )

    def generate(self, user_content: str) -> str:
        user_prompt = self.prompt_repository.get_user_prompt(user_content)
        prompt_char_count = len(user_prompt)
        t0 = time.perf_counter()
        try:
            with llm_api_request_spinner("Gemini", self.model_name, prompt_char_count):
                response = self.model.generate_content(user_prompt)
            text = response.text
            elapsed_s = time.perf_counter() - t0
            log_llm_api_success("Gemini", self.model_name, elapsed_s, len(text))
            return text
        except Exception as e:
            log_llm_api_failure("Gemini", self.model_name, e)
            raise