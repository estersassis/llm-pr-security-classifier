from abc import ABC, abstractmethod


class LLMHandler(ABC):
    @abstractmethod
    def generate(self, user_content: str) -> str:
        pass