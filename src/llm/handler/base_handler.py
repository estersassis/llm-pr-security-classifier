from abc import ABC, abstractmethod


class LLMHandler(ABC):
    @abstractmethod
    def generate(self, user_prompt: str, is_batch: bool) -> str:
        pass