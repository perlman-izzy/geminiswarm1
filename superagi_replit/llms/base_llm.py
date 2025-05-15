"""
Base LLM class for SuperAGI.
"""
from abc import ABC, abstractmethod
from typing import List, Any, Dict, Optional, Union


class BaseLlm(ABC):
    @abstractmethod
    def chat_completion(self, prompt: Union[str, List[Dict[str, str]]]) -> str:
        """Generate a chat completion for the given prompt."""
        pass

    @abstractmethod
    def get_source(self) -> str:
        """Get the source of the LLM."""
        pass

    @abstractmethod
    def get_model(self) -> str:
        """Get the model name."""
        pass

    @abstractmethod
    def get_models(self) -> List[str]:
        """Get available models."""
        pass

    @abstractmethod
    def verify_access_key(self) -> bool:
        """Verify that the access key is valid."""
        pass