from unittest.mock import patch

from src.llm.llm_factory import LLMFactory


def test_get_processor_returns_gemini_handler_for_gemini_models():
    with patch("src.llm.llm_factory.GeminiHandler") as gemini_cls:
        with patch("src.llm.llm_factory.OllamaHandler") as ollama_cls:
            expected = object()
            gemini_cls.return_value = expected

            result = LLMFactory.get_processor("gemini-2.5-flash-lite", "api-key")

            assert result is expected
            gemini_cls.assert_called_once_with("gemini-2.5-flash-lite", "api-key")
            ollama_cls.assert_not_called()


def test_get_processor_returns_ollama_handler_for_non_gemini_models():
    with patch("src.llm.llm_factory.GeminiHandler") as gemini_cls:
        with patch("src.llm.llm_factory.OllamaHandler") as ollama_cls:
            expected = object()
            ollama_cls.return_value = expected

            result = LLMFactory.get_processor("llama3.2", "ignored-api-key")

            assert result is expected
            ollama_cls.assert_called_once_with("llama3.2")
            gemini_cls.assert_not_called()
