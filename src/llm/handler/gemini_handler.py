import time

import google.generativeai as genai

from typing import Optional

from ..prompt import PromptRepository
from ..rich_api_log import llm_api_request_spinner, log_llm_api_failure, log_llm_api_success
from .base_handler import LLMHandler


def _gemini_usage_token_counts(response) -> tuple[Optional[int], Optional[int]]:
    """Returns (input_tokens, output_tokens) from Gemini usage_metadata, if present."""
    usage = getattr(response, "usage_metadata", None)
    if usage is None:
        return None, None
    input_tokens = getattr(usage, "prompt_token_count", None)
    output_tokens = getattr(usage, "candidates_token_count", None)
    return input_tokens, output_tokens


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
        system_text = self.prompt_repository.get_system_prompt() or ""
        user_prompt = self.prompt_repository.get_user_prompt(user_content)
        input_char_count = len(system_text) + len(user_prompt)
        t0 = time.perf_counter()
        try:
            with llm_api_request_spinner("Gemini", self.model_name, input_char_count):
                response = self.model.generate_content(user_prompt)
            text = response.text
            elapsed_s = time.perf_counter() - t0
            input_tokens, output_tokens = _gemini_usage_token_counts(response)
            log_llm_api_success(
                "Gemini",
                self.model_name,
                elapsed_s,
                input_char_count=input_char_count,
                output_char_count=len(text),
                input_token_count=input_tokens,
                output_token_count=output_tokens,
            )
            return text
        except Exception as e:
            log_llm_api_failure("Gemini", self.model_name, e)
            raise