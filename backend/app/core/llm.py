"""
DCBrain LLM Client — Gemini Integration
Provides a wrapper around Google Gemini 2.5 Flash for agent reasoning.
"""

from typing import Dict, Any, List, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from app.core.config import settings


class GeminiClient:
    """Wrapper for Google Gemini API providing structured calls and parsing."""

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = "gemini-2.5-flash"
        self._llm = None

    def get_llm(self) -> Optional[ChatGoogleGenerativeAI]:
        """Lazy load the ChatGoogleGenerativeAI instance."""
        if not self.api_key:
            return None
        
        if self._llm is None:
            try:
                self._llm = ChatGoogleGenerativeAI(
                    model=self.model_name,
                    google_api_key=self.api_key,
                    temperature=0.2,
                    timeout=30.0,
                )
            except Exception as e:
                print(f"⚠️ GeminiClient: Failed to initialize LangChain Gemini: {e}")
        return self._llm

    async def generate_response(self, prompt: str, system_instruction: str = None) -> str:
        """Generate response for a plain text prompt."""
        llm = self.get_llm()
        if not llm:
            return "⚠️ Gemini LLM Client is not initialized (GEMINI_API_KEY missing). Mock response generated."

        messages = []
        if system_instruction:
            messages.append(("system", system_instruction))
        messages.append(("user", prompt))

        try:
            response = await llm.ainvoke(messages)
            return str(response.content)
        except Exception as e:
            print(f"❌ GeminiClient Error: {e}")
            return f"❌ Failed to generate response from Gemini: {e}"

    async def generate_structured(self, prompt: str, schema: type[BaseModel], system_instruction: str = None) -> Any:
        """Generate structured Pydantic output using Gemini's native structured JSON capability."""
        llm = self.get_llm()
        if not llm:
            # Fallback to returning a default instance of the Pydantic schema
            print("⚠️ GeminiClient: API Key not set. Returning empty mock schema.")
            return schema.model_construct()

        messages = []
        if system_instruction:
            messages.append(("system", system_instruction))
        messages.append(("user", prompt))

        try:
            # Bind the Pydantic schema to enforce structured JSON output
            structured_llm = llm.with_structured_output(schema)
            response = await structured_llm.ainvoke(messages)
            return response
        except Exception as e:
            print(f"❌ GeminiClient Structured Output Error: {e}")
            # Fallback mock schema
            return schema.model_construct()


# Singleton client
gemini_client = GeminiClient()
