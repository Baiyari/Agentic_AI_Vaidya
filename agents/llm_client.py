import logging
from typing import Optional

from config.settings import settings

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Thin, resilient wrapper around google-generativeai.
    Ensures that missing keys or network errors NEVER crash the application
    or interrupt the clinical pipeline, returning None to trigger deterministic fallbacks.
    """

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model_name = model_name or settings.GEMINI_MODEL
        self._model = None
        self._initialized = False
        self._initialize()

    def _initialize(self) -> None:
        if not self.api_key:
            logger.info("GEMINI_API_KEY not configured. LLM client running in zero-LLM template fallback mode.")
            return

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._model = genai.GenerativeModel(self.model_name)
            self._initialized = True
            logger.info(f"Gemini LLM client initialized successfully with model {self.model_name}.")
        except Exception as e:
            logger.warning(f"Failed to initialize google-generativeai: {e}. Falling back to template mode.")
            self._initialized = False

    def is_available(self) -> bool:
        """Returns True if Gemini model is configured and ready."""
        return self._initialized and self._model is not None

    def generate(self, prompt: str, system_instruction: Optional[str] = None) -> Optional[str]:
        """
        Attempts to generate text from Gemini. Returns None gracefully on any failure.
        """
        if not self.is_available():
            return None

        try:
            full_prompt = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt
            response = self._model.generate_content(full_prompt)
            if response and hasattr(response, "text") and response.text:
                return response.text.strip()
            return None
        except Exception as e:
            logger.warning(f"LLM generation call failed: {e}. Using deterministic fallback.")
            return None


# Global singleton LLM client
llm_client = LLMClient()
