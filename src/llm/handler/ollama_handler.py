import time

import requests

from ..prompt import PromptRepository
from ..rich_api_log import llm_api_request_spinner, log_llm_api_failure, log_llm_api_success
from .base_handler import LLMHandler


class OllamaHandler(LLMHandler):
    def __init__(self, model_name):
        self.model_name = model_name
        self.prompt_repository = PromptRepository(model_name)
        self.url = "http://localhost:11434/api/generate"

    def generate(self, user_content: str) -> str:
        system = self.prompt_repository.get_system_prompt()
        prompt = self.prompt_repository.get_user_prompt(user_content)
        payload = {
            "model": self.model_name,
            "system": system,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.0},
        }
        input_char_count = len(prompt or "") + len(system or "")
        t0 = time.perf_counter()
        try:
            with llm_api_request_spinner("Ollama", self.model_name, input_char_count):
                response = requests.post(self.url, json=payload, timeout=180)
                response.raise_for_status()
                response_body = response.json()
            text = response_body.get("response", "") or ""
            elapsed_s = time.perf_counter() - t0
            raw_in = response_body.get("prompt_eval_count")
            raw_out = response_body.get("eval_count")
            input_tokens = int(raw_in) if raw_in is not None else None
            output_tokens = int(raw_out) if raw_out is not None else None
            log_llm_api_success(
                "Ollama",
                self.model_name,
                elapsed_s,
                input_char_count=input_char_count,
                output_char_count=len(text),
                input_token_count=input_tokens,
                output_token_count=output_tokens,
            )
            return text
        except Exception as e:
            detail = None
            if isinstance(e, requests.HTTPError) and e.response is not None:
                detail = f"HTTP {e.response.status_code}: {e.response.text[:500]}"
            log_llm_api_failure("Ollama", self.model_name, e, detail=detail)
            raise